import SiteLink from "../components/SiteLink.jsx";
import PendingForm from "../components/PendingForm.jsx";
import { logo } from "../assets.js";
import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

function LoginCard({ title, intro, children, className = "" }) {
  return <main className="login-page"><section className={`login-card ${className}`} aria-labelledby="page-title">
    <SiteLink href="/index.html#inicio" className="login-logo" aria-label="Voltar para o início"><img src={logo} alt="Comunidade Unidos em Cristo" /></SiteLink>
    <h1 id="page-title">{title}</h1><p>{intro}</p>{children}
  </section></main>;
}

export function LoginPage() {
  const { status, login, ensureSession } = useAuth();
  const { state } = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const safeDestination = ["/agenda.html", "/mural.html", "/area-associado.html", "/perfil.html", "/gestao-grupos.html", "/meus-conteudos.html", "/minha-assinatura.html", "/cadastro.html"].includes(state?.from) || /^\/editor\/(novo|[1-9]\d*)$/.test(state?.from || "");
  const panelDestination = /^\/painel(?:\/(destaques|grupos(?:\/novo)?|fundadores|usuarios|assinaturas|atendimentos|mensagens))?$/.test(state?.from || "");
  const destination = state?.from === "/gestao-comunicacao.html" || safeDestination || panelDestination ? state.from : "/area-associado.html";
  if (status === "authenticated") return <Navigate to={destination} replace state={state?.invitation ? { invitation: state.invitation } : undefined} />;
  async function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try { await login({ email: data.get("email"), password: data.get("senha") }); }
    catch (failure) { setError(failure.status ? failure.message : "Não foi possível entrar. Verifique sua conexão e tente novamente."); }
    finally { setBusy(false); }
  }
  return <LoginCard title="Bem-vindo de volta" intro="Acesse sua área da Comunidade Unidos em Cristo.">
    <form className="login-form" onSubmit={submit}>
      <label htmlFor="email">E-mail<input id="email" name="email" type="email" autoComplete="email" required /></label>
      <label htmlFor="senha">Senha<input id="senha" name="senha" type="password" autoComplete="current-password" required /></label>
      <button className="btn btn-red login-submit" type="submit" disabled={busy || ["unknown", "checking"].includes(status)}>{busy ? "Entrando…" : "Entrar"}</button>
      <SiteLink className="login-help" href="/recuperar-senha.html">Esqueci minha senha</SiteLink>
      <SiteLink className="btn login-back" href="/index.html#inicio">← Voltar ao início</SiteLink>
      <p className="form-feedback" role="alert">{error}</p>
    </form>
  </LoginCard>;
}

export { default as RegisterPage } from "./RegistrationPage.jsx";

export function RecoverPasswordPage() {
  return <LoginCard title="Recupere seu acesso" intro="Informe seu e-mail para receber as instruções de recuperação.">
    <PendingForm message="A recuperação de senha ainda não está disponível. Nenhum e-mail foi enviado.">
      <label htmlFor="email">E-mail<input id="email" name="email" type="email" autoComplete="email" required /></label>
      <button className="btn btn-red login-submit" type="submit">Enviar instruções</button>
      <SiteLink className="btn login-back" href="/login.html">Voltar ao login</SiteLink>
    </PendingForm>
  </LoginCard>;
}
