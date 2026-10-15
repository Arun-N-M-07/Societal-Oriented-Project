import { useState, type FormEvent } from "react";

import {
  askGuidance,
  getProcedure,
  identifyProcedure,
  type GuidanceResponse,
  type IdentifyResponse,
  type ProcedureDetail,
} from "./api";


type Pending = "identify" | "procedure" | "guidance" | null;

const message = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;


export default function CitizenPage() {
  const [situation, setSituation] = useState("");
  const [matches, setMatches] = useState<IdentifyResponse | null>(null);
  const [procedure, setProcedure] = useState<ProcedureDetail | null>(null);
  const [followUp, setFollowUp] = useState("");
  const [answer, setAnswer] = useState<GuidanceResponse | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [error, setError] = useState<{ text: string; retry: () => void } | null>(null);

  async function run(step: Pending, action: () => Promise<void>, fallback: string) {
    setPending(step);
    setError(null);
    try {
      await action();
    } catch (requestError) {
      setError({ text: message(requestError, fallback), retry: () => run(step, action, fallback) });
    } finally {
      setPending(null);
    }
  }

  function openProcedure(id: number) {
    setAnswer(null);
    setFollowUp("");
    void run("procedure", async () => setProcedure(await getProcedure(id)), "Unable to load the procedure.");
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = situation.trim();
    if (!question) return;
    setProcedure(null);
    setAnswer(null);
    void run("identify", async () => {
      const result = await identifyProcedure(question);
      setMatches(result);
      if (result.status === "matched") setProcedure(await getProcedure(result.candidates[0].id));
    }, "Unable to search procedures.");
  }

  function handleFollowUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = followUp.trim();
    if (!procedure || !question) return;
    void run("guidance", async () => setAnswer(await askGuidance(procedure.id, question)), "Unable to answer the question.");
  }

  const busy = pending !== null;

  return (
    <main className="admin-page citizen-page">
      <header className="page-header">
        <p className="eyebrow">ProcedureAssist</p>
        <h1>Find the right government procedure</h1>
        <p>Describe your situation in your own words. Answers come only from approved official pages.</p>
      </header>

      <form className="card" onSubmit={handleSearch}>
        <div className="form-field">
          <label htmlFor="situation">Your situation or question</label>
          <textarea
            id="situation"
            rows={3}
            maxLength={1000}
            placeholder="For example: My passport has expired and I need a new one."
            value={situation}
            onChange={(event) => setSituation(event.target.value)}
            required
          />
        </div>
        <button className="primary-button" type="submit" disabled={busy}>
          {pending === "identify" ? "Searching…" : "Find procedure"}
        </button>
      </form>

      {pending && pending !== "identify" && (
        <p className="feedback" role="status">
          {pending === "procedure" ? "Loading the procedure…" : "Checking the official text… this can take up to a minute."}
        </p>
      )}
      {error && (
        <div className="feedback error" role="alert">
          {error.text}{" "}
          <button className="secondary-button" type="button" onClick={error.retry} disabled={busy}>
            Try again
          </button>
        </div>
      )}

      {matches?.status === "no_match" && (
        <p className="feedback" role="status">
          We don't have an approved procedure that matches this yet. Try describing your
          situation differently, for example which document or service you need.
        </p>
      )}

      {matches?.status === "ambiguous" && !procedure && (
        <section className="card review-card" aria-labelledby="choices-heading">
          <h2 id="choices-heading">Which of these fits your situation?</h2>
          <p className="section-intro">Several procedures could apply. Choose one, or add more detail above.</p>
          <ul className="procedure-list">
            {matches.candidates.map((candidate) => (
              <li key={candidate.id}>
                <div>
                  <strong>{candidate.name}</strong>
                  <span>{candidate.summary}</span>
                </div>
                <button className="secondary-button" type="button" disabled={busy} onClick={() => openProcedure(candidate.id)}>
                  Choose
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {procedure && (
        <section className="card review-card" aria-labelledby="procedure-heading">
          <h2 id="procedure-heading">{procedure.name}</h2>
          {procedure.department && <p className="section-intro">{procedure.department}</p>}
          <p>{procedure.summary}</p>
          {procedure.eligibility && (
            <>
              <h3>Who can apply</h3>
              <p>{procedure.eligibility}</p>
            </>
          )}
          <h3>Steps</h3>
          <ol className="citizen-steps">
            {procedure.steps.map((step, index) => <li key={index}>{step}</li>)}
          </ol>
          <p>
            <a href={procedure.source_url} target="_blank" rel="noopener noreferrer">
              Open the official page
            </a>
          </p>
          <p className="field-help">
            This is guidance only. Check the official page and apply there yourself;
            ProcedureAssist does not submit applications.
          </p>
          {matches?.status === "ambiguous" && (
            <button className="secondary-button" type="button" onClick={() => setProcedure(null)}>
              Back to choices
            </button>
          )}

          <form className="follow-up" onSubmit={handleFollowUp}>
            <div className="form-field">
              <label htmlFor="follow-up">Ask about this procedure</label>
              <input
                id="follow-up"
                maxLength={1000}
                placeholder="For example: Which documents do I need?"
                value={followUp}
                onChange={(event) => setFollowUp(event.target.value)}
                required
              />
            </div>
            <button className="primary-button" type="submit" disabled={busy}>
              {pending === "guidance" ? "Checking…" : "Ask"}
            </button>
          </form>

          {answer && answer.insufficient_evidence && (
            <p className="feedback" role="status">
              The approved official information does not answer this question. Please check
              the <a href={answer.source_url} target="_blank" rel="noopener noreferrer">official page</a>.
            </p>
          )}
          {answer && !answer.insufficient_evidence && (
            <div className="answer">
              <ol className="citizen-steps">
                {answer.claims.map((claim, index) => (
                  <li key={index}>
                    {claim.text}
                    <details>
                      <summary>Official source</summary>
                      <blockquote>{claim.quote}</blockquote>
                      <a href={answer.source_url} target="_blank" rel="noopener noreferrer">
                        Open the official page
                      </a>
                    </details>
                  </li>
                ))}
              </ol>
              {answer.omitted_claims > 0 && (
                <p className="field-help">
                  {answer.omitted_claims} statement(s) were left out because the official text did not support them.
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
