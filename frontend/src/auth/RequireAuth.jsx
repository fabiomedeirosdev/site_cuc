import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";


export default function RequireAuth({ children }) {
  const { status, error, ensureSession } = useAuth();
  const location = useLocation();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  if (["unknown", "checking"].includes(status)) {
    return <main className="utility-page"><section className="utility-card"><p role="status">Verificando seu acesso…</p></section></main>;
  }
  if (status === "error") {
    return <main className="utility-page"><section className="utility-card"><p role="alert">{error}</p><button type="button" className="btn btn-red" onClick={() => ensureSession(true)}>Tentar novamente</button></section></main>;
  }
  if (status === "guest") return <Navigate to="/login.html" replace state={{ from: location.pathname }} />;
  return children;
}
