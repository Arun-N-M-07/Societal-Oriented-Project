import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

function ask(text = "Which documents do I need?") {
  fireEvent.change(screen.getByLabelText("Ask about this procedure"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

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
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    render(<CitizenPage />);
    search();

    expect(await screen.findByRole("heading", { name: passport.name })).toBeTruthy();
    const card = screen.getByRole("heading", { name: passport.name }).closest("section")!;
    const steps = Array.from(card.querySelectorAll("ol > li")).map((item) => item.textContent);
    expect(steps).toEqual(passportDetail.steps);
    expect(screen.getByText("Indian citizens.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open the official page" }).getAttribute("href")).toBe(
      passportDetail.source_url,
    );
    expect(screen.getByText(/does not submit applications/)).toBeTruthy();
    expect(api.identifyProcedure).toHaveBeenCalledWith("My passport expired", "en");
    await waitFor(() => expect(api.askGuidance).toHaveBeenCalledWith(13, "My passport expired", "en"));
  });

  it("hides eligibility when the approved record has none", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.getProcedure).mockResolvedValue({ ...passportDetail, eligibility: null });
    render(<CitizenPage />);
    search();

    await screen.findByRole("heading", { name: passport.name });
    expect(screen.queryByText("Who can apply")).toBeNull();
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
      .mockResolvedValueOnce({ status: "matched", candidates: [passport] });
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

describe("follow-up questions", () => {
  beforeEach(async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    render(<CitizenPage />);
    search();
    await screen.findByRole("heading", { name: passport.name });
    await screen.findByRole("button", { name: "Send" });
    vi.mocked(api.askGuidance).mockClear();
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

  it("appends each follow-up as a separate question and answer", async () => {
    vi.mocked(api.askGuidance).mockResolvedValueOnce({
      procedure_id: 13,
      source_url: passportDetail.source_url,
      insufficient_evidence: false,
      claims: [{ text: "Carry proof of address.", chunk_id: 4, quote: "carry proof of address and date of birth" }],
      omitted_claims: 0,
    });
    ask("Which documents do I need?");
    await screen.findByText("Carry proof of address.");
    ask("Is there a fee?");

    await waitFor(() => expect(screen.getAllByText(/does not answer this question/)).toHaveLength(2));
    expect(screen.getByText("Carry proof of address.")).toBeTruthy();
    expect(screen.getByText("My passport expired")).toBeTruthy();
    expect(screen.getByText("Which documents do I need?")).toBeTruthy();
    expect(screen.getByText("Is there a fee?")).toBeTruthy();
    expect(api.askGuidance).toHaveBeenNthCalledWith(1, 13, "Which documents do I need?", "en");
    expect(api.askGuidance).toHaveBeenNthCalledWith(2, 13, "Is there a fee?", "en");
  });

  it("retries a failed answer with the same question", async () => {
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
    expect(document.querySelectorAll("section.card")).toHaveLength(1);

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

  it("routes follow-ups to the procedure they name, relationship questions across all, asks which one otherwise, or uses the one chosen", async () => {
    render(<CitizenPage />);
    search("I want to renew my passport and update my Aadhaar address.");
    await screen.findByText("Answer for 30.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Send" }).hasAttribute("disabled")).toBe(false));

    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [aadhaar] });
    search("Tell me more about the Aadhaar update");
    await waitFor(() => expect(api.askGuidance).toHaveBeenLastCalledWith(30, "Tell me more about the Aadhaar update", "en"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Send" }).hasAttribute("disabled")).toBe(false));

    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "no_match", candidates: [] });
    search("Can I reuse my documents?");
    await waitFor(() => expect(api.askRelation).toHaveBeenLastCalledWith([13, 30], "Can I reuse my documents?"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Send" }).hasAttribute("disabled")).toBe(false));

    vi.mocked(api.askRelation).mockClear();
    search("What are the fees?");
    expect(await screen.findByText(/Which procedure is this about\?/)).toBeTruthy();
    expect(api.askRelation).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Send" }).hasAttribute("disabled")).toBe(false));

    fireEvent.click(screen.getAllByRole("button", { name: "Ask more about this" })[0]);
    await screen.findByRole("heading", { name: passport.name });
    ask("What are the fees?");
    await waitFor(() => expect(api.askGuidance).toHaveBeenLastCalledWith(13, "What are the fees?", "en"));
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

  it("follow-ups about the open procedure are sent with the selected language", async () => {
    vi.mocked(api.identifyProcedure).mockResolvedValue({ status: "matched", candidates: [passport] });
    vi.mocked(api.askGuidance).mockResolvedValueOnce({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: true, claims: [], omitted_claims: 0,
    }).mockResolvedValueOnce({
      procedure_id: 13, source_url: passportDetail.source_url, insufficient_evidence: true, claims: [], omitted_claims: 0,
      normalized_query: "What documents are needed?",
    });
    render(<CitizenPage />);
    search();
    await screen.findByRole("heading", { name: passport.name });
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ta" } });
    ask("Enna documents venum?");

    await waitFor(() => expect(api.askGuidance).toHaveBeenLastCalledWith(13, "Enna documents venum?", "ta"));
    expect(await screen.findByText("Searched as: What documents are needed?")).toBeTruthy();
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
