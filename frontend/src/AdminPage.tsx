import { useState, type FormEvent } from "react";

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


export default function AdminPage() {
  const [sourceUrl, setSourceUrl] = useState("");
  const [extractedSourceText, setExtractedSourceText] = useState("");
  const [procedure, setProcedure] = useState<ProcedureSpine | null>(null);
  const [error, setError] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  function updateTextField(field: EditableTextField, value: string) {
    setProcedure((current) =>
      current ? { ...current, [field]: value } : current,
    );
  }

  function updateStep(index: number, value: string) {
    setProcedure((current) => {
      if (!current) return current;
      const steps = [...current.steps];
      steps[index] = value;
      return { ...current, steps };
    });
  }

  function insertStep(index: number) {
    setProcedure((current) => {
      if (!current) return current;
      const steps = [...current.steps];
      steps.splice(index, 0, "");
      return { ...current, steps };
    });
  }

  function removeStep(index: number) {
    setProcedure((current) =>
      current && current.steps.length > 1
        ? {
            ...current,
            steps: current.steps.filter((_, stepIndex) => stepIndex !== index),
          }
        : current,
    );
  }

  async function handleExtract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSavedMessage("");
    setIsLoading(true);

    try {
      const extraction = await extractProcedure(sourceUrl);
      setProcedure(extraction.procedure);
      setExtractedSourceText(extraction.source_text);
    } catch (requestError) {
      setProcedure(null);
      setExtractedSourceText("");
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
      });
      setProcedure(extractedProcedure);
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
    setProcedure(null);
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
      steps: procedure.steps.map((step) => step.trim()).filter(Boolean),
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
      });
      setSavedMessage(`Saved ${saved.name} with ID ${saved.id}.`);
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
                rows={4}
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
                rows={3}
                value={procedure.eligibility ?? ""}
                onChange={(event) =>
                  updateTextField("eligibility", event.target.value)
                }
              />
            </div>

            <fieldset className="steps-fieldset">
              <legend>Steps</legend>
              <p className="field-help">
                Insert a new step before any existing step, or add one at the end.
              </p>
              {procedure.steps.map((step, index) => (
                <div className="step-row" key={index}>
                  <label htmlFor={`procedure-step-${index}`}>
                    Step {index + 1}
                  </label>
                  <div className="step-controls">
                    <input
                      id={`procedure-step-${index}`}
                      value={step}
                      onChange={(event) => updateStep(index, event.target.value)}
                    />
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => insertStep(index)}
                    >
                      Insert before
                    </button>
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => removeStep(index)}
                      disabled={procedure.steps.length === 1}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
              <button
                className="secondary-button"
                type="button"
                onClick={() => insertStep(procedure.steps.length)}
              >
                Add step at end
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
