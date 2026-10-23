import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";

import {
  askGuidance,
  askRelation,
  getProcedure,
  identifyProcedure,
  type GuidanceResponse,
  type IdentifyResponse,
  type Language,
  type Need,
  type ProcedureDetail,
  type RelationResponse,
} from "./api";
import VoiceInput from "./VoiceInput";


type Pending = "identify" | "procedure" | "guidance" | null;
type Reply = GuidanceResponse | RelationResponse;
// One need of a multi-need message; procedureId is set once it is matched or chosen.
type Section = { need: Need; procedureId?: number; answer?: GuidanceResponse; error?: string };
type Message = {
  id: number;
  question: string;
  // The English query searched and answered for a Tamil question.
  query?: string;
  answer?: Reply;
  sections?: Section[];
  pending?: { phrase: string; question: string }[];
  relation?: { question: string; answer?: RelationResponse; error?: string };
  note?: string;
  // The procedure this message's answer introduces (shown once, above the answer).
  opened?: ProcedureDetail;
  // Set when a related official page answered instead (a fee table naming this procedure).
  source?: string;
};

// A follow-up across several procedures is only sent to the relationship check
// when it asks about order, dependencies or reusing documents.
const ASKS_RELATION = /\b(first|before|after|order|depend\w*|reus\w*|same|both|together|affect\w*|need .* for)\b/i;
const WHICH_ONE = "Which procedure is this about? Use “Ask more about this” on one of them, or describe a new need.";

// Mirrors backend rag.COMPARISON: the backend answers these as a comparison.
const COMPARES = /\b(differ\w*|compar\w*|versus|vs)\b/i;
const NO_COMPARISON = "The approved official pages do not give details that compare these procedures for this question.";
const EXAMPLES = [
  "My passport expired, how do I get a new one?",
  "How do I link my PAN with Aadhaar?",
  "Aadhaar la address change panna enna proof venum?",
  "What is the difference between EPF and EPS?",
];
const NO_RELATION =
  "The approved official sources do not confirm an order, dependency or document reuse between these procedures. " +
  "Use “Ask more about this” to ask about one procedure.";

const message = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;
const asked = (m: Message) => m.query ?? m.question;

// Read-aloud uses only voices installed on this device (Indian English first), so the
// answer is not sent to an online voice service. Answers are in English.
function offlineVoice() {
  const voices = window.speechSynthesis?.getVoices().filter((v) => v.localService && v.lang.startsWith("en")) ?? [];
  return voices.find((v) => v.lang === "en-IN") ?? voices[0];
}

function ReadAloud({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const [, setVoicesLoaded] = useState(0);
  useEffect(() => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    // Browsers load voices asynchronously; render again once they arrive (or if
    // they arrived between the first render and this effect).
    const update = () => setVoicesLoaded((count) => count + 1);
    synth.addEventListener("voiceschanged", update);
    update();
    return () => {
      synth.removeEventListener("voiceschanged", update);
      synth.cancel();
    };
  }, []);
  const voice = offlineVoice();
  if (!voice) return null;
  function play() {
    window.speechSynthesis.cancel(); // stops any other answer being read
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  }
  return speaking ? (
    <button className="secondary-button" type="button" onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); }}>
      Stop reading
    </button>
  ) : (
    <button className="secondary-button" type="button" onClick={play}>Read aloud</button>
  );
}


export default function CitizenPage() {
  const [situation, setSituation] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [matches, setMatches] = useState<IdentifyResponse | null>(null);
  const [procedure, setProcedure] = useState<ProcedureDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending>(null);
  const [error, setError] = useState<{ text: string; retry: () => void } | null>(null);
  const lastId = useRef(0);
  const latest = useRef<HTMLElement>(null);
  // A new question, and again its finished answer, scroll to the top of the window so the answer is read from the start.
  const done = pending === null;
  useEffect(() => {
    latest.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [messages.length, done]);
  const newMessage = (question: string): Message => ({ id: ++lastId.current, question });
  // Updates are keyed by id, so a reply for a message that was reset meanwhile is dropped.
  const update = (id: number, change: (m: Message) => Message) =>
    setMessages((all) => all.map((m) => (m.id === id ? change(m) : m)));
  const updateSection = (id: number, index: number, change: Partial<Section>) =>
    update(id, (m) => ({ ...m, sections: m.sections?.map((s, i) => (i === index ? { ...s, ...change } : s)) }));
  // Remembers the English query a Tamil question was searched as.
  function searchedAs(message: Message, result: IdentifyResponse): Message {
    if (!result.normalized_query) return message;
    update(message.id, (m) => ({ ...m, query: result.normalized_query }));
    return { ...message, query: result.normalized_query };
  }
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
    // An already normalized query is English and is not normalized again.
    const reply = await askGuidance(id, asked(message), message.query ? "en" : language);
    const source = reply.procedure_id === id ? undefined : (await getProcedure(reply.procedure_id)).name;
    update(message.id, (m) => ({ ...m, answer: reply, source, query: reply.normalized_query ?? m.query }));
    return reply;
  }

  // A follow-up is answered from the open procedure. When that page does not answer it,
  // the question is searched again, and a different procedure that matches answers it
  // (a fee asked about on the renewal page is on the fees page).
  async function answerFollowUp(id: number, message: Message) {
    const reply = await answer(id, message);
    if (!reply.insufficient_evidence) return;
    const query = reply.normalized_query;
    const result = await identifyProcedure(query ?? message.question, query ? "en" : language);
    const other = result.status === "matched" ? result.candidates[0].id : undefined;
    if (other && other !== id) await showAndAnswer(other, message);
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
    message = searchedAs(message, result);
    if (result.status === "matched") await showAndAnswer(result.candidates[0].id, message);
    if (result.status === "multiple") await answerNeeds(message, result);
  }

  // With several procedures on screen, a follow-up about one of them answers from it;
  // a question about how they relate goes to the relationship check; anything else
  // unclear asks the citizen which procedure they mean.
  async function followUp(message: Message, active: number[]) {
    const result = await identifyProcedure(message.question, language);
    message = searchedAs(message, result);
    const hit = result.status === "matched" ? result.candidates[0].id : undefined;
    if (hit && active.includes(hit)) {
      await answer(hit, message);
      return;
    }
    if (result.status === "no_match" || result.status === "ambiguous") {
      const note = result.clarification ?? WHICH_ONE;
      if (result.clarification || !ASKS_RELATION.test(asked(message))) return update(message.id, (m) => ({ ...m, note }));
      setPending("guidance");
      const reply = await askRelation(active, asked(message));
      return update(message.id, (m) => ({ ...m, answer: reply }));
    }
    setMessages([message]);
    await handleResult(result, message);
  }

  async function showAndAnswer(id: number, message: Message) {
    const opened = await getProcedure(id);
    setProcedure(opened);
    update(message.id, (m) => ({ ...m, opened }));
    await answer(id, message);
  }

  function openProcedure(id: number) {
    const message = { ...newMessage(messages[0].question), query: messages[0].query };
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
      void run("guidance", () => (procedure ? answerFollowUp(procedure.id, message) : followUp(message, active)),
        "Unable to answer the question.");
      return;
    }
    setMessages([message]);
    void run("identify", async () => handleResult(await identifyProcedure(question, language), message),
      "Unable to search procedures.");
  }

  function renderAnswer(reply: Reply, refusal: ReactNode, names?: Record<number, string>) {
    return (
      <div className="answer">
        {reply.insufficient_evidence ? <p className="feedback" role="status">{refusal}</p> : (
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
        )}
        {reply.omitted_claims > 0 && !reply.insufficient_evidence && (
          <p className="field-help">
            {reply.omitted_claims} statement(s) were left out because the official text did not support them.
          </p>
        )}
        {!reply.insufficient_evidence && (
          <div className="answer-actions">
            <ReadAloud text={reply.claims.map((claim) => claim.text).join(" ")} />
            {"source_url" in reply && (
              <a className="action-link" href={reply.source_url} target="_blank" rel="noopener noreferrer">Official page ↗</a>
            )}
          </div>
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

  function reset() {
    setProcedure(null);
    setMatches(null);
    setMessages([]);
    setError(null);
  }

  // Enter sends (Shift+Enter adds a line); never while an input method (Tamil keyboard) is composing.
  function sendOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const busy = pending !== null;
  const last = messages[messages.length - 1];
  const working = pending === "identify" ? "Searching the approved procedures…"
    : pending === "procedure" ? "Loading the procedure…"
    : pending === "guidance" ? "Checking the official text… this can take up to a minute." : null;

  return (
    <div className="chat">
      <header className="chat-header">
        <span className="chat-brand">ProcedureAssist</span>
        {(messages.length > 0 || procedure) && (
          <button className="secondary-button" type="button" disabled={busy} onClick={reset}>New chat</button>
        )}
      </header>

      <main className="chat-thread">
        {messages.length === 0 && (
          <section className="chat-welcome">
            <h1>Find the right government procedure</h1>
            <p>Describe your situation in your own words, in English or Tamil. Answers come only from approved official pages.</p>
            <div className="examples">
              {EXAMPLES.map((example) => (
                <button key={example} className="example" type="button" onClick={() => setSituation(example)}>{example}</button>
              ))}
            </div>
          </section>
        )}

        {messages.map((m) => (
          <section className="exchange" key={m.id} ref={m === last ? latest : undefined}>
            <div className="user-message"><p>{m.question}</p></div>
            {m.query && m.query !== m.question && <p className="searched-as">Searched as: {m.query}</p>}
            <div className="assistant-message">
              {m.opened && (
                <div className="procedure-intro">
                  <h2>{m.opened.name}</h2>
                  <p className="field-help">
                    {m.opened.department}
                    {matches?.status === "ambiguous" && m.opened.id === procedure?.id && (
                      <button className="link-button" type="button" disabled={busy} onClick={() => setProcedure(null)}>
                        Back to choices
                      </button>
                    )}
                  </p>
                  <details className="procedure-details">
                    <summary>About this procedure ({m.opened.steps.length} steps on the approved page)</summary>
                    <p>{m.opened.summary}</p>
                    {m.opened.eligibility && (
                      <>
                        <h3>Who can apply</h3>
                        <p>{m.opened.eligibility}</p>
                      </>
                    )}
                    <ol>
                      {m.opened.steps.map((step, index) => <li key={index}>{step}</li>)}
                    </ol>
                  </details>
                </div>
              )}
              {m.source && <p className="field-help">From the related official page: <strong>{m.source}</strong></p>}
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
                      <div className="need" key={index}>
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
                      <div className="need">
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
                      </div>
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

              {m === last && matches?.status === "ambiguous" && !procedure && (
                <div className="choices">
                  <h2>Which of these fits your situation?</h2>
                  <p className="field-help">Several procedures could apply. Choose one, or add more detail below.</p>
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
                </div>
              )}
              {m === last && matches?.status === "no_match" && !busy && (
                <p className="feedback" role="status">
                  {matches.clarification ?? (
                    "We don't have an approved procedure that matches this yet. Try describing your " +
                    "situation differently, for example which document or service you need."
                  )}
                </p>
              )}
              {m === last && working && <p className="thinking" role="status">{working}</p>}
              {m === last && error && failure(error.text, error.retry)}
            </div>
          </section>
        ))}
      </main>

      <form className="composer" onSubmit={handleSend}>
        {procedure && <p className="composer-context">Asking about: <strong>{procedure.name}</strong></p>}
        <div className="composer-box">
          <textarea
            id="situation"
            rows={1}
            maxLength={1000}
            aria-label={procedure ? "Ask about this procedure" : "Your situation or question"}
            placeholder={procedure ? "Ask a follow-up question…" : "Ask about a government service…"}
            value={situation}
            onChange={(event) => setSituation(event.target.value)}
            onKeyDown={sendOnEnter}
            required
          />
          <div className="composer-tools">
            <select aria-label="Language" value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
              <option value="en">English</option>
              <option value="ta">தமிழ் (Tamil)</option>
            </select>
            <VoiceInput language={language} disabled={busy}
              onTranscript={(text) => setSituation((current) => (current.trim() ? `${current.trim()} ${text}` : text))} />
            <button className="send-button" type="submit" disabled={busy} aria-label={pending === "identify" ? "Searching…" : "Send"}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
            </button>
          </div>
        </div>
        <p className="composer-note">
          {language === "ta" && "Tamil or Tamil-English is fine. Answers are shown in English, quoted from official pages. "}
          Guidance only: ProcedureAssist does not submit applications; apply on the official page.
        </p>
      </form>
    </div>
  );
}
