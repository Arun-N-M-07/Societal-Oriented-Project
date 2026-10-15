import { useEffect, useState } from "react";

import { deleteProcedure, listSavedProcedures, type SavedProcedure } from "./api";


export default function AdminProcedureList() {
  const [procedures, setProcedures] = useState<SavedProcedure[] | null>(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setProcedures(await listSavedProcedures());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load procedures.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleDelete(procedure: SavedProcedure) {
    if (!window.confirm(`Delete "${procedure.name}"? Citizens will no longer see it.`)) {
      return;
    }
    try {
      await deleteProcedure(procedure.id);
      await load();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Unable to delete procedure.");
    }
  }

  return (
    <section className="admin-page" aria-labelledby="saved-procedures-heading">
      <div className="card">
        <div className="list-header">
          <h2 id="saved-procedures-heading">Saved procedures</h2>
          <button className="secondary-button" type="button" onClick={load}>
            Refresh
          </button>
        </div>
        {error && <p className="feedback error" role="alert">{error}</p>}
        {procedures?.length === 0 && <p>No saved procedures yet.</p>}
        <ul className="procedure-list">
          {procedures?.map((procedure) => (
            <li key={procedure.id}>
              <div>
                <strong>{procedure.name}</strong>
                <a href={procedure.source_url} target="_blank" rel="noopener noreferrer">
                  {procedure.source_url}
                </a>
              </div>
              <button
                className="danger-button"
                type="button"
                onClick={() => handleDelete(procedure)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
