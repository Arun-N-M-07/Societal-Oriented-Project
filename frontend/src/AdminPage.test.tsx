import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./AdminPage";
import * as api from "./api";

vi.mock("./api");

const longText = "Long sentence about the procedure. ".repeat(40).trim();

const extraction: api.ExtractionResponse = {
  source_text: "Official source text.",
  provenance_token: "token-1",
  procedure: {
    name: "Fresh Passport Application",
    department: "Ministry of External Affairs",
    jurisdiction: "Central Government",
    summary: longText,
    eligibility: `Eligibility: ${longText}`,
    steps: ["Register online.", "Fill the form.", "Pay the fee.", "Book a slot."],
    source_url: "https://example.gov.in/passport",
  },
};

function dataTransfer() {
  return { setData: vi.fn(), setDragImage: vi.fn(), effectAllowed: "" };
}

function stepTexts() {
  return screen
    .getAllByTestId("step-row")
    .map((row) => (row.querySelector("textarea") as HTMLTextAreaElement).value);
}

function handle(stepNumber: number) {
  return screen.getByRole("button", { name: `Move step ${stepNumber}` });
}

function row(stepNumber: number) {
  return screen.getAllByTestId("step-row")[stepNumber - 1];
}

async function openReview() {
  vi.mocked(api.extractProcedure).mockResolvedValue(extraction);
  render(<AdminPage />);
  fireEvent.change(screen.getByLabelText("Source URL"), {
    target: { value: "https://example.gov.in/passport" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract" }));
  await screen.findByText("Review extracted procedure");
}

function drag(from: number, to: number) {
  fireEvent.dragStart(handle(from), { dataTransfer: dataTransfer() });
  fireEvent.dragOver(row(to), { dataTransfer: dataTransfer() });
  fireEvent.drop(row(to), { dataTransfer: dataTransfer() });
  fireEvent.dragEnd(handle(from));
}

beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

describe("review form fields", () => {
  it("shows and edits long summary and eligibility text in full", async () => {
    await openReview();

    const summary = screen.getByLabelText("Summary") as HTMLTextAreaElement;
    const eligibility = screen.getByLabelText("Eligibility") as HTMLTextAreaElement;
    expect(summary.value).toBe(longText);
    expect(eligibility.value).toBe(extraction.procedure.eligibility);

    fireEvent.change(summary, { target: { value: `${longText} Edited.` } });
    expect(summary.value.endsWith("Edited.")).toBe(true);
  });

  it("shows every step as an editable multi-line field", async () => {
    await openReview();

    expect(stepTexts()).toEqual(extraction.procedure.steps);
    const first = row(1).querySelector("textarea") as HTMLTextAreaElement;
    fireEvent.change(first, { target: { value: "Register online\nand verify." } });
    expect(stepTexts()[0]).toBe("Register online\nand verify.");
  });
});

describe("step reordering", () => {
  it("moves a step by dragging its handle and renumbers the list", async () => {
    await openReview();

    drag(1, 3);

    expect(stepTexts()).toEqual([
      "Fill the form.",
      "Pay the fee.",
      "Register online.",
      "Book a slot.",
    ]);
    expect(screen.getAllByText(/^Step \d$/).map((l) => l.textContent)).toEqual([
      "Step 1",
      "Step 2",
      "Step 3",
      "Step 4",
    ]);
  });

  it("moves a step upwards", async () => {
    await openReview();
    drag(4, 2);
    expect(stepTexts()).toEqual([
      "Register online.",
      "Book a slot.",
      "Fill the form.",
      "Pay the fee.",
    ]);
  });

  it("shows the dragged step and the drop position", async () => {
    await openReview();

    fireEvent.dragStart(handle(1), { dataTransfer: dataTransfer() });
    expect(row(1).className).toContain("dragging");
    fireEvent.dragOver(row(3), { dataTransfer: dataTransfer() });
    expect(row(3).className).toContain("drop-after");
    fireEvent.dragEnd(handle(1));
    expect(row(1).className).not.toContain("dragging");
    expect(row(3).className).not.toContain("drop-");
  });

  it("moves a step with the arrow keys", async () => {
    await openReview();

    fireEvent.keyDown(handle(2), { key: "ArrowUp" });
    expect(stepTexts().slice(0, 2)).toEqual(["Fill the form.", "Register online."]);

    fireEvent.keyDown(handle(1), { key: "ArrowUp" });
    expect(stepTexts()[0]).toBe("Fill the form.");
  });

  it("keeps edited text with the step when it moves", async () => {
    await openReview();

    fireEvent.change(row(1).querySelector("textarea")!, {
      target: { value: "Edited first step." },
    });
    drag(1, 2);

    expect(stepTexts().slice(0, 2)).toEqual(["Fill the form.", "Edited first step."]);
  });
});

describe("adding and removing steps", () => {
  it("adds a step at the end and removes a step", async () => {
    await openReview();

    fireEvent.click(screen.getByRole("button", { name: "Add step" }));
    expect(stepTexts()).toHaveLength(5);
    expect(screen.queryByRole("button", { name: "Insert before" })).toBeNull();

    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);
    expect(stepTexts()).toEqual([
      "Register online.",
      "Pay the fee.",
      "Book a slot.",
      "",
    ]);
  });
});

describe("approval", () => {
  it("submits the reordered, edited steps and the other fields unchanged", async () => {
    await openReview();
    vi.mocked(api.approveProcedure).mockResolvedValue({
      id: 7,
      name: "Fresh Passport Application",
      status: "saved",
    });

    drag(4, 1);
    fireEvent.change(row(3).querySelector("textarea")!, {
      target: { value: "  Fill the form carefully.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add step" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve and save" }));

    await screen.findByText("Saved Fresh Passport Application with ID 7.");
    expect(api.approveProcedure).toHaveBeenCalledWith({
      source_text: "Official source text.",
      provenance_token: "token-1",
      procedure: {
        ...extraction.procedure,
        steps: [
          "Book a slot.",
          "Register online.",
          "Fill the form carefully.",
          "Pay the fee.",
        ],
      },
    });
  });

  it("still requires at least one step", async () => {
    await openReview();
    for (const step of [1, 2, 3, 4]) {
      fireEvent.change(row(step).querySelector("textarea")!, { target: { value: " " } });
    }
    fireEvent.click(screen.getByRole("button", { name: "Approve and save" }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("at least one step"),
    );
    expect(api.approveProcedure).not.toHaveBeenCalled();
  });

  it("replaces the steps when re-extracting", async () => {
    await openReview();
    vi.mocked(api.reExtractProcedure).mockResolvedValue({
      ...extraction.procedure,
      steps: ["Only step."],
    });

    fireEvent.click(screen.getByRole("button", { name: "Re-extract" }));
    await waitFor(() => expect(stepTexts()).toEqual(["Only step."]));
    expect(api.reExtractProcedure).toHaveBeenCalledWith({
      source_url: extraction.procedure.source_url,
      source_text: "Official source text.",
      provenance_token: "token-1",
    });
  });
});
