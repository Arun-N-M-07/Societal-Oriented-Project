import db_support  # noqa: F401  (must be first)

import json
import unittest
from unittest.mock import patch

from sqlalchemy import func

from backend.extractor import ExtractionError
from backend.models import Procedure, ProcedureChunk
from backend.rag import EmbeddingError, GuidanceError, build_guidance_prompt, check_claims, verify_claims
from db_support import DatabaseTestCase, make_client, unit_vector


FEE = "The application fee for a fresh passport of 36 pages is Rs 1,500 payable online."
DOCS = "Applicants must carry proof of address and proof of date of birth to the appointment."
OLD_FEE = "Older guidance: the application fee for a fresh passport was Rs 1,000."


class VerifyClaimsTest(unittest.TestCase):
    passages = {1: FEE, 2: DOCS, 3: "Applicants without a registered mobile number cannot use online services."}

    def claim(self, text, quote, chunk_id=1):
        return {"text": text, "quote": quote, "chunk_id": chunk_id}

    def test_keeps_claims_quoted_verbatim_from_the_cited_passage(self):
        claims = [
            self.claim("Pay Rs 1,500 online.", "fee for a fresh passport of 36 pages is Rs 1,500"),
            self.claim("Bring address proof.", "  Applicants MUST carry proof\nof address ", 2),
        ]
        self.assertEqual(len(verify_claims(claims, self.passages)), 2)

    def test_keeps_negated_claims_backed_by_negated_quotes(self):
        claim = self.claim(
            "You cannot use online services without a registered mobile.",
            "without a registered mobile number cannot use online services", 3,
        )
        self.assertEqual(len(verify_claims([claim], self.passages)), 1)

    def test_quotes_joining_table_cells_or_list_items_differ_only_in_punctuation(self):
        # Scraped tables and lists store each cell or item as its own paragraph.
        passages = {7: "Purpose\n\nFor test of competence to drive\n\nRs. 300.00/-\n\n4",
                    8: "Documents required\n\nApplication in Form 25\n\nInsurance certificate*"}
        kept = [
            self.claim("The driving test fee is Rs. 300.00/-.", "For test of competence to drive Rs. 300.00/-.", 7),
            self.claim("Apply in Form 25.", "Documents required: Application in Form 25", 8),
        ]
        self.assertEqual(len(verify_claims(kept, passages)), 2)
        dropped = [
            self.claim("The fee is Rs. 300.", "test of competence to drive Rs. 300.00/- extra", 7),
            self.claim("Apply in Form 2.", "required: Application in Form 2", 8),  # "Form 2" is not "Form 25"
            self.claim("Test fee.", "For test of competence to dri", 7),  # stops mid-word
        ]
        self.assertEqual(verify_claims(dropped, passages), [])

    def test_a_short_quote_must_be_a_whole_list_item_without_numbers(self):
        passages = {9: "Documents required\n\nInsurance certificate*\n\nIssue of learner licence\n\nRs. 150.00/-"}
        self.assertEqual(len(verify_claims([self.claim("Bring the insurance certificate.", "Insurance certificate*", 9)], passages)), 1)
        for text, quote in [("Bring the insurance.", "Insurance"),  # part of an item
                            ("The fee is Rs. 150.", "Rs. 150.00/-")]:  # a bare amount needs its label
            with self.subTest(quote):
                self.assertEqual(verify_claims([self.claim(text, quote, 9)], passages), [])

    def test_every_amount_of_money_in_the_quote_is_in_the_claim(self):
        passages = {5: "Renewal after the grace period\n\nRs. 300.00/- (Additional fee at the rate of Rupees One Thousand Only "
                       "for delay of each year)\n\nRenewal of driving licence\n\nRs. 200.00/-"}
        late = "Renewal after the grace period Rs. 300.00/- (Additional fee at the rate of Rupees One Thousand Only for delay of each year)"
        kept = [self.claim("After the grace period it is Rs. 300, plus Rs. 1,000 for each year of delay.", late, 5),
                self.claim("After the grace period it is Rs. 300 plus Rupees One Thousand a year of delay.", late, 5),
                self.claim("Renewal costs Rs. 200.", "Renewal of driving licence Rs. 200.00/-", 5)]
        self.assertEqual(len(verify_claims(kept, passages)), 3)
        dropped = [self.claim("After the grace period an additional fee of Rs. 300 is levied.", late, 5),  # drops the Rs. 1,000
                   self.claim("Renewal of a licence costs a fee.", "Renewal of driving licence Rs. 200.00/-", 5)]  # no amount
        self.assertEqual(verify_claims(dropped, passages), [])
        # A row label copied from the quote without its fee is shown as the official row itself.
        label = verify_claims([self.claim("Renewal of driving licence", "Renewal of driving licence Rs. 200.00/-", 5)], passages)
        self.assertEqual([c["text"] for c in label], ["Renewal of driving licence Rs. 200.00/-"])

    def test_amounts_written_before_rupees_are_checked(self):
        row = ("16. Renewal of certificate of registration for motor vehicle older than 20 years from date of first "
               "registration (e) Imported motor vehicle (Two or Three wheeled ) Twenty thousand rupees 52(1) --")
        passages = {5: row}
        kept = verify_claims([self.claim("Renewing the RC of an imported two or three wheeler older than 20 years costs "
                                         "Rs. 20,000.", row, 5)], passages)
        self.assertEqual(len(kept), 1)
        self.assertEqual(verify_claims([self.claim("Renewing the RC of an imported two-wheeler costs a fee.", row, 5)],
                                       passages), [])

    def test_a_quote_cut_from_a_fee_row_keeps_the_rows_other_charges(self):
        row = ("9 Renewal of a driving licence for which application is made after the grace period Rs. 300.00/- "
               "(Additional fee at the rate of Rupees One Thousand Only for delay of each year)")
        passages = {5: f"8 Renewal of driving licence Rs. 200.00/-\n\n{row}"}
        cut = "after the grace period Rs. 300.00/- (Additional fee"
        self.assertEqual(verify_claims([self.claim("After the grace period an additional fee of Rs. 300 is levied.", cut, 5)],
                                       passages), [])
        kept = verify_claims([self.claim("After the grace period it is Rs. 300, plus Rs. 1,000 for each year of delay.", cut, 5),
                              self.claim("Renewal of driving licence", "8 Renewal of driving licence Rs. 200.00/-", 5)], passages)
        self.assertEqual([c["text"] for c in kept], ["After the grace period it is Rs. 300, plus Rs. 1,000 for each year of delay.",
                                                     "8 Renewal of driving licence Rs. 200.00/-"])

    def test_a_quote_opening_with_a_back_reference_needs_the_sentence_it_refers_to(self):
        passages = {5: "If the application is made more than 30 days after the date of expiry of the licence, the renewal "
                       "will be made with effect from the date of receipt of proper application. In such cases a fee of "
                       "Rs. 30/- will be realised."}
        bare = self.claim("A fee of Rs. 30/- will be realised.", "In such cases a fee of Rs. 30/- will be realised", 5)
        self.assertEqual(verify_claims([bare], passages), [])
        whole = self.claim("If you apply more than 30 days after expiry, a fee of Rs. 30/- is charged.",
                           "If the application is made more than 30 days after the date of expiry of the licence, the "
                           "renewal will be made with effect from the date of receipt of proper application. In such "
                           "cases a fee of Rs. 30/- will be realised", 5)
        self.assertEqual(len(verify_claims([whole], passages)), 1)
        # "such" elsewhere in a quote is not a back-reference.
        own = {6: "Fees as prescribed for such class of vehicle are payable at the RTO office."}
        self.assertEqual(len(verify_claims([self.claim("Fees are payable at the RTO office.",
                                                       "Fees as prescribed for such class of vehicle are payable at the RTO office", 6)],
                                           own)), 1)

    def test_a_fee_is_not_moved_to_another_kind_of_document(self):
        passages = {5: "1. Grant or renewal of trade certificate in respect of each class of vehicle:\n\n"
                       "1. Grant or renewal of trade certificate in respect of each class of vehicle: (a) Motorcycle "
                       "Rupees Five Hundred Only 34(1) ---\n\n"
                       "4. Issue or renewal of certificate of registration and assignment of new registration mark: "
                       "(b) Motor cycle Rupees Three Hundred Only 47(1) ---"}
        trade = "1. Grant or renewal of trade certificate in respect of each class of vehicle: (a) Motorcycle Rupees Five Hundred Only"
        self.assertEqual(verify_claims([self.claim("Renewing a motorcycle's registration certificate costs Rupees Five Hundred Only.",
                                                   trade, 5)], passages), [])
        kept = verify_claims([self.claim("A motorcycle trade certificate costs Rupees Five Hundred Only.", trade, 5),
                              self.claim("Renewing the certificate of registration of a motor cycle costs Rupees Three Hundred Only.",
                                         "4. Issue or renewal of certificate of registration and assignment of new registration "
                                         "mark: (b) Motor cycle Rupees Three Hundred Only", 5)], passages)
        self.assertEqual(len(kept), 2)

    def test_the_document_kind_may_come_from_the_question_a_list_answers(self):
        passages = {5: "9. What are the documents required for applying for Income Certificate?\n\nAddress Proof\n\nPAN card\n\n"
                       "10. What are the documents required for applying solvency certificate?\n\nEncumbrance Certificate"}
        self.assertEqual(len(verify_claims([self.claim("An income certificate needs your PAN card.", "PAN card", 5)], passages)), 1)
        # An item from the next certificate's list is not evidence for the income certificate.
        self.assertEqual(verify_claims([self.claim("An income certificate needs an Encumbrance Certificate.",
                                                   "Encumbrance Certificate", 5)], passages), [])

    def test_the_document_kind_may_come_from_a_lead_in_without_a_colon(self):
        page = ("Duplicate Licence\n\nA duplicate driving licence will be issued in the following circumstances\n\n"
                "When the licence is lost or destroyed\n\nWhen the photograph affixed to the licence requires replacement")
        lost = "When the licence is lost or destroyed"
        self.assertEqual(len(verify_claims([self.claim("A duplicate driving licence is issued when the licence is lost "
                                                       "or destroyed.", lost, 5)], {5: page})), 1)
        # The lead-in names one kind of document; another kind is still not evidenced.
        self.assertEqual(verify_claims([self.claim("A learner's licence is issued when the licence is lost or destroyed.",
                                                   lost, 5)], {5: page}), [])
        # An ordinary sentence ending in "the following year" does not lead a list.
        sentence = {5: page.replace("in the following circumstances", "in the following year")}
        self.assertEqual(verify_claims([self.claim("A duplicate driving licence is issued when the licence is lost "
                                                   "or destroyed.", lost, 5)], sentence), [])

    def test_a_question_or_colon_heading_still_wins_over_a_lead_in(self):
        passages = {5: "What is needed for a trade certificate?\n\nA registration certificate has the following requirements\n\n"
                       "Form 20 and the fee"}
        self.assertEqual(verify_claims([self.claim("A registration certificate needs Form 20 and the fee.",
                                                   "Form 20 and the fee", 5)], passages), [])

    def test_separate_sentences_of_a_paragraph_keep_their_own_amounts(self):
        paragraph = ("On death of an employee in service: Benefit = average PF balance of last 12 months. Alternatively, "
                     "35 × average monthly wages (max ₹15,000) + 50% of average balance, capped at ₹1.75 lakh. "
                     "Minimum benefit: ₹2.5 lakh. Maximum benefit: ₹7 lakh (including 20% enhancement).")
        kept = verify_claims([self.claim("The minimum EDLI benefit is ₹2.5 lakh.", "Minimum benefit: ₹2.5 lakh", 5)],
                             {5: paragraph})
        self.assertEqual(len(kept), 1)
        # A quote cut from inside one sentence still needs that sentence's other amount.
        cut = "average monthly wages (max ₹15,000) + 50% of average balance"
        self.assertEqual(verify_claims([self.claim("It is 35 times average monthly wages (max ₹15,000) plus 50% of "
                                                   "the average balance.", cut, 5)], {5: paragraph}), [])

    def test_numbers_must_equal_the_quoted_numbers(self):
        quote = "fee for a fresh passport of 36 pages is Rs 1,500"
        for text in ["Pay Rs 1500.", "Pay Rs. 1,500.00 online.", "A 36-page passport costs Rs 1,500."]:
            with self.subTest(text):
                self.assertEqual(len(verify_claims([self.claim(text, quote)], self.passages)), 1)
        # Digits of the quoted amount are not the amount ("Rs 150" is not "Rs 1,500").
        for text in ["Pay Rs 150.", "Pay Rs 1,50.", "A 3-page passport costs Rs 1,500.", "Pay Rs 1.5 online."]:
            with self.subTest(text):
                self.assertEqual(verify_claims([self.claim(text, quote)], self.passages), [])

    def test_ages_deadlines_and_counts_in_words_must_equal_the_quoted_ones(self):
        quotes = {
            "twenty": "An applicant who has completed twenty years of age will be eligible for applying for a licence to drive a transport vehicle",
            "eighteen": "The applicant who has completed the age of eighteen years of age is eligible to apply for a driving licence",
            "fourteen": "within fourteen days of the transfer, application for the transfer of ownership shall be made by the transferee",
            "months": "the person succeeding to the possession of the vehicle may for a period of three months, use the vehicle",
            "copies": "Fill two copies of Form 6",
            "times": "Users can re-schedule appointments three times except in the case of tatkaal",
            "compound": "The licence is valid until the holder attains twenty-five years of age",
            "hundred": "Records are kept for one hundred and twenty years by the authority",
        }
        passages = {i: quote + "." for i, quote in enumerate(quotes.values())}
        ids = dict(zip(quotes, passages))

        def kept(text, key):
            return len(verify_claims([self.claim(text, quotes[key], ids[key])], passages)) == 1

        for text, key in [("You can apply after completing 20 years of age.", "twenty"),
                          ("You can apply after completing twenty years of age.", "twenty"),
                          ("Twenty Years of age is the minimum.", "twenty"),
                          ("Apply within 14 days of the transfer.", "fourteen"),
                          ("It is valid until you are 25 years old.", "compound"),
                          ("It is valid until twenty-five years of age.", "compound"),
                          ("Records are kept for 120 years.", "hundred"),
                          ("You may use the vehicle for three months.", "months"),
                          ("Fill 2 copies of Form 6.", "copies")]:
            with self.subTest(text):
                self.assertTrue(kept(text, key))
        for text, key in [("You can apply after completing eighteen years of age.", "twenty"),
                          ("You can apply after completing twenty years of age.", "eighteen"),
                          ("Apply within thirty days of the transfer.", "fourteen"),
                          ("You may use the vehicle for six months.", "months"),
                          ("Fill three copies of Form 6.", "copies"),
                          ("You can re-schedule five times.", "times"),
                          ("It is valid until five years of age.", "compound"),  # "twenty-five" is 25, not 5
                          ("Records are kept for 100 years.", "hundred"),  # "one hundred and twenty" is 120
                          # Units are not converted: "two weeks" is not taken to be "fourteen days".
                          ("Apply within two weeks of the transfer.", "fourteen"),
                          # A claim keeps the period its own quote states.
                          ("Driving a transport vehicle needs a licence.", "twenty")]:
            with self.subTest(text):
                self.assertFalse(kept(text, key))

    def test_a_period_keeps_its_unit_and_its_condition(self):
        sentence = ("Where the owner of a motor vehicle dies, the person succeeding to the possession of the vehicle may for a "
                    "period of three months, use the vehicle as if it has been transferred to him where such person has, within "
                    "thirty days of the death of the owner informs the registering authority.")
        passages = {5: sentence}
        whole = sentence[sentence.index("the person"):-1]
        kept = self.claim("The heir may use the vehicle for three months if they inform the registering authority within "
                          "thirty days of the death.", whole, 5)
        self.assertEqual(len(verify_claims([kept], passages)), 1)
        for claim in [self.claim("The heir may use the vehicle for three days if they inform the authority within thirty days.",
                                 whole, 5),  # "three days" is not "three months"
                      self.claim("The heir may use the vehicle for three months.", whole, 5)]:  # drops its quote's "within thirty days"
            with self.subTest(claim["text"]):
                self.assertEqual(verify_claims([claim], passages), [])

    def test_a_quote_cut_from_a_yes_or_no_answer_keeps_the_answer(self):
        passages = {5: "Can apprentices become EPF members?\n\nNo. But, when he ceases to be an apprentice he should be enrolled immediately.",
                    6: "Are pensions payable across India?\n\nYes",
                    7: "Pension rules\n\nYes"}
        cut = self.claim("Apprentices can become EPF members.", "when he ceases to be an apprentice he should be enrolled immediately", 5)
        self.assertEqual(verify_claims([cut], passages), [])
        whole = self.claim("Apprentices cannot become EPF members, but must be enrolled as soon as they stop being apprentices.",
                           "No. But, when he ceases to be an apprentice he should be enrolled immediately", 5)
        self.assertEqual(len(verify_claims([whole], passages)), 1)
        # A bare "Yes" means something only directly under its question.
        self.assertEqual(len(verify_claims([self.claim("Pensions are payable across India.", "Yes", 6)], passages)), 1)
        self.assertEqual(verify_claims([self.claim("Pensions are payable across India.", "Yes", 7)], passages), [])
        # A word that only starts like one is not an answer: "Nomination ..." is quoted from anywhere.
        nomination = {8: "Nomination facility ensures smooth settlement in case of death."}
        self.assertEqual(len(verify_claims([self.claim("Nomination ensures smooth settlement.", "ensures smooth settlement in case of death",
                                                       8)], nomination)), 1)

    def test_a_fee_for_a_test_duplicate_or_renewal_comes_from_a_row_about_one(self):
        test_row = ("10. Conducting test of a vehicle for grant or renewal of certificate of fitness: (a) Motorcycle (i) Manual: "
                    "Rupees Two Hundred Only (ii) Automated: Rupees Four Hundred Only 62(2) ---")
        certificate_row = "11. Grant or renewal of certificate of fitness for motor vehicle Rupees Two Hundred Only. 62(2) ---"
        passages = {5: f"10. Conducting test of a vehicle for grant or renewal of certificate of fitness:\n\n{test_row}\n\n{certificate_row}"}
        wrong = self.claim("The fitness test fee for a motorcycle is Rupees Two Hundred Only.", certificate_row, 5)
        self.assertEqual(verify_claims([wrong], passages), [])  # item 10's heading above is not item 11's
        kept = [self.claim("The fitness test fee for a motorcycle is Rupees Two Hundred Only (manual) or Rupees Four Hundred "
                           "Only (automated).", test_row, 5),
                self.claim("Renewing a certificate of fitness costs Rupees Two Hundred Only.", certificate_row, 5)]
        self.assertEqual(len(verify_claims(kept, passages)), 2)
        # A heading directly above the amount names its service.
        listed = {6: "Fee for a duplicate licence:\n\nRs. 200.00/- payable at the RTO."}
        self.assertEqual(len(verify_claims([self.claim("A duplicate licence costs Rs. 200.", "Rs. 200.00/- payable at the RTO", 6)],
                                           listed)), 1)

    def test_number_words_without_a_unit_are_not_numbers(self):
        passages = {5: "ITR-1 has five pre-filed sections that need to be validated.\n\nYou have two options to select the "
                       "type of form.\n\nLook for your CAN using any of the six fields provided.\n\nThe steps are detailed below one by one.\n\n"
                       "Penalty days are counted from the date of expiry."}
        for text, quote in [("ITR-1 has five pre-filed sections to validate.", "ITR-1 has five pre-filed sections that need to be validated"),
                            ("ITR-1 has six pre-filed sections to validate.", "ITR-1 has five pre-filed sections that need to be validated"),
                            ("There are two options for the type of form.", "You have two options to select the type of form"),
                            ("Search using any of the six fields.", "Look for your CAN using any of the six fields provided"),
                            ("The steps are explained one by one.", "The steps are detailed below one by one"),
                            ("Penalty days count from the date of expiry.", "Penalty days are counted from the date of expiry"),
                            ("Validate the pre-filed sections of ITR-1.", "ITR-1 has five pre-filed sections that need to be validated")]:
            with self.subTest(text):
                # A bare count is descriptive, not a checked constraint ("six sections" against "five" is a known gap).
                self.assertEqual(len(verify_claims([self.claim(text, quote, 5)], passages)), 1)

    def test_rc_and_dl_name_the_documents_they_abbreviate(self):
        rc = "4. Issue or renewal of certificate of registration and assignment of new registration mark"
        passages = {
            1: "11. Grant or renewal of certificate of fitness for motor vehicle Rupees Two Hundred Only. 62(2) ---",
            2: f"{rc}:\n\n{rc}: (b) Motor cycle Rupees Three Hundred Only 47(1) ---",
            3: "5. Issue of duplicate certificate of registration Half of the fee mentioned against Serial No.4 53(2) ---",
            4: "Attested photocopies of DL if available in case of loss of licence.",
            5: "8 Renewal of driving licence Rs. 200.00/-",
        }
        fitness = "11. Grant or renewal of certificate of fitness for motor vehicle Rupees Two Hundred Only"

        def kept(text, quote, chunk_id):
            return len(verify_claims([self.claim(text, quote, chunk_id)], passages)) == 1

        # A fitness certificate's fee is not an RC's or a DL's fee.
        for text in ["The fee to renew your vehicle RC is Rupees Two Hundred Only.", "The RC renewal fee for a car is Rupees Two Hundred Only.",
                     "The DL renewal fee is Rupees Two Hundred Only."]:
            with self.subTest(text):
                self.assertFalse(kept(text, fitness, 1))
        for text, quote, chunk_id in [
            ("Renewing the RC of a motorcycle costs Rupees Three Hundred Only.", f"{rc}: (b) Motor cycle Rupees Three Hundred Only", 2),
            ("A duplicate RC costs half of the fee mentioned against Serial No. 4.",
             "5. Issue of duplicate certificate of registration Half of the fee mentioned against Serial No.4", 3),
            ("Bring attested photocopies of your DL if it was lost.", "Attested photocopies of DL if available in case of loss of licence", 4),
            ("Renewing a DL costs Rs. 200.", "8 Renewal of driving licence Rs. 200.00/-", 5),
            ("The fitness certificate fee is Rupees Two Hundred Only.", fitness, 1),
        ]:
            with self.subTest(text):
                self.assertTrue(kept(text, quote, chunk_id))
        # Without an amount, "RC" names the procedure a document list belongs to, not the document a claim is about.
        documents = {6: "Application in Form 25\n\nPollution under control certificate\n\nInsurance certificate*"}
        for text, quote in [("The documents required to renew your vehicle RC include the application in Form 25.", "Application in Form 25"),
                            ("The documents required to renew your vehicle RC include the insurance certificate.", "Insurance certificate*")]:
            with self.subTest(text):
                self.assertEqual(len(verify_claims([self.claim(text, quote, 6)], documents)), 1)

    def test_form_and_return_numbers_are_names_not_quantities(self):
        passages = {
            1: "3.2 Who can use it?\n\nITR-1 can be filed by a Resident Individual whose:\n\nTotal income does not exceed ₹ 50 lakh during the FY",
            2: "Citizen, can enroll himself/herself as General Voter and fill Form 6 online at National Voters' Service Portal.",
            3: "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the "
               "transfer of ownership shall be made by the transferee in Form 30",
            4: "Fill Form-8 for correction of entries.",
            5: "Pay appropriate fee and tax as specified in rule 81 of the Central Motor Vehicle Rules 1989",
        }
        limit, form6 = "Total income does not exceed ₹ 50 lakh during the FY", "fill Form 6 online at National Voters' Service Portal"
        transfer = ("within fourteen days of the transfer, application for the transfer of ownership shall be made by the transferee "
                    "in Form 30")
        rule = "Pay appropriate fee and tax as specified in rule 81 of the Central Motor Vehicle Rules 1989"

        def kept(text, quote, chunk_id):
            return len(verify_claims([self.claim(text, quote, chunk_id)], passages)) == 1

        for text, quote, chunk_id in [
            # The form named by the heading the quote sits under, not a quantity of one.
            ("ITR-1 can be filed when total income does not exceed ₹ 50 lakh during the FY.", limit, 1),
            ("Fill Form 6 online at the National Voters' Service Portal.", form6, 2),
            ("Apply within 14 days of the transfer in Form 30.", transfer, 3),
            ("Fill Form 8 to correct entries.", "Fill Form-8 for correction of entries", 4),
            ("Pay the fee and tax specified in Rule 81 of the Central Motor Vehicle Rules 1989.", rule, 5),
            ("The fee is set by the Central Motor Vehicle Rules 1989.", rule, 5),  # a year stays a number
        ]:
            with self.subTest(text):
                self.assertTrue(kept(text, quote, chunk_id))
        for text, quote, chunk_id in [
            ("ITR-2 can be filed when total income does not exceed ₹ 50 lakh during the FY.", limit, 1),
            ("Fill Form 7 online at the National Voters' Service Portal.", form6, 2),
            ("Fill Form 6A online at the National Voters' Service Portal.", form6, 2),  # 6A is not 6
            ("Apply within thirty days of the transfer in Form 30.", transfer, 3),  # "Form 30" is not 30 days
            ("Apply within 30 days of the transfer in Form 30.", transfer, 3),
            ("Pay the fee and tax specified in Rule 82 of the Central Motor Vehicle Rules 1989.", rule, 5),
            ("ITR-1 can be filed when total income does not exceed ₹ 60 lakh during the FY.", limit, 1),  # amounts still checked
            ("ITR-1 can be filed when total income exceeds ₹ 50 lakh during the FY.", limit, 1),  # negation still checked
        ]:
            with self.subTest(text):
                self.assertFalse(kept(text, quote, chunk_id))

    def test_drops_repeated_claims(self):
        claim = self.claim("Pay Rs 1,500 online.", "fee for a fresh passport of 36 pages is Rs 1,500")
        self.assertEqual(len(verify_claims([claim, dict(claim)], self.passages)), 1)

    def test_drops_unsupported_claims(self):
        cases = {
            "fabricated quote": self.claim("Pay online.", "the fee can be paid at any bank branch"),
            "wrong passage": self.claim("Bring address proof.", "Applicants must carry proof of address", 1),
            "unknown passage": self.claim("Pay online.", "payable online at the portal", 99),
            "invented number": self.claim("Pay Rs 2,000 online.", "fee for a fresh passport of 36 pages"),
            "too short quote": self.claim("Pay online.", "payable online"),
            "negation added": self.claim("You cannot pay online.", "is Rs 1,500 payable online"),
            "negation dropped": self.claim(
                "You can use online services.", "registered mobile number cannot use online services", 3
            ),
            "missing text": {"quote": "fee for a fresh passport of 36 pages", "chunk_id": 1},
            "string id": self.claim("Pay.", "fee for a fresh passport of 36 pages", "1"),
            "not an object": "Pay Rs 1,500",
        }
        for name, claim in cases.items():
            with self.subTest(name):
                self.assertEqual(verify_claims([claim], self.passages), [])
        self.assertEqual(verify_claims("not a list", self.passages), [])


@patch("backend.rag.call_qwen")
class CheckClaimsTest(unittest.TestCase):
    """The model's second reading: meaning, conditions, applicant and labels."""

    chunks = [ProcedureChunk(id=1, content=FEE), ProcedureChunk(id=2, content=DOCS), ProcedureChunk(id=3, content=OLD_FEE)]
    claims = [{"text": "Pay Rs 1,500 online.", "chunk_id": 1, "quote": "is Rs 1,500 payable online"},
              {"text": "Bring address proof.", "chunk_id": 2, "quote": "carry proof of address and proof"}]

    def test_keeps_only_the_claims_judged_correct_and_reports_completeness(self, llm):
        llm.side_effect = [json.dumps({"correct": [2], "complete": False})]
        kept, complete = check_claims("What does it cost?", self.claims, self.chunks)

        self.assertEqual((kept, complete), ([self.claims[1]], False))
        prompt = llm.call_args_list[0].args[0]
        self.assertIn("Citizen question: What does it cost?", prompt)
        self.assertIn("1. Claim: Pay Rs 1,500 online.", prompt)
        self.assertIn(FEE, prompt)
        self.assertNotIn(OLD_FEE, prompt)  # only the cited passages

    def test_nothing_correct_is_never_complete(self, llm):
        llm.return_value = json.dumps({"correct": [], "complete": True})
        self.assertEqual(check_claims("Fee?", self.claims, self.chunks), ([], False))

    def test_malformed_output_is_a_service_error_and_no_claims_need_no_call(self, llm):
        for output in ["not json", "[]", json.dumps({"correct": "1", "complete": True}), json.dumps({"correct": [1]})]:
            with self.subTest(output=output):
                llm.return_value = output
                with self.assertRaises(GuidanceError):
                    check_claims("Fee?", self.claims, self.chunks)
        llm.reset_mock()
        self.assertEqual(check_claims("Fee?", [], self.chunks), ([], False))
        llm.assert_not_called()


@patch("backend.rag.call_qwen", return_value=json.dumps({"correct": [1, 2], "complete": True}))
class ApplicantLimitTest(unittest.TestCase):
    """A fee the official text limits to an organisation is only for an asker who names it."""

    chunks = [ProcedureChunk(id=1, content="Issue of duplicate licence to a school or establishment Rs. 5000.00/-"),
              ProcedureChunk(id=2, content="An appeal against the orders of licensing authority Rs. 500.00/-")]
    school = {"text": "A duplicate licence costs Rs. 5000.", "chunk_id": 1, "quote": "duplicate licence to a school or establishment Rs. 5000.00/-"}
    appeal = {"text": "An appeal costs Rs. 500.", "chunk_id": 2, "quote": "appeal against the orders of licensing authority Rs. 500.00/-"}

    def kept(self, question):
        return check_claims(question, [self.school, self.appeal], self.chunks)[0]

    def test_a_citizen_asking_for_themselves_never_gets_an_organisation_s_fee(self, llm):
        self.assertEqual(self.kept("What is the fee for a duplicate driving licence?"), [self.appeal])

    def test_a_driving_school_asking_for_itself_keeps_its_fee(self, llm):
        self.assertEqual(self.kept("What is the duplicate licence fee for my driving school?"), [self.school, self.appeal])

    def test_a_fee_the_text_does_not_limit_to_an_applicant_type_is_kept(self, llm):
        self.assertEqual(self.kept("How much does an appeal cost?"), [self.appeal])
        describes = {"text": "EPS covers employees of establishments.", "chunk_id": 2,
                     "quote": "eligible employees of establishments covered under the Act"}
        self.assertEqual(check_claims("Who gets EPS?", [describes], self.chunks)[0], [describes])  # "of", not "to"


class GuidanceApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.procedure = self.add("Passport", [FEE, DOCS, OLD_FEE])
        self.other = self.add("Aadhaar", ["Aadhaar address can be updated online for Rs 50."])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def add(self, name, passages):
        procedure = Procedure(
            name=name,
            summary=f"{name} summary.",
            source_url=f"https://example.gov.in/{name}",
            source_text="\n\n".join(passages),
            structured_data={"eligibility": None, "steps": ["One"]},
        )
        self.session.add(procedure)
        self.session.flush()
        for index, passage in enumerate(passages):
            self.session.add(
                ProcedureChunk(
                    procedure_id=procedure.id, chunk_index=index, content=passage, embedding=unit_vector(index)
                )
            )
        self.session.flush()
        return procedure

    def chunk_ids(self):
        rows = self.session.query(ProcedureChunk).filter_by(procedure_id=self.procedure.id)
        return {row.content: row.id for row in rows}

    def ask(self, model_output, question="How much does a passport cost?"):
        self.llm.return_value = json.dumps(model_output) if not isinstance(model_output, str) else model_output
        return self.client.post(
            "/api/guidance", json={"procedure_id": self.procedure.id, "question": question}
        )

    def test_returns_verified_steps_with_citations_and_official_link(self):
        ids = self.chunk_ids()
        response = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Bring proof of address.", "chunk_id": ids[DOCS], "quote": "carry proof of address and proof"},
            ],
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["insufficient_evidence"])
        self.assertEqual([c["chunk_id"] for c in body["claims"]], [ids[FEE], ids[DOCS]])
        self.assertEqual(body["source_url"], "https://example.gov.in/Passport")
        self.assertEqual(body["omitted_claims"], 0)

    def test_removes_fabricated_claims_and_counts_them(self):
        ids = self.chunk_ids()
        body = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Applications close on 31 March.", "chunk_id": ids[FEE], "quote": "applications close on 31 March each year"},
            ],
        }).json()

        self.assertEqual(len(body["claims"]), 1)
        self.assertEqual(body["omitted_claims"], 1)

    def test_refuses_when_no_claim_survives_or_model_finds_no_answer(self):
        for output in (
            {"insufficient_evidence": False, "claims": [{"text": "Fee is Rs 900.", "chunk_id": 1, "quote": "fee is Rs 900 for everyone"}]},
            {"insufficient_evidence": True, "claims": []},
            {"insufficient_evidence": True, "claims": [{"text": "x", "chunk_id": 1, "quote": "y"}]},
        ):
            with self.subTest(output=output):
                body = self.ask(output, "Can I get a passport delivered by drone?").json()
                self.assertTrue(body["insufficient_evidence"])
                self.assertEqual(body["claims"], [])

    def test_keeps_both_sides_of_conflicting_evidence(self):
        ids = self.chunk_ids()
        body = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "The fee is Rs 1,500.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Older guidance listed Rs 1,000.", "chunk_id": ids[OLD_FEE], "quote": "fresh passport was Rs 1,000"},
            ],
        }).json()

        self.assertEqual(len(body["claims"]), 2)

    def test_prompt_contains_only_this_procedures_evidence_and_question(self):
        self.ask({"insufficient_evidence": True, "claims": []}, "What documents do I need?")
        prompt = self.llm.call_args.args[0]

        self.assertIn("What documents do I need?", prompt)
        self.assertIn(DOCS, prompt)
        self.assertNotIn("Aadhaar address", prompt)
        self.assertIn("untrusted data", prompt)
        self.assertTrue(self.embed.call_args.kwargs["query"])

    def test_procedure_without_evidence_is_refused_without_calling_the_model(self):
        empty = Procedure(
            name="Empty", summary="s", source_url="https://example.gov.in/e",
            source_text="t", structured_data={"eligibility": None, "steps": ["s"]},
        )
        self.session.add(empty)
        self.session.flush()

        response = self.client.post("/api/guidance", json={"procedure_id": empty.id, "question": "fee?"})

        self.assertTrue(response.json()["insufficient_evidence"])
        self.llm.assert_not_called()

    def test_a_page_naming_the_procedure_answers_when_its_own_page_cannot(self):
        table = self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter."])
        chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=table.id).one()
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": True, "claims": []}),
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "It costs Rs 1,500.", "chunk_id": chunk.id, "quote": "Passport of 36 pages costs Rs 1,500"}]}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Fee?"}).json()

        # The reply stays the passport's; the claim names the page it comes from.
        self.assertEqual((body["procedure_id"], body["source_url"]), (self.procedure.id, "https://example.gov.in/Passport"))
        self.assertEqual(body["claims"], [{"text": "It costs Rs 1,500.", "chunk_id": chunk.id, "quote": "Passport of 36 pages costs Rs 1,500",
                                           "procedure_id": table.id, "source_url": "https://example.gov.in/Fee table"}])
        # The Aadhaar page does not name the passport procedure, so it was never asked.
        self.assertEqual(self.llm.call_count, 2)
        self.assertNotIn("Aadhaar", self.llm.call_args.args[0])

    def test_the_second_reading_drops_misread_claims_and_flags_a_partial_answer(self):
        self.check.stop()
        ids = self.chunk_ids()
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "The extra fee is Rs 1,000.", "chunk_id": ids[OLD_FEE], "quote": "the application fee for a fresh passport was Rs 1,000"}]}),
            json.dumps({"correct": [1], "complete": False}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Fee?"}).json()

        self.assertEqual([c["text"] for c in body["claims"]], ["Pay Rs 1,500 online."])
        self.assertEqual((body["omitted_claims"], body["partial"]), (1, True))

    def test_a_partial_answer_is_completed_by_a_page_naming_the_procedure(self):
        self.check.stop()
        table = self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter."])
        table_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=table.id).one()
        ids = self.chunk_ids()
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Bring address proof.", "chunk_id": ids[DOCS], "quote": "carry proof of address and proof"}]}),
            json.dumps({"correct": [1], "complete": False}),
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "It costs Rs 1,500.", "chunk_id": table_chunk.id, "quote": "Passport of 36 pages costs Rs 1,500"}]}),
            json.dumps({"correct": [1], "complete": True}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Documents and fee?"}).json()

        self.assertEqual([c.get("procedure_id") for c in body["claims"]], [None, table.id])
        self.assertNotIn("partial", body)

    def test_a_fee_answer_without_an_amount_is_completed_with_only_this_procedures_row(self):
        self.check.stop()  # the model's own completeness judgement is what is tested
        permit = self.add("International Driving Permit", ["Fees as prescribed along with user charges."])
        table = self.add("Fee table", ["Issue of International Driving Permit Rs. 1000.00/-\n\nRenewal of driving licence Rs. 200.00/-"])
        permit_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=permit.id).one().id
        table_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=table.id).one().id
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Fees as prescribed along with user charges.", "chunk_id": permit_chunk,
                 "quote": "Fees as prescribed along with user charges"}]}),
            json.dumps({"correct": [1], "complete": True}),  # the model takes "as prescribed" for an answer
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "The permit costs Rs. 1000.", "chunk_id": table_chunk, "quote": "Issue of International Driving Permit Rs. 1000.00/-"},
                {"text": "Renewal costs Rs. 200.", "chunk_id": table_chunk, "quote": "Renewal of driving licence Rs. 200.00/-"}]}),
            json.dumps({"correct": [1, 2], "complete": True}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": permit.id, "question": "And how much does it cost?"}).json()

        self.assertEqual([(c["text"], c.get("procedure_id")) for c in body["claims"]],
                         [("Fees as prescribed along with user charges.", None), ("The permit costs Rs. 1000.", table.id)])
        self.assertEqual(body["omitted_claims"], 1)  # the renewal row is another procedure's fee

    def test_a_fee_table_stored_cell_by_cell_still_completes_the_answer(self):
        self.check.stop()
        permit = self.add("International Driving Permit", ["Fees as prescribed along with user charges."])
        table = self.add("Fee table", ["Issue of International Driving Permit\n\nRs. 1000.00/-\n\nRenewal of driving licence\n\nRs. 200.00/-"])
        permit_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=permit.id).one().id
        table_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=table.id).one().id
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Fees as prescribed along with user charges.", "chunk_id": permit_chunk,
                 "quote": "Fees as prescribed along with user charges"}]}),
            json.dumps({"correct": [1], "complete": True}),
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "The permit costs Rs. 1000.", "chunk_id": table_chunk, "quote": "Issue of International Driving Permit Rs. 1000.00/-"},
                {"text": "Renewal costs Rs. 200.", "chunk_id": table_chunk, "quote": "Renewal of driving licence Rs. 200.00/-"}]}),
            json.dumps({"correct": [1, 2], "complete": True}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": permit.id, "question": "What is the fee?"}).json()
        self.assertEqual([c["text"] for c in body["claims"]], ["Fees as prescribed along with user charges.", "The permit costs Rs. 1000."])

    def test_a_fee_answer_is_complete_when_the_service_is_free_and_partial_when_no_amount_is_published(self):
        self.check.stop()  # the model's own completeness judgement is what is tested
        free = self.add("Aadhaar enrolment", ["Aadhaar enrolment at the post office is free of cost."])
        free_chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=free.id).one().id
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Enrolment is free.", "chunk_id": free_chunk, "quote": "Aadhaar enrolment at the post office is free of cost"}]}),
            json.dumps({"correct": [1], "complete": True}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": free.id, "question": "Is there a fee for enrolment?"}).json()
        self.assertNotIn("partial", body)
        self.assertEqual(self.llm.call_count, 2)  # no other page is asked

        prescribed = self.add("Duplicate licence", ["Fees as prescribed along with user charges."])
        chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=prescribed.id).one().id
        self.llm.reset_mock()
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "Fees as prescribed along with user charges.", "chunk_id": chunk, "quote": "Fees as prescribed along with user charges"}]}),
            json.dumps({"correct": [1], "complete": True}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": prescribed.id, "question": "What is the fee?"}).json()
        self.assertTrue(body["partial"])  # no approved page states the amount: said, never invented
        self.assertEqual([c["text"] for c in body["claims"]], ["Fees as prescribed along with user charges."])

    def test_only_the_related_page_s_passages_naming_the_procedure_are_used(self):
        table = self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter.",
                                       "Duplicate licence to a driving school costs Rs 5,000."])
        self.llm.return_value = json.dumps({"insufficient_evidence": True, "claims": []})
        self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Duplicate fee?"})

        related_prompt = self.llm.call_args_list[1].args[0]
        self.assertIn("Issue of a Passport", related_prompt)
        self.assertNotIn("driving school", related_prompt)

    def test_related_pages_are_not_asked_when_the_page_answers_or_nothing_names_it(self):
        self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter."])
        ids = self.chunk_ids()
        self.ask({"insufficient_evidence": False, "claims": [
            {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"}]})
        self.assertEqual(self.llm.call_count, 1)

        self.llm.reset_mock()
        body = self.client.post("/api/guidance", json={"procedure_id": self.other.id, "question": "Fee?"}).json()
        self.assertEqual((body["procedure_id"], body["insufficient_evidence"]), (self.other.id, True))
        self.assertEqual(self.llm.call_count, 1)

    def test_errors(self):
        self.assertEqual(
            self.client.post("/api/guidance", json={"procedure_id": 999999, "question": "fee?"}).status_code, 404
        )
        for body in ({"procedure_id": "x", "question": "fee?"}, {"procedure_id": 1, "question": " "}):
            self.assertEqual(self.client.post("/api/guidance", json=body).status_code, 422)
        for failure in ("not json", json.dumps([1, 2]), json.dumps({"claims": []})):
            with self.subTest(failure=failure):
                self.assertEqual(self.ask(failure).status_code, 502)
        self.llm.side_effect = ExtractionError("Qwen extraction timed out.")
        response = self.ask({"insufficient_evidence": True})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The answer service is unavailable. Try again."})
        self.llm.side_effect = None
        self.embed.side_effect = EmbeddingError("down")
        self.assertEqual(self.ask({"insufficient_evidence": True}).status_code, 502)

    def test_counts_distinct_unsupported_claims_and_survives_malformed_ones(self):
        ids = self.chunk_ids()
        good = {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"}
        body = self.ask({"insufficient_evidence": False, "claims": [good, good, ["odd"], {"text": ["other"]}, {"text": None}]}).json()

        self.assertEqual([c["text"] for c in body["claims"]], ["Pay Rs 1,500 online."])
        self.assertEqual(body["omitted_claims"], 3)

    def test_writes_nothing(self):
        before = self.session.query(func.count(ProcedureChunk.id)).scalar()
        self.ask({"insufficient_evidence": True, "claims": []})
        self.assertEqual(self.session.query(func.count(ProcedureChunk.id)).scalar(), before)


LINK = "Existing PAN holders must link PAN with Aadhaar before filing the return."
BOTH_NAMES = "Enter your PAN and Aadhaar number on the portal."
ADDRESS = "Address update requests are verified at an Aadhaar Enrolment Centre."
STEP = "Upload the address proof after you sign in to the portal."
TAX_ORDER = "File the income tax return only after your PAN is linked with Aadhaar."


class RelationApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.pan = GuidanceApiTest.add(self, "PAN", [LINK, BOTH_NAMES])
        self.aadhaar = GuidanceApiTest.add(self, "Aadhaar", [ADDRESS, STEP])
        self.tax = GuidanceApiTest.add(self, "Income tax", [TAX_ORDER])
        self.unrelated = GuidanceApiTest.add(self, "Passport", [FEE])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def chunk(self, content):
        return self.session.query(ProcedureChunk).filter_by(content=content).one().id

    def claim(self, text, content, quote=None):
        return {"text": text, "chunk_id": self.chunk(content), "quote": quote or content.rstrip(".")}

    def ask(self, claims, ids=None, question="Which should I do first?"):
        self.llm.return_value = json.dumps({"insufficient_evidence": not claims, "claims": claims})
        ids = ids or [self.pan.id, self.aadhaar.id]
        return self.client.post("/api/relation", json={"procedure_ids": ids, "question": question})

    def test_keeps_an_explicitly_stated_relationship_as_official_text_with_its_source(self):
        body = self.ask([self.claim("You can reuse your Aadhaar address proof for PAN too.", LINK)]).json()

        self.assertFalse(body["insufficient_evidence"])
        self.assertEqual(body["claims"][0]["text"], LINK.rstrip("."))
        self.assertEqual(body["claims"][0]["procedure_id"], self.pan.id)
        self.assertEqual(body["claims"][0]["source_url"], self.pan.source_url)

    def test_rejects_relationships_the_quote_does_not_state(self):
        cases = {
            "order from an unrelated fact": self.claim("Update your Aadhaar address first, then link PAN.", ADDRESS),
            "reuse from an unrelated fact": self.claim("You can reuse the same address proof for PAN.", ADDRESS),
            "step inside one procedure": self.claim("Upload the address proof after you sign in.", STEP),
            "names both but states nothing": self.claim("Link PAN and Aadhaar first.", BOTH_NAMES),
            "inference with no relation words": self.claim("Your Aadhaar proof also works for PAN.", BOTH_NAMES),
        }
        for name, claim in cases.items():
            with self.subTest(name):
                self.assertEqual(self.ask([claim]).json(),
                                 {"insufficient_evidence": True, "claims": [], "omitted_claims": 1})

    def test_relates_three_procedures_with_each_quote_attributed_to_its_own_page(self):
        body = self.ask(
            [self.claim("Link PAN before filing.", LINK), self.claim("File after linking.", TAX_ORDER),
             self.claim("Verify at a centre first.", ADDRESS)],
            ids=[self.pan.id, self.aadhaar.id, self.tax.id],
        ).json()

        self.assertEqual([(c["text"], c["procedure_id"]) for c in body["claims"]],
                         [(LINK.rstrip("."), self.pan.id), (TAX_ORDER.rstrip("."), self.tax.id)])
        self.assertEqual(body["omitted_claims"], 1)

    def test_uses_only_the_requested_procedures_evidence(self):
        self.ask([])
        prompt = self.llm.call_args.args[0]
        self.assertIn(LINK, prompt)
        self.assertIn(ADDRESS, prompt)
        self.assertNotIn(FEE, prompt)
        self.assertIn("never combine separate facts", prompt)

        body = self.ask([self.claim("The passport fee is Rs 1,500.", FEE, "fee for a fresh passport of 36 pages is Rs 1,500")]).json()
        self.assertTrue(body["insufficient_evidence"])

    def test_rejects_bad_requests_and_reports_failures(self):
        self.assertEqual(self.ask([], ids=[self.pan.id]).status_code, 422)
        self.assertEqual(self.ask([], ids=[self.pan.id, 999999]).status_code, 404)
        self.llm.side_effect = ExtractionError("down")
        self.assertEqual(self.ask([]).status_code, 502)


EPF = "EPF members can withdraw the full balance at retirement after 58 years."
EPS = "EPS pays a monthly pension to members after 58 years of service."
EDLI = "EDLI pays an assurance benefit to the nominee if a member dies in service."


class ComparisonApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.epf = GuidanceApiTest.add(self, "Employees' Provident Fund Scheme", [EPF])
        self.eps = GuidanceApiTest.add(self, "Employees' Pension Scheme (EPS)", [EPS])
        self.edli = GuidanceApiTest.add(self, "Employees' Deposit Linked Insurance (EDLI)", [EDLI])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def chunk(self, content):
        return self.session.query(ProcedureChunk).filter_by(content=content).one().id

    def ask(self, claims, procedures, question="What is the difference between EPF and EPS?"):
        self.llm.return_value = json.dumps({"insufficient_evidence": not claims, "claims": claims})
        return self.client.post("/api/relation", json={"procedure_ids": [p.id for p in procedures], "question": question}).json()

    def test_each_point_is_verified_against_its_own_procedure(self):
        body = self.ask([
            {"text": "EPF allows full withdrawal at retirement.", "chunk_id": self.chunk(EPF), "quote": "can withdraw the full balance at retirement"},
            {"text": "EPS pays a monthly pension.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"},
            {"text": "Unlike the pension scheme, EPF pays a lump sum.", "chunk_id": self.chunk(EPF), "quote": "can withdraw the full balance at retirement"},
            {"text": "EPS pays a pension of Rs 7,500.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"},
        ], [self.epf, self.eps])

        self.assertTrue(body["comparison"])
        self.assertEqual([(c["text"], c["procedure_id"], c["source_url"]) for c in body["claims"]], [
            ("EPF allows full withdrawal at retirement.", self.epf.id, self.epf.source_url),
            ("EPS pays a monthly pension.", self.eps.id, self.eps.source_url),
        ])
        self.assertEqual(body["omitted_claims"], 2)

    def test_compares_three_procedures_from_their_own_passages_only(self):
        body = self.ask([{"text": "EDLI pays the nominee if a member dies in service.", "chunk_id": self.chunk(EDLI),
                          "quote": "pays an assurance benefit to the nominee"}],
                        [self.epf, self.eps, self.edli], "Explain EPF, EPS and EDLI and how they differ")
        prompt = self.llm.call_args.args[0]

        self.assertEqual([c["procedure_id"] for c in body["claims"]], [self.edli.id])
        self.assertIn("how several government schemes or procedures compare", prompt)
        for passage in (EPF, EPS, EDLI):
            self.assertIn(passage, prompt)

    def test_says_so_when_the_pages_do_not_support_a_comparison(self):
        self.assertEqual(self.ask([], [self.epf, self.eps]),
                         {"insufficient_evidence": True, "claims": [], "omitted_claims": 0, "comparison": True})

    def test_dependency_questions_keep_the_strict_relationship_rules(self):
        body = self.ask([{"text": "EPS pays a monthly pension.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"}],
                        [self.epf, self.eps], "Must I join EPF before EPS?")

        self.assertEqual(body, {"insufficient_evidence": True, "claims": [], "omitted_claims": 1})


class GuidancePromptTest(unittest.TestCase):
    def test_marks_passages_and_requires_quotes(self):
        chunk = ProcedureChunk(id=7, content="Official text.")
        prompt = build_guidance_prompt("Question?", [chunk])

        self.assertIn("--- PASSAGE 7 ---\nOfficial text.\n--- END PASSAGE 7 ---", prompt)
        self.assertIn("quote copied word for word", prompt)
        self.assertIn("insufficient_evidence", prompt)


if __name__ == "__main__":
    unittest.main()
