import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import * as api from "./api";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof api>()),
  getSession: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  listSavedProcedures: vi.fn(),
}));

function signIn(password = "secret") {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "admin" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getSession).mockRejectedValue(new Error("Not signed in."));
  vi.mocked(api.listSavedProcedures).mockResolvedValue([]);
});
afterEach(cleanup);

describe("admin sign in", () => {
  it("shows the login form when there is no session", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Admin sign in" })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("opens the review page after signing in", async () => {
    vi.mocked(api.login).mockResolvedValue({ username: "admin" });
    render(<App />);
    await screen.findByLabelText("Username");

    signIn();

    expect(await screen.findByText("Procedure review")).toBeTruthy();
    expect(screen.getByText("Signed in as admin")).toBeTruthy();
    expect(api.login).toHaveBeenCalledWith("admin", "secret");
  });

  it("shows the server error and clears the password on failure", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("Invalid username or password."));
    render(<App />);
    await screen.findByLabelText("Username");

    signIn("wrong");

    expect((await screen.findByRole("alert")).textContent).toBe("Invalid username or password.");
    expect((screen.getByLabelText("Password") as HTMLInputElement).value).toBe("");
  });

  it("returns to login when a request reports an expired session", async () => {
    vi.mocked(api.getSession).mockResolvedValue({ username: "admin" });
    render(<App />);
    await screen.findByText("Procedure review");

    act(() => {
      window.dispatchEvent(new Event(api.UNAUTHORIZED_EVENT));
    });

    expect((await screen.findByRole("alert")).textContent).toContain("session has expired");
  });

  it("signs out", async () => {
    vi.mocked(api.getSession).mockResolvedValue({ username: "admin" });
    vi.mocked(api.logout).mockResolvedValue(undefined);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Admin sign in" })).toBeTruthy();
    expect(api.logout).toHaveBeenCalled();
  });
});
