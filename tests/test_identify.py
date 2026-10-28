import db_support  # noqa: F401  (must be first)

import json
import math
import unittest
from unittest.mock import patch

from backend.extractor import ExtractionError
from backend.models import Procedure, ProcedureChunk
from backend.procedure_search import (abbreviates, acronym_names, classify, covers, extract_needs, mentions, more_specific_document,
                                      named_by_the_others, names_procedure, names_something, read_abbreviations, residence,
                                      unnamed_document)
from backend.rag import EmbeddingError
from db_support import DatabaseTestCase, make_client, unit_vector


class ClassifyTest(unittest.TestCase):
    def test_outcomes(self):
        cases = [
            ([], ("no_match", [])),
            ([(1, 0.40), (2, 0.39)], ("no_match", [])),
            ([(1, 0.80), (2, 0.60)], ("matched", [1])),
            ([(1, 0.70), (2, 0.69), (3, 0.40)], ("ambiguous", [1, 2])),
            ([(1, 0.70), (2, 0.70), (3, 0.70), (4, 0.70)], ("ambiguous", [1, 2, 3])),
        ]
        for ranked, expected in cases:
            with self.subTest(ranked=ranked):
                self.assertEqual(classify(ranked, min_score=0.53, margin=0.03), expected)


class MentionsTest(unittest.TestCase):
    def test_named_terms_must_mostly_appear_in_the_official_text(self):
        text = "Apply for a Community Certificate on the e-Sevai portal using your Citizen Number (CAN)."
        cases = [
            ("How do I get a certificate?", True),
            ("What documents does a Community Certificate need?", True),
            ("What is a Citizen Access Number (CAN)?", True),
            ("How can I update my address on my Aadhaar card?", False),
            ("How do I apply for a Caste Certificate in Gujarat?", False),
        ]
        for question, expected in cases:
            with self.subTest(question=question):
                self.assertEqual(mentions(text, question), expected)

    def test_ignores_sentence_initial_words(self):
        text = "Updating Data on Aadhaar: upload address proof."
        question = "I want to update my address on Aadhaar. What documents do I need, and how do I apply?"
        self.assertTrue(mentions(text, question))

    def test_matches_whole_words_only(self):
        self.assertFalse(mentions("Company registration and panchayat records.", "How do I update my PAN?"))

    def test_accepts_plural_names(self):
        self.assertTrue(mentions("Overseas Indian electors: an NRI can register online.", "Can NRIs vote in Indian elections?"))

    def test_india_and_its_states_are_jurisdictions_not_names_to_find(self):
        # covers checks a state against the page's own; every stored page is an official Indian page.
        self.assertTrue(mentions("Register to vote online with Form 6.", "How do I register to vote in Kerala?"))
        self.assertTrue(mentions("Citizens of India absent from the country can enrol.", "Can I still vote in Indian elections?"))
        self.assertTrue(mentions("Link PAN with Aadhaar online.", "How do I link Aadhaar with PAN in Tamil Nadu?"))
        # Another country is still a name the page must use.
        self.assertFalse(mentions("Register to vote online with Form 6.", "How do I register to vote in Canada?"))

    def test_uk_in_any_case_is_the_country_but_lower_case_us_is_a_word(self):
        self.assertFalse(mentions("Renewal of driving licence.", "how do i renew my uk driving licence"))
        self.assertTrue(mentions("Renewal of driving licence. Contact us.", "can you tell us how to renew a driving licence"))

    def test_where_the_citizen_lives_or_travels_is_not_a_name_to_find(self):
        overseas = "A citizen absent from the country owing to employment can enrol as an overseas elector."
        for question in ["I work in Dubai. Can I vote in India?", "I study in Canada. Can I still vote?",
                         "i am travelling to the uk. how do i get a permit?"]:
            with self.subTest(question):
                self.assertTrue(mentions(overseas, question))
        # A place that qualifies the service still counts, even beside where the citizen lives.
        self.assertFalse(mentions("Renewal of driving licence.", "I live in the UK. How do I renew my UK driving licence?"))
        self.assertFalse(mentions("Renewal of driving licence.", "How do I renew my driving licence in Dubai?"))

    def test_us_and_uk_must_appear_on_the_page_as_written(self):
        indian = "Apply for a passport at a Passport Seva Kendra. Contact us for help."
        self.assertFalse(mentions(indian, "How do I apply for a US passport?"))  # "contact us" is not the US
        self.assertFalse(mentions("Renewal of driving licence.", "How do I renew my driving licence in the UK?"))
        self.assertTrue(mentions("Register to vote in the UK online.", "How do I register to vote in the UK?"))
        # Where the citizen is going is one name among others the page does use.
        self.assertTrue(mentions("International Driving Permit for the countries to be visited.",
                                 "I am travelling to the UK. How do I get an International Driving Permit?"))
        self.assertTrue(mentions("We help everyone.", "PLEASE HELP US"))  # a question in capitals throughout

    def test_an_abbreviation_of_the_procedures_own_name_counts_as_named(self):
        permit = "International Driving Permit will be issued to a resident of India."
        self.assertFalse(mentions(permit, "How do I get an IDP?"))
        self.assertTrue(mentions(permit, "How do I get an IDP?", own=("International Driving Permit", "India")))
        self.assertFalse(mentions("Passport rules.", "How do I get an IDP?", own=("Apply for Passport", "India")))


MESSAGE = "I want to renew my passport and update my Aadhaar address. Which should I do first?"


def needs_output(*phrases, relation="Which should I do first?"):
    return json.dumps({
        "needs": [{"phrase": p, "question": f"How do I {p}?"} for p in phrases],
        "relation_question": relation,
    })


@patch("backend.procedure_search.call_qwen")
class ExtractNeedsTest(unittest.TestCase):
    def test_returns_needs_copied_from_the_message(self, llm):
        llm.return_value = needs_output("renew my passport", "update my Aadhaar address")
        needs, relation = extract_needs(MESSAGE)
        self.assertEqual([n["phrase"] for n in needs], ["renew my passport", "update my Aadhaar address"])
        self.assertEqual(relation, "Which should I do first?")

    def test_rejects_untrustworthy_output(self, llm):
        cases = {
            "invented phrase": needs_output("renew my passport", "apply for a gun licence"),
            "same phrase twice": needs_output("renew my passport", "renew my passport"),
            "extra field": json.dumps({"needs": [{"phrase": "renew my passport", "question": "q", "procedure_id": 1}]}),
            "empty question": json.dumps({"needs": [{"phrase": "renew my passport", "question": " "}]}),
            "not a list": json.dumps({"needs": "renew my passport"}),
            "not json": "renew my passport",
        }
        for name, output in cases.items():
            with self.subTest(name):
                llm.return_value = output
                self.assertIsNone(extract_needs(MESSAGE))
        llm.side_effect = ExtractionError("down")
        self.assertIsNone(extract_needs(MESSAGE))

    def test_accepts_a_verb_shared_by_listed_services_but_not_new_words(self, llm):
        message = "Explain EPF, EPS and EDLI and how they differ."
        llm.return_value = json.dumps({"needs": [{"phrase": f"Explain {s}", "question": f"What is {s}?"} for s in ("EPF", "EPS", "EDLI")],
                                       "relation_question": "how they differ"})
        needs, relation = extract_needs(message)
        self.assertEqual([n["phrase"] for n in needs], ["Explain EPF", "Explain EPS", "Explain EDLI"])
        self.assertEqual(relation, "how they differ")

        llm.return_value = json.dumps({"needs": [{"phrase": "Explain EPF", "question": "q"}, {"phrase": "Explain PAN", "question": "q"}]})
        self.assertIsNone(extract_needs(message))

    def test_drops_a_relation_question_not_in_the_message(self, llm):
        llm.return_value = needs_output("renew my passport", "update my Aadhaar address", relation="Can I reuse documents?")
        self.assertIsNone(extract_needs(MESSAGE)[1])


class AbbreviatesTest(unittest.TestCase):
    def test_literal_abbreviations_and_initials_of_consecutive_capitalised_words(self):
        for acronym, name in [("EPS", "Employees' Pension Scheme (EPS)"), ("EPF", "Employees' Provident Fund Scheme"),
                              ("DL", "Duplicate Driving Licence"), ("RC", "Renewal of Vehicle Registration Certificate"),
                              ("PAN", "Link PAN with Aadhaar")]:
            with self.subTest(acronym):
                self.assertTrue(abbreviates(acronym, name))
        for acronym, name in [("EPS", "Employees' Provident Fund Scheme"), ("EPF", "Employees' Pension Scheme (EPS)"),
                              ("RC", "Change of Address in Vehicle Registration"), ("UK", "Apply for a passport"),
                              ("RC", "REV-101 Community Certificate")]:  # a code gives no initial
            with self.subTest(acronym):
                self.assertFalse(abbreviates(acronym, name))

    def test_a_procedures_own_abbreviation_starts_its_name_or_is_written_in_it(self):
        for acronym, name in [("EPF", "Employees' Provident Fund Scheme"), ("EPS", "Employees' Pension Scheme (EPS)"),
                              ("DL", "Driving Licence Fees and Charges")]:
            with self.subTest(acronym):
                self.assertTrue(abbreviates(acronym, name, own=True))
        # The document a procedure deals with is not the procedure's own abbreviation.
        for acronym, name in [("RC", "Renewal of Vehicle Registration Certificate"), ("DL", "Duplicate Driving Licence"),
                              ("RC", "REV-101 Community Certificate")]:
            with self.subTest(acronym):
                self.assertFalse(abbreviates(acronym, name, own=True))

    def test_a_term_inside_a_longer_name_names_it_only_with_another_word_of_the_name(self):
        link = "Link PAN with Aadhaar"
        for question in ["Is it mandatory to link my PAN?", "Does my PAN need my aadhar?", "What if PAN is not linked?"]:
            with self.subTest(question):
                self.assertTrue(acronym_names("PAN", link, question))
        for question in ["How do I apply for a new PAN card?", "How do I change the name on my PAN card?"]:
            with self.subTest(question):
                self.assertFalse(acronym_names("PAN", link, question))
        self.assertTrue(acronym_names("ITR-2", "Filing of ITR-2", "Who should file ITR-2?"))
        # A one-letter piece ("e" of "e-PAN") is not a word of the name: "e-filing" does not name Instant e-PAN.
        self.assertFalse(acronym_names("PAN", "Instant e-PAN", "How do I register on the income tax e-filing portal with my PAN?"))
        self.assertTrue(acronym_names("PAN", "Instant e-PAN", "How do I get an instant PAN?"))
        # A bracketed short form is the name's own, and initials are as abbreviates has them.
        self.assertTrue(acronym_names("EPS", "Employees' Pension Scheme (EPS)", "What about EPS?"))
        self.assertTrue(acronym_names("DL", "Renewal of Driving Licence", "How much is it?"))


class CoversTest(unittest.TestCase):
    def test_a_state_procedure_does_not_cover_another_state_in_any_capitalisation(self):
        for question in ["how do i get a community certificate in kerala", "Income certificate in KARNATAKA?",
                         "I live in Orissa. Which documents do I need?"]:
            with self.subTest(question):
                self.assertFalse(covers("Tamil Nadu", question))
        for question in ["How do I get a community certificate in Tamil Nadu?", "community certificate tamilnadu",
                         "I moved from Kerala to Tamil Nadu. How do I get a ration card?", "What documents do I need?"]:
            with self.subTest(question):
                self.assertTrue(covers("Tamil Nadu", question))
        # A central procedure, however its jurisdiction is written, covers every state.
        for jurisdiction in ["India", "Central Government", None]:
            with self.subTest(jurisdiction):
                self.assertTrue(covers(jurisdiction, "How do I apply for a passport in Kerala?"))
        self.assertTrue(covers("Odisha", "documents for a certificate in orissa"))


class NamesProcedureTest(unittest.TestCase):
    def test_own_abbreviation_or_every_word_of_the_name(self):
        page = lambda name: Procedure(name=name)
        for question, name in [("What about EPS?", "Employees' Pension Scheme (EPS)"),
                               ("How do I claim EDLI insurance?", "Employees' Deposit Linked Insurance (EDLI)"),
                               ("How do I register to vote?", "Register to Vote"),
                               ("And what about linking PAN with Aadhaar?", "Link PAN with Aadhaar"),
                               ("Who should file ITR-2?", "Filing of ITR-2")]:
            with self.subTest(question):
                self.assertTrue(names_procedure(question, page(name)))
        for question, name in [("What about the pension?", "Employees' Pension Scheme (EPS)"),
                               ("What about the certificate?", "REV-101 Community Certificate"),
                               ("What about the RC?", "Renewal of Vehicle Registration Certificate"),  # a document, not its name
                               ("And how much does it cost?", "Driving Licence Fees and Charges"),
                               ("What about voters living abroad?", "Overseas (NRI) Voter Registration"),
                               ("How do I change the name on my PAN card?", "Link PAN with Aadhaar")]:  # a document it uses
            with self.subTest(question):
                self.assertFalse(names_procedure(question, page(name)))


class NamesSomethingTest(unittest.TestCase):
    def test_a_question_must_name_a_service_document_or_detail(self):
        for question in ["How do I renew?", "What documents do I need?", "How much is the fee?", "How do I apply?"]:
            with self.subTest(question):
                self.assertFalse(names_something(question))
        for question in ["How do I renew my passport?", "Can I vote?", "I turned 18.", "எனக்கு பாஸ்போர்ட் வேண்டும்"]:
            with self.subTest(question):
                self.assertTrue(names_something(question))


class ResidenceTest(unittest.TestCase):
    def test_where_the_message_says_the_citizen_is(self):
        for message in ["I work in Saudi Arabia.", "i study in canada", "I am an NRI.", "Can NRIs vote?",
                        "I live outside India.", "We live in the USA.", "I moved to the uk last year", "I work in the Gulf."]:
            with self.subTest(message):
                self.assertEqual(residence(message), "abroad")
        for message in ["How do I change my address?", "I live in Tamil Nadu.", "i live in kerala", "Tell us how to vote."]:
            with self.subTest(message):
                self.assertEqual(residence(message), "india")
        # A city is not known to be in India or abroad, in any capitalisation.
        for message in ["I work in Dubai.", "i work in dubai", "I live in Chennai."]:
            with self.subTest(message):
                self.assertIsNone(residence(message))


class ReadAbbreviationsTest(unittest.TestCase):
    def test_lower_case_own_abbreviations_are_read_in_capitals(self):
        names = ["International Driving Permit", "Employees' Pension Scheme (EPS)", "Link PAN with Aadhaar"]
        self.assertEqual(read_abbreviations("how do i get an idp", names), "how do i get an IDP")
        self.assertEqual(read_abbreviations("how much goes into eps", names), "how much goes into EPS")
        self.assertEqual(read_abbreviations("link pan with aadhaar", names), "link PAN with aadhaar")
        # A name that already holds an abbreviation gives no initials ("lpa" is a salary), and words stay words.
        self.assertEqual(read_abbreviations("my salary is 12 lpa", names), "my salary is 12 lpa")
        self.assertEqual(read_abbreviations("what is the permit fee", names), "what is the permit fee")


class MoreSpecificDocumentTest(unittest.TestCase):
    faq = Procedure(source_text="13. What are the documents required for applying Inter Caste Marriage Certificate?\n\n"
                                "Marriage Registration Certificate\n\n"
                                "7. What are the documents required for applying Community Certificate?\n\nPhoto")

    def test_a_heading_naming_the_document_only_with_more_qualifiers(self):
        self.assertTrue(more_specific_document("How do I get a marriage certificate?", self.faq))
        for question in ["What documents are needed for an inter caste marriage certificate?",
                         "What documents do I need for a community certificate?", "How do I get a birth certificate?"]:
            with self.subTest(question):
                self.assertFalse(more_specific_document(question, self.faq))
        # Without headings the page says nothing about it.
        lists = Procedure(source_text="Inter Caste Marriage Certificate\n\nMarriage Registration Certificate")
        self.assertFalse(more_specific_document("How do I get a marriage certificate?", lists))


class UnnamedDocumentTest(unittest.TestCase):
    def test_a_document_noun_without_its_kind_or_anything_else_named(self):
        for question, noun in [("How do I apply for a certificate in Tamil Nadu?", "certificate"),
                               ("I need a certificate from the government. How do I apply online?", "certificate"),
                               ("How do I apply for a licence?", "licence"), ("How do I get a new card?", "card")]:
            with self.subTest(question):
                self.assertEqual(unnamed_document(question), noun)
        for question in ["How do I renew my registration certificate?", "How do I get a certificate of registration?",
                         "What documents do I need for a nativity certificate?", "How do I get a gun licence?",
                         "How do I get a certificate for my vehicle?", "How do I renew?"]:
            with self.subTest(question):
                self.assertIsNone(unnamed_document(question))


class NamedByTheOthersTest(unittest.TestCase):
    def page(self, name, text):
        return Procedure(name=name, source_text=text)

    def test_prefers_the_service_page_that_a_tied_fee_table_names(self):
        permit = self.page("International Driving Permit", "Fees as prescribed along with user charges.")
        fees = self.page("Driving Licence Fees and Charges", "5 Issue of International Driving Permit Rs. 1000.00/-")
        self.assertIs(named_by_the_others("What is the fee for an International Driving Permit?", [permit, fees]), permit)
        self.assertIs(named_by_the_others("How much is the fee to renew a driving licence?",
                                          [self.page("Renewal of Driving Licence", "Fees as prescribed."),
                                           self.page("Driving Licence Fees and Charges", "8 Renewal of driving licence Rs. 200.00/-")])
                      .name, "Renewal of Driving Licence")

    def test_keeps_the_choice_when_the_question_or_the_pages_do_not_settle_it(self):
        permit = self.page("International Driving Permit", "Fees as prescribed.")
        fees = self.page("Driving Licence Fees and Charges", "5 Issue of International Driving Permit Rs. 1000.00/-")
        # The question does not use the page's whole name: a general fee question stays a choice.
        self.assertIsNone(named_by_the_others("What are the driving licence fees?", [permit, fees]))
        # Pages that name each other, or that do not name each other, do not decide anything.
        voters = self.page("Register to Vote", "Overseas (NRI) Voter Registration uses Form 6A.")
        overseas = self.page("Overseas (NRI) Voter Registration", "Register to Vote with Form 6.")
        self.assertIsNone(named_by_the_others("How do I register to vote as an overseas NRI voter registration?", [voters, overseas]))
        learner = self.page("Learner's Licence", "Age limit.")
        permanent = self.page("Permanent Driving Licence", "Form 4.")
        self.assertIsNone(named_by_the_others("Learner's licence or permanent driving licence?", [learner, permanent]))


def between(first, second):
    vector = [a + b for a, b in zip(unit_vector(first), unit_vector(second))]
    return [value / math.sqrt(2) for value in vector]


class IdentifyApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.passport = self.add("Passport", [unit_vector(0), unit_vector(3)])
        self.aadhaar = self.add("Aadhaar update", [unit_vector(1)])
        self.tax = self.add("Income tax return", [unit_vector(2)])

    def add(self, name, vectors):
        procedure = Procedure(
            name=name,
            summary=f"{name} summary.",
            source_url=f"https://example.gov.in/{name.replace(' ', '-')}",
            source_text="PRIVATE SOURCE TEXT",
            structured_data={"eligibility": None, "steps": ["One"]},
        )
        self.session.add(procedure)
        self.session.flush()
        for index, vector in enumerate(vectors):
            self.session.add(
                ProcedureChunk(
                    procedure_id=procedure.id, chunk_index=index, content="x", embedding=vector
                )
            )
        self.session.flush()
        return procedure

    def ask(self, query_vector, question="How do I get a passport?"):
        self.embed.side_effect = lambda texts, query=False: [query_vector]
        return self.client.post("/api/identify", json={"question": question})

    def test_matches_on_the_best_chunk_of_each_procedure(self):
        response = self.ask(unit_vector(3))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "matched")
        self.assertEqual([c["id"] for c in body["candidates"]], [self.passport.id])
        self.assertEqual(set(body["candidates"][0]), {"id", "name", "department", "jurisdiction", "summary"})
        self.assertNotIn("PRIVATE SOURCE TEXT", response.text)
        self.assertTrue(self.embed.call_args.kwargs["query"])

    def test_asks_for_clarification_when_procedures_are_equally_plausible(self):
        body = self.ask(between(1, 2)).json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual({c["id"] for c in body["candidates"]}, {self.aadhaar.id, self.tax.id})

    def test_reports_no_match_for_unrelated_questions(self):
        body = self.ask(unit_vector(9), "What is the best biryani recipe?").json()

        self.assertEqual(body, {"status": "no_match", "candidates": []})

    def test_similar_procedure_without_the_named_service_is_not_a_match(self):
        body = self.ask(unit_vector(3), "How do I update my Aadhaar address?").json()

        self.assertEqual(body, {"status": "no_match", "candidates": []})

    def test_a_bare_acronym_in_a_procedure_name_rescues_a_near_miss(self):
        eps = self.add("Employees' Pension Scheme (EPS)", [unit_vector(4)])
        eps.source_text = "EPS pension rules"
        # cosine `score` with the EPS chunk: below IDENTIFY_MIN_SCORE (0.53), around ACRONYM_MIN_SCORE (0.45)
        near = lambda score: [score if i == 4 else (1 - score ** 2) ** 0.5 if i == 9 else 0.0 for i in range(len(unit_vector()))]
        self.assertEqual(self.ask(near(0.5), "What is EPS?").json()["candidates"][0]["id"], eps.id)
        self.assertEqual(self.ask(near(0.5), "What is the pension?").json()["status"], "no_match")
        self.assertEqual(self.ask(near(0.4), "What is EPS?").json()["status"], "no_match")

    def test_an_abbreviation_naming_one_close_candidate_decides(self):
        epf = self.add("Employees' Provident Fund Scheme", [unit_vector(4)])
        eps = self.add("Employees' Pension Scheme (EPS)", [unit_vector(5)])
        epf.source_text = eps.source_text = "EPF and EPS rules"
        tie = between(4, 5)
        self.assertEqual(self.ask(tie, "Can I withdraw my EPF?").json()["candidates"][0]["id"], epf.id)
        self.assertEqual(self.ask(tie, "How much goes into EPS?").json()["candidates"][0]["id"], eps.id)
        # It also overrides a confident match on the other scheme ...
        leaning_eps = [0.75 if i == 5 else 0.66 if i == 4 else 0.0 for i in range(len(unit_vector()))]
        self.assertEqual(self.ask(leaning_eps, "Can I withdraw my EPF?").json()["candidates"][0]["id"], epf.id)
        # ... but naming both, or neither, leaves the scores to decide.
        self.assertEqual(self.ask(tie, "Is EPS part of EPF?").json()["status"], "ambiguous")
        self.assertEqual(self.ask(tie, "Can I withdraw my provident fund?").json()["status"], "ambiguous")

    def test_a_match_says_whether_the_question_names_the_procedure_itself(self):
        eps = self.add("Employees' Pension Scheme (EPS)", [unit_vector(4)])
        eps.source_text = "Employees' Pension Scheme (EPS): pension rules"
        for question in ["What about EPS?", "How do I join the Employees' Pension Scheme?"]:
            with self.subTest(question):
                body = self.ask(unit_vector(4), question).json()
                self.assertEqual((body["candidates"][0]["id"], body.get("named")), (eps.id, True))
        # Related words match the page but do not name it, so a follow-up stays where it is.
        body = self.ask(unit_vector(4), "What about the pension?").json()
        self.assertEqual((body["candidates"][0]["id"], body.get("named")), (eps.id, None))

    def test_an_abbreviation_only_one_nearby_page_uses_decides_a_near_miss(self):
        self.passport.source_text = "Check the VVPAT slip after voting."
        near = lambda score: [score if i == 3 else (1 - score ** 2) ** 0.5 if i == 9 else 0.0 for i in range(len(unit_vector()))]
        body = self.ask(near(0.5), "How long is the VVPAT slip shown?").json()
        self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", self.passport.id))
        # Used by two pages (even if only one is nearby), or by none, it decides nothing.
        self.tax.source_text = "VVPAT"
        self.assertEqual(self.ask(near(0.5), "How long is the VVPAT slip shown?").json()["status"], "no_match")
        self.assertEqual(self.ask(near(0.5), "What is GST?").json()["status"], "no_match")

    def test_another_countrys_procedure_is_not_matched_but_a_trip_abroad_is(self):
        self.passport.source_text = "Apply for an Indian passport at a Passport Seva Kendra."
        self.assertEqual(self.ask(unit_vector(0), "How do I apply for a US passport?").json()["status"], "no_match")
        self.assertEqual(self.ask(unit_vector(0), "How do I apply for a passport?").json()["status"], "matched")
        permit = self.add("International Driving Permit", [unit_vector(4)])
        permit.source_text = "International Driving Permit for the countries to be visited."
        for question in ["How do I get an IDP?", "How do I get an International Driving Permit for my trip to the UK?"]:
            with self.subTest(question):
                body = self.ask(unit_vector(4), question).json()
                self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", permit.id))

    def test_a_central_page_covers_a_question_naming_a_state(self):
        self.passport.source_text = "Apply for a passport online."
        self.assertEqual(self.ask(unit_vector(0), "How do I apply for a passport in Kerala?").json()["status"], "matched")
        self.assertEqual(self.ask(unit_vector(0), "how do i apply for a uk passport").json()["status"], "no_match")

    def test_a_document_asked_about_without_its_kind_is_asked_which(self):
        body = self.ask(unit_vector(0), "How do I apply for a certificate in Tamil Nadu?").json()
        self.assertEqual((body["status"], body["candidates"]), ("no_match", []))
        self.assertIn("Which certificate", body["clarification"])
        # Close pages are already a choice, and a named kind is searched as usual.
        self.assertEqual(self.ask(between(1, 2), "How do I apply for a licence?").json()["status"], "ambiguous")
        self.assertEqual(self.ask(unit_vector(0), "How do I renew my registration certificate?").json()["status"], "matched")

    def test_a_term_written_inside_a_procedure_name_names_it_only_with_another_word_of_it(self):
        link = self.add("Link PAN with Aadhaar", [unit_vector(4)])
        link.source_text = "Link your PAN with Aadhaar on the e-Filing portal."
        efiling = self.add("Register on the e-Filing Portal", [unit_vector(5)])
        efiling.source_text = "Enter your name as per your PAN to register."
        leaning_efiling = [0.75 if i == 5 else 0.66 if i == 4 else 0.0 for i in range(len(unit_vector()))]
        body = self.ask(leaning_efiling, "How do I link my PAN with Aadhaar?").json()
        self.assertEqual((body["candidates"][0]["id"], body.get("named")), (link.id, True))
        # Another action on the PAN card is neither page's service; the login page only uses the PAN.
        self.assertEqual(self.ask(leaning_efiling, "How do I apply for a new PAN card?").json()["status"], "no_match")
        body = self.ask(leaning_efiling, "How do I register on the e-filing portal with my PAN?").json()
        self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", efiling.id))

    def test_where_the_citizen_is_decides_between_a_service_and_its_overseas_variant(self):
        voters = self.add("Register to Vote", [unit_vector(4)])
        overseas = self.add("Overseas (NRI) Voter Registration", [unit_vector(5)])
        voters.source_text = overseas.source_text = "Fill the form to enrol in the electoral roll."
        leaning = lambda best, second: [0.75 if i == best else 0.66 if i == second else 0.0 for i in range(len(unit_vector()))]
        match = lambda vector, question: self.ask(vector, question).json()["candidates"][0]["id"]
        self.assertEqual(match(leaning(4, 5), "How do I register to vote while working in Saudi Arabia?"), overseas.id)
        self.assertEqual(match(leaning(5, 4), "How do I change my address in the electoral roll?"), voters.id)
        # A place it cannot tell leaves the scores to decide.
        self.assertEqual(match(leaning(5, 4), "How do I register to vote while working in Dubai?"), overseas.id)
        self.assertEqual(match(leaning(4, 5), "How do I register to vote while working in Dubai?"), voters.id)
        # It chooses between the two only once the service clears the threshold; it never makes a match of a miss.
        weak = [0.50 if i == 5 else 0.49 if i == 4 else (1 - 0.50 ** 2 - 0.49 ** 2) ** 0.5 if i == 9 else 0.0
                for i in range(len(unit_vector()))]
        self.assertEqual(self.ask(weak, "Can I do this at a post office?").json()["status"], "no_match")

    def test_a_lower_case_abbreviation_rescues_a_near_miss(self):
        permit = self.add("International Driving Permit", [unit_vector(4)])
        permit.source_text = "Apply for an International Driving Permit."
        near = lambda score: [score if i == 4 else (1 - score ** 2) ** 0.5 if i == 9 else 0.0 for i in range(len(unit_vector()))]
        self.assertEqual(self.ask(near(0.5), "how do i get an idp").json()["candidates"][0]["id"], permit.id)
        self.assertEqual(self.ask(near(0.5), "how do i get a permit").json()["status"], "no_match")

    def test_a_page_about_a_more_specific_document_is_not_matched(self):
        self.passport.source_text = ("13. What are the documents required for applying Inter Caste Marriage Certificate?\n\n"
                                     "Marriage Registration Certificate")
        self.assertEqual(self.ask(unit_vector(0), "How do I get a marriage certificate?").json()["status"], "no_match")
        body = self.ask(unit_vector(0), "What documents are needed for an inter caste marriage certificate?").json()
        self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", self.passport.id))

    def test_name_check_does_not_turn_a_close_call_into_a_match(self):
        self.aadhaar.source_text = "Aadhaar update in India"
        body = self.ask(between(1, 2), "How do I update my details in India?").json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual({c["id"] for c in body["candidates"]}, {self.aadhaar.id, self.tax.id})

    def test_a_close_call_goes_to_the_page_the_other_candidate_names(self):
        self.aadhaar.source_text = "Aadhaar update: fees as prescribed."
        self.tax.source_text = "Fee table: Aadhaar update Rs. 50."
        body = self.ask(between(1, 2), "What is the fee for an Aadhaar update?").json()
        self.assertEqual((body["status"], [c["id"] for c in body["candidates"]]), ("matched", [self.aadhaar.id]))

    def test_deleted_procedures_are_never_returned(self):
        self.client = make_client(self.session)
        self.client.delete(f"/api/admin/procedures/{self.passport.id}")

        self.assertEqual(self.ask(unit_vector(0)).json()["status"], "no_match")

    def test_invalid_questions_are_rejected(self):
        for body in ({"question": ""}, {"question": "   "}, {"question": "x" * 1001}, {}):
            with self.subTest(body=str(body)[:30]):
                response = self.client.post("/api/identify", json=body)
                self.assertEqual(response.status_code, 422)

    def test_single_questions_never_call_the_extraction_model(self):
        with patch("backend.procedure_search.call_qwen") as llm:
            self.ask(unit_vector(3), "How do I get a passport?")
        llm.assert_not_called()

    def test_embedding_failure_returns_502(self):
        self.embed.side_effect = EmbeddingError("down")

        response = self.client.post("/api/identify", json={"question": "passport"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The search service is unavailable. Try again."})



@patch("backend.procedure_search.call_qwen")
class IdentifyNeedsApiTest(DatabaseTestCase):
    VECTORS = {"renew my passport": 0, "update my Aadhaar address": 1, "get a driving licence": 9,
               "check the documents for that update": 1, "file my tax return": 2, "get a voter ID": 8}

    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.passport = IdentifyApiTest.add(self, "Passport", [unit_vector(0)])
        self.aadhaar = IdentifyApiTest.add(self, "Aadhaar", [unit_vector(1)])
        self.aadhaar.source_text = "Updating Data on Aadhaar"
        self.tax = IdentifyApiTest.add(self, "Income tax", [unit_vector(2)])
        self.embed.side_effect = lambda texts, query=False: [unit_vector(self.VECTORS.get(t, 7)) for t in texts]

    def ask(self, llm, message, *phrases):
        llm.return_value = needs_output(*phrases)
        return self.client.post("/api/identify", json={"question": message}).json()

    def test_matches_each_need_independently(self, llm):
        body = self.ask(llm, "I want to renew my passport, update my Aadhaar address and get a driving licence. Which should I do first?",
                        "renew my passport", "update my Aadhaar address", "get a driving licence")

        self.assertEqual(body["status"], "multiple")
        self.assertEqual([(n["phrases"], n["status"]) for n in body["needs"]], [
            (["renew my passport"], "matched"), (["update my Aadhaar address"], "matched"),
            (["get a driving licence"], "no_match"),
        ])
        self.assertEqual(body["needs"][0]["candidates"][0]["id"], self.passport.id)
        self.assertEqual(body["needs"][1]["candidates"][0]["id"], self.aadhaar.id)
        self.assertEqual(body["relation_question"], "Which should I do first?")
        self.assertEqual(body["pending"], [])
        self.assertEqual(llm.call_count, 1)

    def test_needs_for_the_same_procedure_share_one_answer(self, llm):
        body = self.ask(llm, "I need to update my Aadhaar address and check the documents for that update, and renew my passport.",
                        "update my Aadhaar address", "check the documents for that update", "renew my passport")

        self.assertEqual(len(body["needs"]), 2)
        self.assertEqual(body["needs"][0]["phrases"], ["update my Aadhaar address", "check the documents for that update"])
        self.assertEqual(body["needs"][0]["question"],
                         "How do I update my Aadhaar address? How do I check the documents for that update?")

    def test_background_cannot_hide_the_one_real_need(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        message = "I updated my Aadhaar last week. Now I need to renew my passport."
        self.embed.side_effect = lambda texts, query=False: [unit_vector(self.VECTORS.get(t, 7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]], "named": True})
        self.assertEqual(body["candidates"][0]["id"], self.passport.id)

    def test_background_that_matches_another_procedure_does_not_win(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        message = "I recently updated my Aadhaar. Now I want to renew my passport."
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1 if "Aadhaar" in t else 0) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body["candidates"][0]["id"], self.passport.id)

    def test_the_standalone_question_decides_when_the_phrase_alone_is_unclear(self, llm):
        llm.return_value = json.dumps({"needs": [{"phrase": "get a new one", "question": "How do I get a new passport?"}],
                                       "relation_question": None})
        vectors = {"get a new one": between(1, 2), "How do I get a new passport?": unit_vector(0)}
        self.embed.side_effect = lambda texts, query=False: [vectors.get(t, unit_vector(7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": "My passport has expired. How do I get a new one?"}).json()

        self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", self.passport.id))

    def test_the_whole_message_is_used_when_the_need_alone_matches_nothing(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1 if "," in t else 9) for t in texts]
        body = self.client.post("/api/identify", json={"question": "I want to renew my passport, please."}).json()

        self.assertEqual(body["candidates"][0]["id"], self.aadhaar.id)

    def test_questions_about_one_procedure_keep_the_single_flow(self, llm):
        llm.return_value = needs_output("update my Aadhaar address", "check the documents for that update")
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1) for _ in texts]
        body = self.client.post("/api/identify", json={
            "question": "I need to update my Aadhaar address and check the documents for that update."}).json()

        self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]], "named": True})
        self.assertEqual(body["candidates"][0]["id"], self.aadhaar.id)

    def test_needs_over_the_limit_are_listed_not_dropped(self, llm):
        phrases = ["renew my passport", "update my Aadhaar address", "file my tax return", "get a driving licence", "get a voter ID"]
        body = self.ask(llm, "I need to " + ", ".join(phrases) + ".", *phrases)

        self.assertEqual([n["phrases"][0] for n in body["needs"]], phrases[:3])
        self.assertEqual(body["pending"], [{"phrase": p, "question": f"How do I {p}?"} for p in phrases[3:]])

    def test_each_listed_service_is_matched_separately(self, llm):
        for procedure, name in ((self.passport, "EPF"), (self.aadhaar, "EPS"), (self.tax, "EDLI")):
            procedure.source_text = f"{name} scheme rules"
        llm.return_value = json.dumps({"needs": [{"phrase": f"Explain {s}", "question": f"What is {s}?"} for s in ("EPF", "EPS", "EDLI")],
                                       "relation_question": None})
        # Bare names can score too low on their own; each need's question is the fallback.
        vectors = {"Explain EPF": 0, "What is EPS?": 1, "What is EDLI?": 2}
        self.embed.side_effect = lambda texts, query=False: [unit_vector(vectors.get(t, 7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": "Explain EPF, EPS and EDLI"}).json()

        self.assertEqual(body["status"], "multiple")
        self.assertEqual([(n["status"], n["candidates"][0]["id"]) for n in body["needs"]],
                         [("matched", self.passport.id), ("matched", self.aadhaar.id), ("matched", self.tax.id)])

    def test_a_comparison_reaches_extraction_and_keeps_unsupported_services_unmatched(self, llm):
        llm.return_value = json.dumps({"needs": [{"phrase": "passport renewal", "question": "How do I renew my passport?"},
                                                 {"phrase": "ration card application", "question": "How do I apply for a ration card?"}],
                                       "relation_question": None})
        self.embed.side_effect = lambda texts, query=False: [unit_vector(0 if "passport" in t else 9) for t in texts]
        body = self.client.post("/api/identify", json={"question": "Compare passport renewal versus a ration card application"}).json()

        self.assertEqual(llm.call_count, 1)
        self.assertEqual([(n["phrases"], n["status"]) for n in body["needs"]],
                         [(["passport renewal"], "matched"), (["ration card application"], "no_match")])

    def test_a_comparison_gets_one_need_per_side_and_sides_are_distinct(self, llm):
        self.passport.source_text, self.aadhaar.source_text = "EPF rules", "EPS rules"
        message = "What is the difference between EPF and EPS?"
        llm.return_value = json.dumps({"needs": [{"phrase": "difference between EPF and EPS", "question": message}],
                                       "relation_question": None})
        self.embed.side_effect = lambda texts, query=False: [
            between(0, 1) if t in ("EPF", "What is EPF?") else unit_vector(1 if t in ("EPS", "What is EPS?") else 7) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual([(n["phrases"], n["status"], n["candidates"][0]["id"]) for n in body["needs"]],
                         [(["EPF"], "matched", self.passport.id), (["EPS"], "matched", self.aadhaar.id)])
        self.assertEqual(body["relation_question"], message)

    def test_a_question_naming_no_service_asks_which_one_without_searching(self, llm):
        body = self.client.post("/api/identify", json={"question": "How do I renew?"}).json()

        self.assertEqual((body["status"], body["candidates"]), ("no_match", []))
        self.assertIn("Which service or document", body["clarification"])
        self.embed.assert_not_called()
        llm.assert_not_called()

    def test_the_citizen_chooses_when_the_phrase_and_its_question_disagree(self, llm):
        llm.return_value = json.dumps({"needs": [{"phrase": "register to vote", "question": "How do I register to vote from abroad?"}],
                                       "relation_question": None})
        message = "I live abroad. How do I register to vote?"
        vectors = {"register to vote": unit_vector(0), "How do I register to vote from abroad?": unit_vector(1), message: unit_vector(1)}
        self.embed.side_effect = lambda texts, query=False: [vectors.get(t, unit_vector(7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual({c["id"] for c in body["candidates"]}, {self.passport.id, self.aadhaar.id})
        # Background in the question alone (the whole message still agrees with the phrase) does not.
        vectors[message] = unit_vector(0)
        body = self.client.post("/api/identify", json={"question": message}).json()
        self.assertEqual((body["status"], body["candidates"][0]["id"]), ("matched", self.passport.id))

    def test_the_citizen_chooses_when_the_whole_message_alone_confidently_disagrees(self, llm):
        # The extraction dropped what decides the service from the phrase and its question.
        llm.return_value = json.dumps({"needs": [{"phrase": "register as a voter", "question": "How do I register as a voter?"}],
                                       "relation_question": None})
        message = "I live outside India. How do I register as a voter?"
        vectors = {"register as a voter": unit_vector(0), "How do I register as a voter?": unit_vector(0), message: unit_vector(1)}
        self.embed.side_effect = lambda texts, query=False: [vectors.get(t, unit_vector(7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual([c["id"] for c in body["candidates"]], [self.passport.id, self.aadhaar.id])

    def test_the_citizen_chooses_when_the_question_alone_confidently_disagrees_and_the_message_is_close(self, llm):
        llm.return_value = json.dumps({"needs": [{"phrase": "vote in india", "question": "Can someone working abroad vote in India?"}],
                                       "relation_question": None})
        message = "i work far away, can i vote in india"
        vectors = {"vote in india": unit_vector(0), "Can someone working abroad vote in India?": unit_vector(1), message: between(0, 1)}
        self.embed.side_effect = lambda texts, query=False: [vectors.get(t, unit_vector(7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual([c["id"] for c in body["candidates"]], [self.passport.id, self.aadhaar.id])

    def test_a_phrase_without_its_document_is_checked_with_its_question(self, llm):
        link = IdentifyApiTest.add(self, "Link PAN with Aadhaar", [unit_vector(4)])
        link.source_text = "Link PAN with Aadhaar"
        llm.return_value = json.dumps({"needs": [{"phrase": "get a duplicate", "question": "How do I get a duplicate PAN card?"}],
                                       "relation_question": None})
        # The phrase alone is close to the passport page, which never names a PAN.
        self.embed.side_effect = lambda texts, query=False: [unit_vector(0) if t == "get a duplicate" else unit_vector(7) for t in texts]
        body = self.client.post("/api/identify", json={"question": "I lost my PAN card. How do I get a duplicate?"}).json()

        self.assertEqual((body["status"], body["candidates"]), ("no_match", []))

    def test_untrustworthy_or_single_extraction_keeps_the_single_flow(self, llm):
        for output in (needs_output("renew my passport"), "not json"):
            with self.subTest(output=output[:20]):
                llm.return_value = output
                self.embed.side_effect = lambda texts, query=False: [unit_vector(0) for _ in texts]
                body = self.client.post("/api/identify", json={"question": "I want to renew my passport, please."}).json()
                self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]], "named": True})
                self.assertEqual(body["candidates"][0]["id"], self.passport.id)

if __name__ == "__main__":
    unittest.main()
