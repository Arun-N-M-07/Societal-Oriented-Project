import { useEffect, useState } from "react";

import AdminLogin from "./AdminLogin";
import AdminPage from "./AdminPage";
import AdminProcedureList from "./AdminProcedureList";
import { getSession, logout, UNAUTHORIZED_EVENT } from "./api";


export default function App() {
  // undefined: checking the session; null: signed out.
  const [admin, setAdmin] = useState<string | null>();
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getSession().then(
      (session) => setAdmin(session.username),
      () => setAdmin(null),
    );
    function expire() {
      setAdmin(null);
      setNotice("Your session has expired. Please sign in again.");
    }
    window.addEventListener(UNAUTHORIZED_EVENT, expire);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, expire);
  }, []);

  async function handleSignOut() {
    await logout().catch(() => undefined);
    setNotice("");
    setAdmin(null);
  }

  if (admin === undefined) return <p className="session-bar">Loading…</p>;
  if (admin === null) {
    return (
      <AdminLogin
        notice={notice}
        onSignedIn={(username) => {
          setNotice("");
          setAdmin(username);
        }}
      />
    );
  }
  return (
    <>
      <div className="session-bar">
        Signed in as {admin}
        <button className="secondary-button" type="button" onClick={handleSignOut}>
          Sign out
        </button>
      </div>
      <AdminPage />
      <AdminProcedureList />
    </>
  );
}
