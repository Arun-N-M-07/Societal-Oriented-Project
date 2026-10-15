import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  approveProcedure,
  extractProcedure,
  reExtractProcedure,
  type ProcedureSpine,
} from "./api";


type EditableTextField =
  | "name"
  | "department"
  | "jurisdiction"
  | "summary"
  | "eligibility";


type StepItem = { id: number; text: string };

let nextStepId = 0;

function toStepItems(texts: string[]): StepItem[] {
  return texts.map((text) => ({ id: nextStepId++, text }));
}


export default function AdminPage({ onSaved }: { onSaved?: () => void }) {
  const [sourceUrl, setSourceUrl] = useState("");
  const [extractedSourceText, setExtractedSourceText] = useState("");
  const [provenanceToken, setProvenanceToken] = useState("");
  const [procedure, setProcedure] = useState<ProcedureSpine | null>(null);
  const [error, setError] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [steps, setSteps] = useState<StepItem[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const refocusStepId = useRef<number | null>(null);

  // Messages render at the top of the page; bring them into view after Approve.
  useEffect(() => {
    if (error || savedMessage) {
      document
        .querySelector(".feedback")
        ?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    }
  }, [error, savedMessage]);

  useEffect(() => {
    if (refocusStepId.current === null) return;
    document
      .querySelector<HTMLElement>(`[data-handle-id="${refocusStepId.current}"]`)
      ?.focus();
    refocusStepId.current = null;
  }, [steps]);

  function updateTextField(field: EditableTextField, value: string) {
    setProcedure((current) =>
      current ? { ...current, [field]: value } : current,
    );
  }

  function updateStep(index: number, text: string) {
    setSteps((current) =>
      current.map((step, i) => (i === index ? { ...step, text } : step)),
    );
  }

  function addStep() {
    setSteps((current) => [...current, ...toStepItems([""])]);
  }

  function removeStep(index: number) {
    setSteps((current) =>
      current.length > 1 ? current.filter((_, i) => i !== index) : current,
    );
  }

  function moveStep(from: number, to: number) {
    if (from === to || to < 0 || to >= steps.length) return;
    setSteps((current) => {
      const next = [...current];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }

  function endDrag() {
    setDragIndex(null);
    setOverIndex(null);
  }

  async function handleExtract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSavedMessage("");
    setIsLoading(true);

    try {
      const extraction = await extractProcedure(sourceUrl);
      setProcedure(extraction.procedure);
      setSteps(toStepItems(extraction.procedure.steps));
      setExtractedSourceText(extraction.source_text);
      setProvenanceToken(extraction.provenance_token);
    } catch (requestError) {
      setProcedure(null);
      setSteps([]);
      setExtractedSourceText("");
      setProvenanceToken("");
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to extract procedure.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReExtract() {
    if (!procedure) return;

    setError("");
    setSavedMessage("");
    setIsLoading(true);

    try {
      const extractedProcedure = await reExtractProcedure({
        source_url: procedure.source_url,
        source_text: extractedSourceText,
        provenance_token: provenanceToken,
      });
      setProcedure(extractedProcedure);
      setSteps(toStepItems(extractedProcedure.steps));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to re-extract procedure.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleDiscard() {
    if (!window.confirm("Clear this review and return to the URL form?")) return;

    setSourceUrl("");
    setExtractedSourceText("");
    setProvenanceToken("");
    setProcedure(null);
    setSteps([]);
    setError("");
    setSavedMessage("");
  }

  async function handleApprove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!procedure) return;

    setError("");

    const reviewedProcedure: ProcedureSpine = {
      ...procedure,
      name: procedure.name.trim(),
      department: procedure.department?.trim() || null,
      jurisdiction: procedure.jurisdiction?.trim() || null,
      summary: procedure.summary.trim(),
      eligibility: procedure.eligibility?.trim() || null,
      steps: steps.map((step) => step.text.trim()).filter(Boolean),
    };

    if (
      !reviewedProcedure.name ||
      !reviewedProcedure.summary ||
      reviewedProcedure.steps.length === 0
    ) {
      setError("Name, summary, and at least one step are required.");
      return;
    }

    setProcedure(reviewedProcedure);
    setIsSaving(true);

    try {
      const saved = await approveProcedure({
        procedure: reviewedProcedure,
        source_text: extractedSourceText,
        provenance_token: provenanceToken,
      });
      setSavedMessage(`Saved ${saved.name} with ID ${saved.id}.`);
      onSaved?.();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to save procedure.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="admin-page">
      <header className="page-header">
        <p className="eyebrow">ProcedureAssist</p>
        <h1>Procedure review</h1>
        <p>Extract a government procedure, review it, and approve the result.</p>
      </header>

      <form className="card" onSubmit={handleExtract}>
        <div className="form-field">
          <label htmlFor="source-url">Source URL</label>
          <input
            id="source-url"
            type="url"
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            required
          />
        </div>

        <button
          className="primary-button"
          type="submit"
          disabled={isLoading || isSaving}
        >
          {isLoading ? "Extracting…" : "Extract"}
        </button>
      </form>

      {error && <p className="feedback error" role="alert">{error}</p>}
      {savedMessage && (
        <p className="feedback success" role="status">{savedMessage}</p>
      )}

      {procedure && (
        <section
          className="card review-card"
          aria-labelledby="extracted-procedure-heading"
        >
          <h2 id="extracted-procedure-heading">Review extracted procedure</h2>
          <p className="section-intro">
            Correct any AI-generated details before approving this procedure.
          </p>

          <form className="review-form" onSubmit={handleApprove}>
            <div className="form-field">
              <label htmlFor="procedure-source-url">Source URL</label>
              <input
                id="procedure-source-url"
                value={procedure.source_url}
                readOnly
              />
              <small>This verified URL cannot be edited during review.</small>
            </div>

            <div className="form-field">
              <label htmlFor="procedure-source-text">Source text</label>
              <textarea
                id="procedure-source-text"
                rows={8}
                value={extractedSourceText}
                readOnly
              />
              <small>This is the text collected from the source page.</small>
            </div>

            <div className="form-field">
              <label htmlFor="procedure-name">Name</label>
              <input
                id="procedure-name"
                value={procedure.name}
                onChange={(event) => updateTextField("name", event.target.value)}
                required
              />
            </div>

            <div className="field-grid">
              <div className="form-field">
                <label htmlFor="procedure-department">Department</label>
                <input
                  id="procedure-department"
                  value={procedure.department ?? ""}
                  onChange={(event) =>
                    updateTextField("department", event.target.value)
                  }
                />
              </div>

              <div className="form-field">
                <label htmlFor="procedure-jurisdiction">Jurisdiction</label>
                <input
                  id="procedure-jurisdiction"
                  value={procedure.jurisdiction ?? ""}
                  onChange={(event) =>
                    updateTextField("jurisdiction", event.target.value)
                  }
                />
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="procedure-summary">Summary</label>
              <textarea
                id="procedure-summary"
                rows={6}
                value={procedure.summary}
                onChange={(event) =>
                  updateTextField("summary", event.target.value)
                }
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="procedure-eligibility">Eligibility</label>
              <textarea
                id="procedure-eligibility"
                rows={5}
                value={procedure.eligibility ?? ""}
                onChange={(event) =>
                  updateTextField("eligibility", event.target.value)
                }
              />
            </div>

            <fieldset className="steps-fieldset">
              <legend>Steps</legend>
              <p className="field-help">
                Drag a step by its handle to reorder it, or focus the handle and
                press Arrow Up or Arrow Down.
              </p>
              {steps.map((step, index) => {
                const dropClass =
                  dragIndex !== null && overIndex === index && dragIndex !== index
                    ? dragIndex < index
                      ? " drop-after"
                      : " drop-before"
                    : "";
                return (
                  <div
                    className={`step-row${dragIndex === index ? " dragging" : ""}${dropClass}`}
                    key={step.id}
                    data-testid="step-row"
                    onDragOver={(event) => {
                      if (dragIndex === null) return;
                      event.preventDefault();
                      setOverIndex(index);
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      if (dragIndex !== null) moveStep(dragIndex, index);
                      endDrag();
                    }}
                  >
                    <label htmlFor={`procedure-step-${step.id}`}>
                      Step {index + 1}
                    </label>
                    <div className="step-controls">
                      <button
                        className="drag-handle"
                        type="button"
                        draggable
                        data-handle-id={step.id}
                        aria-label={`Move step ${index + 1}`}
                        title="Drag to reorder, or press Arrow Up / Arrow Down"
                        onDragStart={(event) => {
                          event.dataTransfer.effectAllowed = "move";
                          event.dataTransfer.setData("text/plain", String(index));
                          const row = event.currentTarget.closest(".step-row");
                          if (row) event.dataTransfer.setDragImage(row, 16, 16);
                          setDragIndex(index);
                        }}
                        onDragEnd={endDrag}
                        onKeyDown={(event) => {
                          if (event.key !== "ArrowUp" && event.key !== "ArrowDown") {
                            return;
                          }
                          event.preventDefault();
                          const target = index + (event.key === "ArrowUp" ? -1 : 1);
                          if (target < 0 || target >= steps.length) return;
                          refocusStepId.current = step.id;
                          moveStep(index, target);
                        }}
                      >
                        ⋮⋮
                      </button>
                      <textarea
                        id={`procedure-step-${step.id}`}
                        className="step-text"
                        rows={2}
                        value={step.text}
                        onChange={(event) => updateStep(index, event.target.value)}
                      />
                      <button
                        className="danger-button"
                        type="button"
                        onClick={() => removeStep(index)}
                        disabled={steps.length === 1}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                );
              })}
              <button
                className="secondary-button"
                type="button"
                onClick={addStep}
              >
                Add step
              </button>
            </fieldset>

            <div className="review-actions">
              <button
                className="danger-button"
                type="button"
                onClick={handleDiscard}
                disabled={isLoading || isSaving}
              >
                Discard
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={handleReExtract}
                disabled={isLoading || isSaving || Boolean(savedMessage)}
              >
                {isLoading ? "Re-extracting…" : "Re-extract"}
              </button>
              <button
                className="primary-button"
                type="submit"
                disabled={isSaving || isLoading || Boolean(savedMessage)}
              >
                {isSaving
                  ? "Saving…"
                  : savedMessage
                    ? "Saved"
                    : "Approve and save"}
              </button>
            </div>
          </form>
        </section>
      )}
    </main>
  );
}
