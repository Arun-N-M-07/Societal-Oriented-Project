import { useRef, useState, type FormEvent, type ReactNode } from "react";

import {
  askGuidance,
  askRelation,
  getProcedure,
  identifyProcedure,
  type GuidanceResponse,
  type IdentifyResponse,
  type Need,
  type ProcedureDetail,
  type RelationResponse,
} from "./api";


type Pending = "identify" | "procedure" | "guidance" | null;
type Reply = GuidanceResponse | RelationResponse;
// One need of a multi-need message; procedureId is set once it is matched or chosen.
type Section = { need: Need; procedureId?: number; answer?: GuidanceResponse; error?: string };
type Message = {
  id: number;
  question: string;
  answer?: Reply;
  sections?: Section[];
  pending?: { phrase: string; question: string }[];
  relation?: { question: string; answer?: RelationResponse; error?: string };
  note?: string;
};

// A follow-up across several procedures is only sent to the relationship check
// when it asks about order, dependencies or reusing documents.
const ASKS_RELATION = /\b(first|before|after|order|depend\w*|reus\w*|same|both|together|affect\w*|need .* for)\b/i;
const WHICH_ONE = "Which procedure is this about? Use “Ask more about this” on one of them, or describe a new need.";

// Mirrors backend rag.COMPARISON: the backend answers these as a comparison.
const COMPARES = /\b(differ\w*|compar\w*|versus|vs)\b/i;
const NO_COMPARISON = "The approved official pages do not give details that compare these procedures for this question.";
const NO_RELATION =
  "The approved official sources do not confirm an order, dependency or document reuse between these procedures. " +
  "Use “Ask more about this” to ask about one procedure.";

const message = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;


export default function CitizenPage() {
  const [situation, setSituation] = useState("");
  const [matches, setMatches] = useState<IdentifyResponse | null>(null);
  const [procedure, setProcedure] = useState<ProcedureDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending>(null);
  const [error, setError] = useState<{ text: string; retry: () => void } | null>(null);
  const lastId = useRef(0);
  const newMessage = (question: string): Message => ({ id: ++lastId.current, question });
  // Updates are keyed by id, so a reply for a message that was reset meanwhile is dropped.
  const update = (id: number, change: (m: Message) => Message) =>
    setMessages((all) => all.map((m) => (m.id === id ? change(m) : m)));
  const updateSection = (id: number, index: number, change: Partial<Section>) =>
    update(id, (m) => ({ ...m, sections: m.sections?.map((s, i) => (i === index ? { ...s, ...change } : s)) }));
  const matchedIds = (m?: Message) => m?.sections?.flatMap((s) => (s.procedureId ? [s.procedureId] : [])) ?? [];

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

  // Answer one message from the procedure's evidence.
  async function answer(id: number, message: Message) {
    setPending("guidance");
    const reply = await askGuidance(id, message.question);
    update(message.id, (m) => ({ ...m, answer: reply }));
  }

  // Each need is answered on its own, one at a time, so one failure leaves the others intact.
  async function answerSection(id: number, index: number, procedureId: number, question: string) {
    updateSection(id, index, { procedureId, error: undefined });
    try {
      updateSection(id, index, { answer: await askGuidance(procedureId, question) });
    } catch (requestError) {
      updateSection(id, index, { error: message(requestError, "Unable to answer the question.") });
    }
  }

  async function relate(id: number, question: string, procedureIds: number[]) {
    if (procedureIds.length < 2) return;
    try {
      const answer = await askRelation(procedureIds, question);
      update(id, (m) => ({ ...m, relation: { question, answer } }));
    } catch (requestError) {
      update(id, (m) => ({ ...m, relation: { question, error: message(requestError, "Unable to answer the question.") } }));
    }
  }

  async function answerNeeds(message: Message, result: IdentifyResponse) {
    const sections = (result.needs ?? []).map((need) => ({
      need, procedureId: need.status === "matched" ? need.candidates[0].id : undefined,
    }));
    const relationQuestion = result.relation_question;
    update(message.id, (m) => ({
      ...m, sections, pending: result.pending, relation: relationQuestion ? { question: relationQuestion } : undefined,
    }));
    setPending("guidance");
    for (const [index, section] of sections.entries()) {
      if (section.procedureId) await answerSection(message.id, index, section.procedureId, section.need.question);
    }
    if (relationQuestion) await relate(message.id, relationQuestion, matchedIds({ ...message, sections }));
  }

  async function handleResult(result: IdentifyResponse, message: Message) {
    setMatches(result);
    if (result.status === "matched") await showAndAnswer(result.candidates[0].id, message);
    if (result.status === "multiple") await answerNeeds(message, result);
  }

  // With several procedures on screen, a follow-up about one of them answers from it;
  // a question about how they relate goes to the relationship check; anything else
  // unclear asks the citizen which procedure they mean.
  async function followUp(message: Message, active: number[]) {
    const result = await identifyProcedure(message.question);
    const hit = result.status === "matched" ? result.candidates[0].id : undefined;
    if (hit && active.includes(hit)) return answer(hit, message);
    if (result.status === "no_match" || result.status === "ambiguous") {
      if (!ASKS_RELATION.test(message.question)) return update(message.id, (m) => ({ ...m, note: WHICH_ONE }));
      setPending("guidance");
      const reply = await askRelation(active, message.question);
      return update(message.id, (m) => ({ ...m, answer: reply }));
    }
    setMessages([message]);
    await handleResult(result, message);
  }

  async function showAndAnswer(id: number, message: Message) {
    setProcedure(await getProcedure(id));
    await answer(id, message);
  }

  function openProcedure(id: number) {
    const message = newMessage(messages[0].question);
    setMessages([message]);
    void run("procedure", () => showAndAnswer(id, message), "Unable to load the procedure.");
  }

  function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = situation.trim();
    if (!question) return;
    const message = newMessage(question);
    setSituation("");
    const active = matchedIds(messages.find((m) => m.sections));
    if (procedure || active.length > 1) {
      setMessages((all) => [...all, message]);
      void run("guidance", () => (procedure ? answer(procedure.id, message) : followUp(message, active)),
        "Unable to answer the question.");
      return;
    }
    setMessages([message]);
    void run("identify", async () => handleResult(await identifyProcedure(question), message),
      "Unable to search procedures.");
  }

  function renderAnswer(reply: Reply, refusal: ReactNode, names?: Record<number, string>) {
    if (reply.insufficient_evidence) return <p className="feedback" role="status">{refusal}</p>;
    return (
      <div className="answer">
        <ol className="citizen-steps">
          {reply.claims.map((claim, index) => (
            <li key={index}>
              {names && claim.procedure_id !== undefined && <strong>{names[claim.procedure_id]}: </strong>}
              {claim.text}
              <details>
                <summary>Official source</summary>
                <blockquote>{claim.quote}</blockquote>
                <a href={claim.source_url ?? ("source_url" in reply ? reply.source_url : "")} target="_blank" rel="noopener noreferrer">
                  Open the official page
                </a>
              </details>
            </li>
          ))}
        </ol>
        {reply.omitted_claims > 0 && (
          <p className="field-help">
            {reply.omitted_claims} statement(s) were left out because the official text did not support them.
          </p>
        )}
      </div>
    );
  }

  const failure = (text: string, retry: () => void) => (
    <div className="feedback error" role="alert">
      {text}{" "}
      <button className="secondary-button" type="button" onClick={retry} disabled={busy}>
        Try again
      </button>
    </div>
  );

  const refusal = (reply: Reply) => ("source_url" in reply ? (
    <>
      The approved official information does not answer this question. Please check
      the <a href={reply.source_url} target="_blank" rel="noopener noreferrer">official page</a>.
    </>
  ) : NO_RELATION);

  const busy = pending !== null;

  return (
    <main className="admin-page citizen-page">
      <header className="page-header">
        <p className="eyebrow">ProcedureAssist</p>
        <h1>Find the right government procedure</h1>
        <p>Describe your situation in your own words. Answers come only from approved official pages.</p>
      </header>

      {matches?.status === "ambiguous" && !procedure && (
        <section className="card review-card" aria-labelledby="choices-heading">
          <h2 id="choices-heading">Which of these fits your situation?</h2>
          <p className="section-intro">Several procedures could apply. Choose one, or add more detail below.</p>
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
            <button className="secondary-button" type="button" disabled={busy} onClick={() => setProcedure(null)}>
              Back to choices
            </button>
          )}{" "}
          <button className="secondary-button" type="button" disabled={busy} onClick={() => { setProcedure(null); setMatches(null); setMessages([]); }}>
            Start a new search
          </button>
        </section>
      )}

      {messages.map((m) => (
        <section className="card review-card" key={m.id}>
          <p className="section-intro"><strong>You:</strong> {m.question}</p>
          {m.answer && renderAnswer(m.answer, refusal(m.answer))}
          {m.note && <p className="feedback" role="status">{m.note}</p>}
          {m.sections && (
            <>
              <p>I understood your request as:</p>
              <ol>
                {[...m.sections.flatMap((s) => s.need.phrases), ...(m.pending ?? []).map((p) => p.phrase)].map(
                  (phrase, index) => <li key={index}>{phrase}</li>,
                )}
              </ol>
              {m.sections.map((s, index) => {
                const name = s.need.candidates.find((c) => c.id === s.procedureId)?.name;
                return (
                  <div key={index}>
                    <h3>{name ?? s.need.phrases.join(" / ")}</h3>
                    {s.need.status === "no_match" ? (
                      <p className="feedback" role="status">We don't have an approved procedure for this yet.</p>
                    ) : !s.procedureId ? (
                      <ul className="procedure-list">
                        {s.need.candidates.map((candidate) => (
                          <li key={candidate.id}>
                            <div><strong>{candidate.name}</strong><span>{candidate.summary}</span></div>
                            <button className="secondary-button" type="button" disabled={busy}
                              onClick={() => void run("guidance", () => answerSection(m.id, index, candidate.id, s.need.question), "Unable to answer the question.")}>
                              Choose
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : s.error ? (
                      failure(s.error, () => void run("guidance", () => answerSection(m.id, index, s.procedureId!, s.need.question), "Unable to answer the question."))
                    ) : s.answer ? renderAnswer(s.answer, refusal(s.answer)) : (
                      <p className="feedback" role="status">Waiting for the answer…</p>
                    )}
                    {s.procedureId && (
                      <button className="secondary-button" type="button" disabled={busy}
                        onClick={() => void run("procedure", async () => setProcedure(await getProcedure(s.procedureId!)), "Unable to load the procedure.")}>
                        Ask more about this
                      </button>
                    )}
                  </div>
                );
              })}
              {m.relation && (() => {
                const comparing = COMPARES.test(m.relation.question);
                const names = Object.fromEntries(m.sections.flatMap((s) => s.need.candidates).map((c) => [c.id, c.name]));
                const uncovered = matchedIds(m).filter((id) => !m.relation?.answer?.claims.some((c) => c.procedure_id === id));
                return (
                <>
                  <h3>{comparing ? "How they compare (official text)" : "How these relate (official text)"}</h3>
                  {m.relation.answer ? (
                    <>
                      {renderAnswer(m.relation.answer, comparing ? NO_COMPARISON : NO_RELATION, comparing ? names : undefined)}
                      {comparing && !m.relation.answer.insufficient_evidence && (
                        <p className="field-help">
                          The official pages do not compare these procedures directly; each point comes only from that
                          procedure's own page.{uncovered.length > 0 && ` No comparable details were found for: ${uncovered.map((id) => names[id]).join(", ")}.`}
                        </p>
                      )}
                    </>
                  ) : m.relation.error ? (
                    failure(m.relation.error, () => void run("guidance", () => relate(m.id, m.relation!.question, matchedIds(m)), "Unable to answer the question."))
                  ) : matchedIds(m).length < 2 ? (
                    <p className="feedback" role="status">At least two matched procedures are needed to compare them.</p>
                  ) : (
                    <p className="feedback" role="status">Waiting for the answer…</p>
                  )}
                </>
                );
              })()}
              {m.pending && m.pending.length > 0 && (
                <p className="feedback" role="status">
                  Not answered yet: {m.pending.map((p) => p.phrase).join("; ")}.{" "}
                  <button className="secondary-button" type="button" disabled={busy}
                    onClick={() => setSituation(m.pending!.map((p) => p.question).join(" "))}>
                    Ask about these next
                  </button>
                </p>
              )}
            </>
          )}
        </section>
      ))}

      {pending && pending !== "identify" && (
        <p className="feedback" role="status">
          {pending === "procedure" ? "Loading the procedure…" : "Checking the official text… this can take up to a minute."}
        </p>
      )}
      {error && failure(error.text, error.retry)}

      {matches?.status === "no_match" && (
        <p className="feedback" role="status">
          We don't have an approved procedure that matches this yet. Try describing your
          situation differently, for example which document or service you need.
        </p>
      )}

      <form className="card" onSubmit={handleSend}>
        <div className="form-field">
          <label htmlFor="situation">{procedure ? "Ask about this procedure" : "Your situation or question"}</label>
          <textarea
            id="situation"
            rows={3}
            maxLength={1000}
            placeholder={procedure ? "For example: Which documents do I need?" : "For example: My passport has expired and I need a new one."}
            value={situation}
            onChange={(event) => setSituation(event.target.value)}
            required
          />
        </div>
        <button className="primary-button" type="submit" disabled={busy}>
          {pending === "identify" ? "Searching…" : "Send"}
        </button>
      </form>
    </main>
  );
}
