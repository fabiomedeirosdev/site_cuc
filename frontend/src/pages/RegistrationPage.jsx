import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import SiteLink from "../components/SiteLink.jsx";
import { logo } from "../assets.js";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { LegalCheck, ResendInviteForm } from "./SubscriptionPages.jsx";

export default function RegistrationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, ensureSession, acceptSession } = useAuth();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("convite") || location.state?.invitation || "");
  const [invitation, setInvitation] = useState(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    ensureSession();
    if (!token) return;
    if (location.hash) navigate(location.pathname, { replace: true });
    let active = true;
    api.checkInvitation(token).then((data) => { if (active) setInvitation(data); }).catch((failure) => { if (active) setError(failure.message || "Não foi possível verificar o convite."); });
    return () => { active = false; };
  }, [token, ensureSession]);
  async function register(event) {
    event.preventDefault(); setError("");
    const form = new FormData(event.currentTarget);
    if (!invitation.existing_account && form.get("senha") !== form.get("confirmar-senha")) { setError("As senhas não coincidem."); return; }
    setBusy(true);
    try {
      const result = await api.completeInvitation({ token, name: form.get("nome") || "", password: form.get("senha") || "", accepted, legal_version: invitation.legal_version });
      acceptSession(result.user);
      navigate("/area-associado.html", { replace: true });
    } catch (failure) { setError(failure.message || "Não foi possível concluir o cadastro."); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-card register-card"><SiteLink href="/index.html#inicio" className="login-logo" aria-label="Voltar para o início"><img src={logo} alt="Comunidade Unidos em Cristo" /></SiteLink><h1>Conclua seu cadastro</h1><p>Crie seu acesso à área exclusiva da Comunidade Unidos em Cristo.</p><div className="register-note" role="note">O cadastro é liberado pelo link pessoal enviado após a confirmação do pagamento.</div>
    {token && !invitation && !error && <p role="status">Verificando seu link…</p>}
    {invitation && invitation.existing_account && !user && <><p>Já existe uma conta para {invitation.email}. Entre para vincular a assinatura, sem alterar sua senha.</p><SiteLink className="btn btn-red" href="/login.html" state={{ from: "/cadastro.html", invitation: token }}>Entrar e vincular assinatura</SiteLink></>}
    {invitation && (!invitation.existing_account || user) && <form className="login-form" onSubmit={register}>
      {!invitation.existing_account && <><label htmlFor="nome">Nome completo<input id="nome" name="nome" type="text" autoComplete="name" required maxLength={150} /></label><label htmlFor="email">E-mail do pagamento<input id="email" type="email" value={invitation.email} readOnly autoComplete="email" /></label><label htmlFor="senha">Crie uma senha<input id="senha" name="senha" type="password" autoComplete="new-password" minLength="8" required /></label><label htmlFor="confirmar-senha">Confirme sua senha<input id="confirmar-senha" name="confirmar-senha" type="password" autoComplete="new-password" minLength="8" required /></label></>}
      {invitation.existing_account && <p>Vincular a assinatura de {invitation.email} à sua conta autenticada.</p>}
      <LegalCheck checked={accepted} onChange={setAccepted} /><button className="btn btn-red login-submit" type="submit" disabled={busy}>{busy ? "Concluindo…" : invitation.existing_account ? "Vincular assinatura" : "Concluir cadastro"}</button>
    </form>}
    <p className="form-feedback" role="alert">{error}</p>{(!token || error) && <ResendInviteForm />}<SiteLink className="btn login-back" href="/login.html">Já tenho cadastro</SiteLink><SiteLink className="btn login-back" href="/index.html#inicio">← Voltar ao início</SiteLink>
  </section></main>;
}
