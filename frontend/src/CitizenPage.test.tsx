import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CitizenPage from "./CitizenPage";
import * as api from "./api";

vi.mock("./api");

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
  fireEvent.click(screen.getByRole("button", { name: "Find procedure" }));
}

function ask(text = "Which documents do I need?") {
  fireEvent.change(screen.getByLabelText("Ask about this procedure"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getProcedure).mockResolvedValue(passportDetail);
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
    const steps = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(steps).toEqual(passportDetail.steps);
    expect(screen.getByText("Indian citizens.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open the official page" }).getAttribute("href")).toBe(
      passportDetail.source_url,
    );
    expect(screen.getByText(/does not submit applications/)).toBeTruthy();
    expect(api.identifyProcedure).toHaveBeenCalledWith("My passport expired");
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
    expect(api.identifyProcedure).toHaveBeenNthCalledWith(2, "My passport expired");
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
    expect(api.askGuidance).toHaveBeenCalledWith(13, "Which documents do I need?");
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
    expect(api.askGuidance).toHaveBeenLastCalledWith(13, "Which documents do I need?");
  });
});
