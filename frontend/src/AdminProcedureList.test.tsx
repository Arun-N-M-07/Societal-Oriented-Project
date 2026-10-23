import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminProcedureList from "./AdminProcedureList";
import * as api from "./api";

vi.mock("./api");

const passport = {
  id: 13,
  name: "Fresh Passport",
  department: null,
  jurisdiction: null,
  source_url: "https://www.passportindia.gov.in/psp/Apply",
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listSavedProcedures).mockResolvedValue([passport]);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("saved procedure list", () => {
  it("lists procedures with their official links", async () => {
    render(<AdminProcedureList />);

    expect(await screen.findByText("Fresh Passport")).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toBe(passport.source_url);
  });

  it("deletes after confirmation and reloads", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.deleteProcedure).mockResolvedValue(undefined);
    render(<AdminProcedureList />);
    await screen.findByText("Fresh Passport");
    vi.mocked(api.listSavedProcedures).mockResolvedValue([]);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByText("No saved procedures yet.")).toBeTruthy();
    expect(api.deleteProcedure).toHaveBeenCalledWith(13);
  });

  it("does nothing when deletion is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<AdminProcedureList />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));

    expect(api.deleteProcedure).not.toHaveBeenCalled();
  });

  it("shows errors", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(api.deleteProcedure).mockRejectedValue(new Error("Unable to delete procedure."));
    render(<AdminProcedureList />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toBe("Unable to delete procedure."),
    );
  });
});
