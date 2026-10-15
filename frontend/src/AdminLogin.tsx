import { useState, type FormEvent } from "react";

import { login } from "./api";


export default function AdminLogin({
  notice,
  onSignedIn,
}: {
  notice: string;
  onSignedIn: (username: string) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      onSignedIn((await login(username, password)).username);
    } catch (loginError) {
      setPassword("");
      setError(loginError instanceof Error ? loginError.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="admin-page">
      <header className="page-header">
        <p className="eyebrow">ProcedureAssist</p>
        <h1>Admin sign in</h1>
      </header>

      {(error || notice) && (
        <p className="feedback error" role="alert">{error || notice}</p>
      )}

      <form className="card" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="admin-username">Username</label>
          <input
            id="admin-username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="admin-password">Password</label>
          <input
            id="admin-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
