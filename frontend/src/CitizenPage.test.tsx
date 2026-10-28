import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CitizenPage from "./CitizenPage";
import * as api from "./api";

vi.mock("./api");
// The recorder itself is tested in VoiceInput.test.tsx; here it just hands over a transcript.
vi.mock("./VoiceInput", () => ({
  default: ({ onTranscript }: { onTranscript: (text: string) => void }) => (
    <button type="button" onClick={() => onTranscript("Passport renew pannanum")}>Speak your question</button>
  ),
}));

const passport = {
  id: 13,
  name: "Apply for a fresh passport",
  department: "Ministry of External Affairs",
  jurisdiction: null,
  summary: "Apply online through Passport Seva.",
};
const passportDetail = {
  ...passport,
  eligibility: "Indian citizens.",
  steps: ["Register on the portal.", "Fill the form.", "Book an appointment."],
  source_url: "https://www.passportindia.gov.in/psp/Apply",
};
const uk = { ...passport, id: 20, name: "Apply for a UK passport", summary: "UK service." };

function search(text = "My passport expired") {
  fireEvent.change(screen.getByLabelText("Your situation or question"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

// A later question goes through the same box and the same identification as the first.
function ask(text = "Which documents do I need?") {
  search(text);
}

// The nth question-and-answer block on the page, oldest first.
const exchange = (index: number) => document.querySelectorAll<HTMLElement>("section.exchange")[index];

// The Send button is disabled while a question is being searched or answered.
const settled = () =>
  waitFor(() => expect(screen.getByRole("button", { name: "Send" }).hasAttribute("disabled")).toBe(false));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getProcedure).mockResolvedValue(passportDetail);
  vi.mocked(api.askGuidance).mockResolvedValue({
    procedure_id: 13,
    source_url: passportDetail.source_url,
    insufficient_evidence: true,
    claims: [],
    omitted_claims: 0,
  });
});
afterEach(cleanup);

describe("citizen workflow", () => {
  it("does not search for a blank situation", () => {
    render(<CitizenPage />);
    search("   ");
    expect(api.identifyProcedure).not.toHaveBeenCalled();
  });

  it("shows the matched procedure with steps, eligibility, link and disclaimer", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport], named: true });
    render(<CitizenPage />);
    search();

    expect(await screen.findByRole("heading", { name: passport.name })).toBeTruthy();
    const card = screen.getByRole("heading", { name: passport.name }).closest("section")!;
    const steps = Array.from(card.querySelectorAll("ol > li")).map((item) => item.textContent);
    expect(steps).toEqual(passportDetail.steps);
    expect(screen.getByText("Indian citizens.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "official page" }).getAttribute("href")).toBe(
      passportDetail.source_url,
    );
    expect(screen.getByText(/does not submit applications/)).toBeTruthy();
    expect(api.identifyProcedure).toHaveBeenCalledWith("My passport expired", "en");
    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledWith(13, "My passport expired", "en"));
  });

  it("hides eligibility when the approved record has none", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport], named: true });
    vi.mocked(api.getProcedure).mockResolvedValue({ ...passportDetail, eligibility: null });
    render(<CitizenPage />);
    search();

    await screen.findByRole("heading", { name: passport.name });
    expect(screen.queryByText("Who can apply")).toBeNull();
  });

  it("does not present a procedure the citizen did not name when its page answers nothing", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    render(<CitizenPage />);
    search("How do I get a marriage certificate?");

    expect(await screen.findByText(/No approved official information answers this question yet/)).toBeTruthy();
    expect(screen.queryByRole("heading", { name: passport.name })).toBeNull();
    expect(screen.queryByText(/does not answer this question/)).toBeNull();
    // Nothing is left open: the next question is searched afresh.
    await settled();
    search("How do I renew my passport?");
    await waitFor(() => expect(api.identifyProcedure).toHaveBeenCalledTimes(2));
  });

  it("shows a procedure the citizen did not name once its page answers", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: false, omitted_claims: 0,
      claims: [{ text: "Register on the portal first.", chunk_id: 1, quote: "Register on the portal" }],
    });
    render(<CitizenPage />);
    search();

    expect(await screen.findByText("Register on the portal first.")).toBeTruthy();
    expect(screen.getByRole("heading", { name: passport.name })).toBeTruthy();
  });

  it("lets the citizen choose between plausible procedures", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "ambiguous", candidates: [passport, uk] });
    render(<CitizenPage />);
    search("How do I apply for a passport?");

    expect(await screen.findByText("Which of these fits your situation?")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Choose" })[1]);

    await screen.findByRole("heading", { name: passport.name });
    expect(api.getProcedure).toHaveBeenCalledWith(20);
    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledWith(20, "How do I apply for a passport?", "en"));
    fireEvent.click(screen.getByRole("button", { name: "Back to choices" }));
    expect(screen.getByText("Which of these fits your situation?")).toBeTruthy();
  });

  it("explains when nothing matches", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "no_match", candidates: [] });
    render(<CitizenPage />);
    search("Biryani recipe");

    expect(await screen.findByText(/don't have an approved procedure/)).toBeTruthy();
    expect(api.getProcedure).not.toHaveBeenCalled();
  });

  it("shows errors and retries without losing the question", async () => {
    vi.mocked(api.identifyProcedure)
      .mockRejectedValueOnce(new Error("The search service is unavailable. Try again."))
      .mockResolvedValueOnce({ status: "matched", candidates: [passport], named: true });
    render(<CitizenPage />);
    search();

    expect((await screen.findByRole("alert")).textContent).toContain("search service is unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    await screen.findByRole("heading", { name: passport.name });
    expect(api.identifyProcedure).toHaveBeenNthCalledWith(2, "My passport expired", "en");
  });

  it("disables searching while a request is in progress", async () => {
    vi.mocked(api.identifyProcedure).mockReturnValue(new Promise(() => {}));
    render(<CitizenPage />);
    search();

    expect(screen.getByRole("button", { name: "Searching…" }).hasAttribute("disabled")).toBe(true);
  });
});

describe("later questions", () => {
  beforeEach(async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport], named: true });
    render(<CitizenPage />);
    search();
    await screen.findByRole("heading", { name: passport.name });
    await settled();
    vi.mocked(api.askGuidance).mockClear();
    vi.mocked(api.identifyProcedure).mockClear();
  });

  it("shows verified answers with their official quotes", async () => {
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13,
      source_url: passportDetail.source_url,
      insufficient_evidence: false,
      claims: [{ text: "Carry proof of address.", chunk_id: 4, quote: "carry proof of address and date of birth" }],
      omitted_claims: 1,
    });
    ask();

    expect(await screen.findByText("Carry proof of address.")).toBeTruthy();
    expect(screen.getByText("carry proof of address and date of birth")).toBeTruthy();
    expect(screen.getByText(/1 statement\(s\) were left out/)).toBeTruthy();
    expect(api.askGuidance).toHaveBeenCalledWith(13, "Which documents do I need?", "en");
  });

  it("refuses honestly when the official text has no answer", async () => {
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13,
      source_url: passportDetail.source_url,
      insufficient_evidence: true,
      claims: [],
      omitted_claims: 0,
    });
    ask("Can it be delivered by drone?");

    expect(await screen.findByText(/does not answer this question/)).toBeTruthy();
  });

  it("keeps the earlier exchange: each question is identified and answered on its own", async () => {
    vi.mocked(api.askGuidance).mockResolvedValueOnce({
      procedure_id: 13,
      source_url: passportDetail.source_url,
      insufficient_evidence: false,
      claims: [{ text: "Carry proof of address.", chunk_id: 4, quote: "carry proof of address and date of birth" }],
      omitted_claims: 0,
    });
    ask("Which documents do I need?");
    await screen.findByText("Carry proof of address.");
    await settled();
    ask("Is there a fee?");

    await waitFor(() => expect(screen.getByText(/does not answer this question/)).toBeTruthy());
    expect(screen.getByText("Carry proof of address.")).toBeTruthy();
    expect(screen.getByText("My passport expired")).toBeTruthy();
    expect(screen.getByText("Is there a fee?")).toBeTruthy();
    expect(document.querySelectorAll("section.exchange")).toHaveLength(3);
    expect(api.identifyProcedure).toHaveBeenNthCalledWith(1, "Which documents do I need?", "en");
    expect(api.identifyProcedure).toHaveBeenNthCalledWith(2, "Is there a fee?", "en");
    expect(api.askGuidance).toHaveBeenNthCalledWith(1, 13, "Which documents do I need?", "en");
    expect(api.askGuidance).toHaveBeenNthCalledWith(2, 13, "Is there a fee?", "en");
  });

  it("retries a failed answer by asking the same question again", async () => {
    vi.mocked(api.askGuidance)
      .mockRejectedValueOnce(new Error("The answer service is unavailable. Try again."))
      .mockResolvedValueOnce({
        procedure_id: 13,
        source_url: passportDetail.source_url,
        insufficient_evidence: true,
        claims: [],
        omitted_claims: 0,
      });
    ask();

    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));

    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledTimes(2));
    expect(api.askGuidance).toHaveBeenLastCalledWith(13, "Which documents do I need?", "en");
    // The retry repeats the whole question, identification included.
    expect(api.identifyProcedure).toHaveBeenCalledTimes(2);
    expect(api.identifyProcedure).toHaveBeenLastCalledWith("Which documents do I need?", "en");
  });
});

describe("several needs in one message", () => {
  const aadhaar = { ...passport, id: 30, name: "Updating Data on Aadhaar", summary: "UIDAI service." };
  const verified = (id: number, text: string) => ({
    procedure_id: id,
    source_url: `https://example.gov.in/${id}`,
    insufficient_evidence: false,
    claims: [{ text, chunk_id: id, quote: `${text} quoted` }],
    omitted_claims: 0,
  });
  const multiple = {
    status: "multiple" as const,
    candidates: [],
    needs: [
      { phrases: ["renew my passport"], question: "How do I renew my passport?", status: "matched" as const, candidates: [passport] },
      { phrases: ["update my Aadhaar address"], question: "How do I update my Aadhaar address?", status: "matched" as const, candidates: [aadhaar] },
      { phrases: ["get a driving licence"], question: "How do I get a driving licence?", status: "no_match" as const, candidates: [] },
      { phrases: ["get a passport"], question: "How do I get a passport?", status: "ambiguous" as const, candidates: [passport, uk] },
    ],
    pending: [{ phrase: "get a voter ID", question: "How do I get a voter ID?" }],
    relation_question: "Which should I do first?",
  };

  beforeEach(() => {
    vi.mocked(api.identifyProcedure).mockResolvedValue(multiple);
    vi.mocked(api.askGuidance).mockImplementation(async (id) => verified(id, `Answer for ${id}.`));
    vi.mocked(api.askRelation).mockResolvedValue({
      insufficient_evidence: false,
      claims: [{ text: "Link PAN before filing.", chunk_id: 9, quote: "link PAN before filing", procedure_id: 30, source_url: "https://example.gov.in/30" }],
      omitted_claims: 0,
    });
  });

  it("answers every matched need in one response and connects them only through verified claims", async () => {
    render(<CitizenPage />);
    search("I want to renew my passport, update my Aadhaar address, get a driving licence and a passport. Which should I do first?");

    expect(await screen.findByText("Answer for 30.")).toBeTruthy();
    expect(screen.getByText("Answer for 13.")).toBeTruthy();
    expect(screen.getByText("I understood your request as:")).toBeTruthy();
    expect(screen.getByText("get a voter ID")).toBeTruthy();
    expect(screen.getByText(/don't have an approved procedure for this yet/)).toBeTruthy();
    expect(api.askGuidance).toHaveBeenNthCalledWith(1, 13, "How do I renew my passport?");
    expect(api.askGuidance).toHaveBeenNthCalledWith(2, 30, "How do I update my Aadhaar address?");
    expect(api.askGuidance).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Link PAN before filing.")).toBeTruthy();
    expect(api.askRelation).toHaveBeenCalledWith([13, 30], "Which should I do first?");
    expect(screen.queryAllByRole("heading", { level: 2 })).toHaveLength(0);
    expect(document.querySelectorAll("section.exchange")).toHaveLength(1);

    fireEvent.click(screen.getAllByRole("button", { name: "Choose" })[1]);
    expect(await screen.findByText("Answer for 20.")).toBeTruthy();
  });

  it("says when the sources do not establish a relationship", async () => {
    vi.mocked(api.askRelation).mockResolvedValue({ insufficient_evidence: true, claims: [], omitted_claims: 2 });
    render(<CitizenPage />);
    search("I want to renew my passport and update my Aadhaar address. Which should I do first?");

    expect(await screen.findByText(/do not confirm an order, dependency or document reuse/)).toBeTruthy();
  });

  it("keeps other answers when one fails and retries only that one", async () => {
    vi.mocked(api.askGuidance)
      .mockRejectedValueOnce(new Error("The answer service is unavailable. Try again."))
      .mockImplementation(async (id) => verified(id, `Answer for ${id}.`));
    render(<CitizenPage />);
    search("I want to renew my passport and update my Aadhaar address.");

    expect(await screen.findByText("Answer for 30.")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("answer service is unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Answer for 13.")).toBeTruthy();
    expect(api.askGuidance).toHaveBeenLastCalledWith(13, "How do I renew my passport?");
  });

  it("lets the citizen send needs over the limit next", async () => {
    render(<CitizenPage />);
    search("I want to renew my passport, update my Aadhaar address and get a voter ID.");
    fireEvent.click(await screen.findByRole("button", { name: "Ask about these next" }));

    expect((screen.getByLabelText("Your situation or question") as HTMLTextAreaElement).value).toBe("How do I get a voter ID?");
  });

  it("identifies a later question on its own instead of routing it through the earlier procedures", async () => {
    render(<CitizenPage />);
    search("I want to renew my passport and update my Aadhaar address.");
    await screen.findByText("Answer for 30.");
    await settled();
    vi.mocked(api.askGuidance).mockClear();
    vi.mocked(api.askRelation).mockClear();

    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [aadhaar] });
    search("Tell me more about the Aadhaar update");
    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledWith(30, "Tell me more about the Aadhaar update", "en"));
    await settled();
    expect(api.identifyProcedure).toHaveBeenLastCalledWith("Tell me more about the Aadhaar update", "en");

    vi.mocked(api.askGuidance).mockClear();
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "no_match", candidates: [] });
    search("Can I reuse my documents?");
    expect(await screen.findByText(/don't have an approved procedure/)).toBeTruthy();
    await settled();
    expect(api.askGuidance).not.toHaveBeenCalled();
    expect(api.askRelation).not.toHaveBeenCalled(); // no relationship check from the earlier matched ids
  });

  it("shows a comparison point by point with each procedure named and missing details stated", async () => {
    const epf = { ...passport, id: 36, name: "Employees' Provident Fund Scheme", summary: "EPF." };
    const eps = { ...passport, id: 37, name: "Employees' Pension Scheme (EPS)", summary: "EPS." };
    vi.mocked(api.identifyProcedure).mockResolvedValue({
      status: "multiple",
      candidates: [],
      needs: [
        { phrases: ["EPF"], question: "What is EPF?", status: "matched", candidates: [epf] },
        { phrases: ["EPS"], question: "What is EPS?", status: "matched", candidates: [eps] },
      ],
      pending: [],
      relation_question: "What is the difference between EPF and EPS?",
    });
    vi.mocked(api.askRelation).mockResolvedValue({
      insufficient_evidence: false,
      comparison: true,
      claims: [{ text: "Full withdrawal at retirement.", chunk_id: 1, quote: "withdraw the full balance", procedure_id: 36, source_url: "https://www.epfo.gov.in/epf-scheme" }],
      omitted_claims: 0,
    });
    render(<CitizenPage />);
    search("What is the difference between EPF and EPS?");

    expect(await screen.findByText("Full withdrawal at retirement.")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "How they compare (official text)" })).toBeTruthy();
    expect(screen.getByText("Employees' Provident Fund Scheme:")).toBeTruthy();
    expect(screen.getByText(/No comparable details were found for: Employees' Pension Scheme \(EPS\)/)).toBeTruthy();
    expect(api.askRelation).toHaveBeenCalledWith([36, 37], "What is the difference between EPF and EPS?");
  });
});

describe("Tamil questions", () => {
  it("searches and answers the English query while showing the citizen's own words", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({
      status: "matched", candidates: [passport], normalized_query: "How do I renew my passport?",
    });
    render(<CitizenPage />);
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ta" } });
    expect(screen.getByText(/Answers are shown in English/)).toBeTruthy();
    search("Enakku passport renew pannanum");

    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledWith(13, "How do I renew my passport?", "en"));
    expect(api.identifyProcedure).toHaveBeenCalledWith("Enakku passport renew pannanum", "ta");
    expect(screen.getByText("Enakku passport renew pannanum")).toBeTruthy();
    expect(screen.getByText("Searched as: How do I renew my passport?")).toBeTruthy();
  });

  it("puts the transcript in the question box to edit, and sends only what the citizen sends", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "no_match", candidates: [] });
    render(<CitizenPage />);
    const box = screen.getByLabelText("Your situation or question") as HTMLTextAreaElement;
    fireEvent.click(screen.getByRole("button", { name: "Speak your question" }));

    expect(box.value).toBe("Passport renew pannanum");
    expect(api.identifyProcedure).not.toHaveBeenCalled();
    fireEvent.change(box, { target: { value: "Enakku passport renew pannanum" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(api.identifyProcedure).toHaveBeenCalledWith("Enakku passport renew pannanum", "en"));
  });

  it("asks which service is meant instead of guessing", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({
      status: "no_match", candidates: [], clarification: "Which service or document is your question about?",
    });
    render(<CitizenPage />);
    search("Update pannanum");

    expect(await screen.findByText("Which service or document is your question about?")).toBeTruthy();
    expect(screen.queryByText(/We don't have an approved procedure/)).toBeNull();
    expect(api.askGuidance).not.toHaveBeenCalled();
  });

  it("identifies a later Tanglish question with the selected language and answers its English query", async () => {
    vi.mocked(api.identifyProcedure)
      .mockResolvedValueOnce({ status: "matched", candidates: [passport], named: true })
      .mockResolvedValueOnce({ status: "matched", candidates: [passport], normalized_query: "What documents are needed?" });
    render(<CitizenPage />);
    search();
    await screen.findByRole("heading", { name: passport.name });
    await settled();
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ta" } });
    ask("Enna documents venum?");

    expect(await screen.findByText("Searched as: What documents are needed?")).toBeTruthy();
    expect(api.identifyProcedure).toHaveBeenLastCalledWith("Enna documents venum?", "ta");
    expect(api.askGuidance).toHaveBeenLastCalledWith(13, "What documents are needed?", "en");
  });
});

describe("read aloud", () => {
  const listeners: (() => void)[] = [];
  const speech = {
    getVoices: vi.fn(), speak: vi.fn(), cancel: vi.fn(),
    addEventListener: (_: string, listener: () => void) => listeners.push(listener),
    removeEventListener: vi.fn(),
  };

  beforeEach(() => {
    vi.stubGlobal("speechSynthesis", speech);
    vi.stubGlobal("SpeechSynthesisUtterance", class { onend = null; onerror = null; voice = null; lang = ""; constructor(public text: string) {} });
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: false, omitted_claims: 0,
      claims: [{ text: "Create a Passport Seva account.", chunk_id: 1, quote: "Register" }, { text: "Book an appointment.", chunk_id: 2, quote: "Book" }],
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("reads the written answer with an offline Indian English voice and can stop", async () => {
    const indian = { localService: true, lang: "en-IN" };
    speech.getVoices.mockReturnValue([{ localService: false, lang: "en-IN" }, { localService: true, lang: "en-US" }, indian]);
    render(<CitizenPage />);
    search();
    fireEvent.click(await screen.findByRole("button", { name: "Read aloud" }));

    const utterance = speech.speak.mock.calls[0][0];
    expect([utterance.text, utterance.voice]).toEqual(["Create a Passport Seva account. Book an appointment.", indian]);
    expect(screen.getByText("Create a Passport Seva account.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Stop reading" }));
    expect(speech.cancel).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Read aloud" })).toBeTruthy();
  });

  it("appears once the browser finishes loading its voices", async () => {
    speech.getVoices.mockReturnValue([]);
    render(<CitizenPage />);
    search();
    await screen.findByText("Create a Passport Seva account.");
    expect(screen.queryByRole("button", { name: "Read aloud" })).toBeNull();

    speech.getVoices.mockReturnValue([{ localService: true, lang: "en-IN" }]);
    act(() => listeners.forEach((listener) => listener()));
    expect(screen.getByRole("button", { name: "Read aloud" })).toBeTruthy();
  });

  it("is hidden when only online voices are available", async () => {
    speech.getVoices.mockReturnValue([{ localService: false, lang: "en-IN" }]);
    render(<CitizenPage />);
    search();
    await screen.findByText("Create a Passport Seva account.");
    expect(screen.queryByRole("button", { name: "Read aloud" })).toBeNull();
  });
});

describe("every question is identified on its own", () => {
  const enrolment = { ...passport, id: 40, name: "Aadhaar Enrolment", summary: "Enrol for Aadhaar." };
  const income = { ...passport, id: 17, name: "Income Certificate", summary: "Apply for an income certificate." };
  const detail = (p: typeof enrolment) => ({ ...passportDetail, ...p, source_url: `https://example.gov.in/${p.id}` });
  const answer = (id: number, text: string) => ({
    procedure_id: id, source_url: `https://example.gov.in/${id}`, insufficient_evidence: false, omitted_claims: 0,
    claims: [{ text, chunk_id: id, quote: `${text} quoted` }],
  });

  beforeEach(async () => {
    vi.mocked(api.getProcedure).mockImplementation(async (id) => detail(id === 40 ? enrolment : income));
    vi.mocked(api.askGuidance).mockImplementation(async (id) => answer(id, `Answer for ${id}.`));
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "matched", candidates: [enrolment], named: true });
    render(<CitizenPage />);
    search("How do I apply for Aadhaar?");
    await screen.findByText("Answer for 40.");
    await settled();
    vi.mocked(api.askGuidance).mockClear();
  });

  it("asks for the new procedure's guidance, never the earlier one's", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "matched", candidates: [income], named: true });
    ask("How do I apply for an income certificate?");

    expect(await screen.findByText("Answer for 17.")).toBeTruthy();
    expect(api.identifyProcedure).toHaveBeenCalledTimes(2);
    expect(api.identifyProcedure).toHaveBeenLastCalledWith("How do I apply for an income certificate?", "en");
    expect(api.askGuidance).toHaveBeenCalledTimes(1);
    expect(api.askGuidance).toHaveBeenCalledWith(17, "How do I apply for an income certificate?", "en");
    expect(api.askGuidance).not.toHaveBeenCalledWith(40, expect.anything(), expect.anything());
    expect(within(exchange(1)).getByRole("heading", { name: income.name })).toBeTruthy();
    expect(within(exchange(1)).queryByRole("heading", { name: enrolment.name })).toBeNull();
  });

  it("keeps the first question and answer visible, each under its own question", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "matched", candidates: [income], named: true });
    ask("How do I apply for an income certificate?");
    await screen.findByText("Answer for 17.");

    expect(document.querySelectorAll("section.exchange")).toHaveLength(2);
    expect(within(exchange(0)).getByText("How do I apply for Aadhaar?")).toBeTruthy();
    expect(within(exchange(0)).getByText("Answer for 40.")).toBeTruthy();
    expect(within(exchange(0)).getByRole("heading", { name: enrolment.name })).toBeTruthy();
    expect(within(exchange(0)).queryByText("Answer for 17.")).toBeNull();
    expect(within(exchange(1)).getByText("How do I apply for an income certificate?")).toBeTruthy();
    expect(within(exchange(1)).getByText("Answer for 17.")).toBeTruthy();
    expect(within(exchange(1)).queryByText("Answer for 40.")).toBeNull();
  });

  it("resolves different questions to different procedures and never reuses an earlier id", async () => {
    vi.mocked(api.identifyProcedure)
      .mockResolvedValueOnce({ status: "matched", candidates: [income], named: true })
      .mockResolvedValueOnce({ status: "no_match", candidates: [] })
      .mockResolvedValueOnce({ status: "matched", candidates: [enrolment], named: true });
    ask("How do I apply for an income certificate?");
    await screen.findByText("Answer for 17.");
    await settled();
    expect(api.askGuidance).toHaveBeenLastCalledWith(17, "How do I apply for an income certificate?", "en");

    // Nothing matches the third question, so no guidance is asked for 40 or 17, though both are on screen.
    vi.mocked(api.askGuidance).mockClear();
    ask("Biryani recipe");
    expect(await screen.findByText(/don't have an approved procedure/)).toBeTruthy();
    await settled();
    expect(api.askGuidance).not.toHaveBeenCalled();

    // The fourth question is identified afresh and is answered for what it returns, not for the previous question.
    ask("How do I enrol for Aadhaar?");
    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledTimes(1));
    expect(api.askGuidance).toHaveBeenCalledWith(40, "How do I enrol for Aadhaar?", "en");
    expect(api.identifyProcedure).toHaveBeenCalledTimes(4);
    expect(document.querySelectorAll("section.exchange")).toHaveLength(4);
  });

  it("clears the displayed history with New chat", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "matched", candidates: [income], named: true });
    ask("How do I apply for an income certificate?");
    await screen.findByText("Answer for 17.");
    await settled();
    expect(document.querySelectorAll("section.exchange")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "New chat" }));

    expect(document.querySelectorAll("section.exchange")).toHaveLength(0);
    expect(screen.queryByText("Answer for 40.")).toBeNull();
    expect(screen.queryByText("Answer for 17.")).toBeNull();
    expect(screen.getByText("Find the right government procedure")).toBeTruthy();
  });

  it("does not answer an ambiguous question from the earlier procedure", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "ambiguous", candidates: [income, passport] });
    ask("How do I apply for a certificate?");

    expect(await screen.findByText("Which of these fits your situation?")).toBeTruthy();
    await settled();
    expect(api.askGuidance).not.toHaveBeenCalled();
    expect(within(exchange(1)).queryByRole("heading", { name: enrolment.name })).toBeNull();

    fireEvent.click(screen.getAllByRole("button", { name: "Choose" })[0]);
    expect(await screen.findByText("Answer for 17.")).toBeTruthy();
    expect(api.askGuidance).toHaveBeenCalledTimes(1);
    expect(api.askGuidance).toHaveBeenCalledWith(17, "How do I apply for a certificate?", "en");
    // Choosing keeps the first exchange, and answers the latest question rather than the first.
    expect(document.querySelectorAll("section.exchange")).toHaveLength(2);
    expect(within(exchange(0)).getByText("Answer for 40.")).toBeTruthy();
    expect(within(exchange(1)).getByText("Answer for 17.")).toBeTruthy();
  });

  it("does not ask any guidance when the new question matches nothing", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "no_match", candidates: [] });
    ask("Biryani recipe");

    expect(await screen.findByText(/don't have an approved procedure/)).toBeTruthy();
    await settled();
    expect(api.askGuidance).not.toHaveBeenCalled();
    expect(within(exchange(1)).queryByRole("heading", { name: enrolment.name })).toBeNull();
  });

  it("does not ask any guidance when identification of the new question fails, and retries the search", async () => {
    vi.mocked(api.identifyProcedure)
      .mockRejectedValueOnce(new Error("The search service is unavailable. Try again."))
      .mockResolvedValueOnce({ status: "matched", candidates: [income], named: true });
    ask("How do I apply for an income certificate?");

    expect((await screen.findByRole("alert")).textContent).toContain("search service is unavailable");
    expect(api.askGuidance).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Answer for 17.")).toBeTruthy();
    expect(api.askGuidance).not.toHaveBeenCalledWith(40, expect.anything(), expect.anything());
  });

  it("keeps a refusal for the new procedure and never falls back to the earlier one", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValueOnce({ status: "matched", candidates: [income], named: true });
    vi.mocked(api.askGuidance).mockResolvedValueOnce({
      procedure_id: 17, source_url: "https://example.gov.in/17", insufficient_evidence: true, claims: [], omitted_claims: 0,
    });
    ask("Can an income certificate be delivered by drone?");

    expect(await screen.findByText(/does not answer this question/)).toBeTruthy();
    await settled();
    expect(api.askGuidance).toHaveBeenCalledTimes(1);
    expect(api.askGuidance).toHaveBeenCalledWith(17, "Can an income certificate be delivered by drone?", "en");
  });

  it("does not start a new question while one is still being answered", async () => {
    vi.mocked(api.identifyProcedure).mockReturnValueOnce(new Promise(() => {}));
    ask("How do I apply for an income certificate?");
    expect(screen.getByRole("button", { name: "Searching…" }).hasAttribute("disabled")).toBe(true);

    // Enter in the box submits the form even while the button is disabled.
    fireEvent.change(screen.getByLabelText("Your situation or question"), { target: { value: "How do I renew my passport?" } });
    fireEvent.submit(screen.getByLabelText("Your situation or question").closest("form")!);
    expect(api.identifyProcedure).toHaveBeenCalledTimes(2);
    expect(api.askGuidance).not.toHaveBeenCalled();
    // The blocked question is not added to the conversation.
    expect(document.querySelectorAll("section.exchange")).toHaveLength(2);
    expect(document.querySelector("main")!.textContent).not.toContain("How do I renew my passport?");
  });
});

describe("answers from a related official page", () => {
  it("name the page each related claim comes from", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: false, omitted_claims: 0,
      claims: [{ text: "The permit costs Rs. 1000.", chunk_id: 69, quote: "Issue of International Driving Permit Rs. 1000.00/-",
                 procedure_id: 27, source_url: "https://parivahan.gov.in/fees" }],
    });
    vi.mocked(api.getProcedure)
      .mockResolvedValueOnce(passportDetail)
      .mockResolvedValueOnce({ ...passportDetail, id: 27, name: "Driving Licence Fees and Charges" });
    render(<CitizenPage />);
    search("What is the fee for an International Driving Permit?");

    expect(await screen.findByText("Driving Licence Fees and Charges:")).toBeTruthy();
    expect(screen.getByText("The permit costs Rs. 1000.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open the official page" }).getAttribute("href")).toBe("https://parivahan.gov.in/fees");
  });

  it("say when the answer covers only part of the question", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.askGuidance).mockResolvedValue({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: false, omitted_claims: 0, partial: true,
      claims: [{ text: "Register on the portal first.", chunk_id: 1, quote: "Register on the portal" }],
    });
    render(<CitizenPage />);
    search();
    expect(await screen.findByText(/may not cover every part of your question/)).toBeTruthy();
  });
});
