import SiteLink from "../components/SiteLink.jsx";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { NewsletterPreference } from "./CommunicationsPages.jsx";
function StatusPage({ icon, tone, title, children }) {
  return <main className="utility-page"><section className="utility-card status-card" aria-labelledby="page-title">
    {icon && <div className={`status-icon status-${tone}`} aria-hidden="true">{icon}</div>}
    <h1 id="page-title">{title}</h1>{children}
  </section></main>;
}

export function AccessDeniedPage() {
  return <StatusPage icon="×" tone="error" title="Acesso restrito"><p>Esta área é exclusiva para associados com pagamento confirmado e cadastro concluído.</p><SiteLink className="btn btn-red" href="/login.html">Ir para o login</SiteLink><SiteLink className="utility-link" href="/index.html#inicio">Voltar ao início</SiteLink></StatusPage>;
}

export function ExpiredLinkPage() {
  return <StatusPage icon="!" tone="error" title="Link indisponível"><p>Este link de cadastro expirou ou já foi utilizado. Solicite um novo link pelo e-mail cadastrado.</p><SiteLink className="btn btn-red" href="/cadastro.html">Solicitar novo link</SiteLink><SiteLink className="utility-link" href="/index.html#inicio">Voltar ao início</SiteLink></StatusPage>;
}

const paymentStates = {
  success: { icon: "!", tone: "pending", title: "Aguarde a confirmação do pagamento", text: "O retorno do checkout não comprova o pagamento. Após a confirmação pelo PagBank, enviaremos um link exclusivo por e-mail para você concluir seu cadastro.", primary: "Consultar minha assinatura", href: "/minha-assinatura.html", secondary: true },
  pending: { icon: "!", tone: "pending", title: "Pagamento em análise", text: "Seu pagamento ainda está sendo processado. Assim que houver uma confirmação, você receberá as próximas instruções por e-mail.", primary: "Voltar ao início", href: "/index.html#inicio" },
  cancelled: { icon: "×", tone: "error", title: "Pagamento não concluído", text: "Não foi possível concluir o pagamento. Você pode voltar aos planos e tentar novamente quando desejar.", primary: "Ver planos novamente", href: "/index.html#associacao" },
};

export function PaymentPage({ state }) {
  const page = paymentStates[state];
  return <StatusPage icon={page.icon} tone={page.tone} title={page.title}><p>{page.text}</p><SiteLink className="btn btn-red" href={page.href}>{page.primary}</SiteLink>{page.secondary && <SiteLink className="utility-link" href="/index.html#inicio">Voltar ao início</SiteLink>}</StatusPage>;
}

export function MemberPage() {
  const { user, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function signOut() {
    setBusy(true); setError("");
    try { await logout(); }
    catch { setError("Não foi possível sair. Tente novamente."); }
    finally { setBusy(false); }
  }
  return <main className="member-page"><section className="member-panel" aria-labelledby="page-title">
    <div className="member-header"><div><span className="eyebrow">Minha conta</span><h1 id="page-title">Olá, {user.display_name || "associado"}</h1><p>Acompanhe os conteúdos da Comunidade Unidos em Cristo.</p></div><div className="account-actions"><SiteLink className="btn login-back" href="/perfil.html">Meu perfil</SiteLink><button className="btn login-back" type="button" disabled={busy} onClick={signOut}>{busy ? "Saindo…" : "Sair"}</button></div></div>
    <p className="form-feedback" role="alert">{error}</p>
    {user.can_access_panel && <aside className="account-subscription"><div><h2>Administração da comunidade</h2><p>Acompanhe os indicadores e gerencie as páginas, a equipe e os destaques do site.</p></div><SiteLink className="btn btn-red" href="/painel">Abrir painel de administração</SiteLink></aside>}
    <aside className="account-subscription" aria-labelledby="account-subscription-title">
      <div><h2 id="account-subscription-title">Minha assinatura</h2><p>Consulte a validade ou cancele as próximas cobranças. O acesso continua até o fim do período já pago.</p></div>
      <SiteLink className="btn btn-red" href="/minha-assinatura.html">Gerenciar ou cancelar assinatura</SiteLink>
    </aside>
    <div className="member-grid">
      <article className="member-item"><span aria-hidden="true">✦</span><h2>Artigos</h2><p>Leia os artigos publicados pelos facilitadores.</p></article>
      <article className="member-item"><span aria-hidden="true">▣</span><h2>Vídeos</h2><p>Assista aos vídeos do YouTube dentro do próprio site.</p></article>
      <article className="member-item"><span aria-hidden="true">♫</span><h2>Áudios</h2><p>Ouça os áudios publicados pelos facilitadores.</p></article>
    </div>
    <NewsletterPreference />
    {user.can_manage_communications && <p className="account-actions"><SiteLink className="btn btn-red" href="/gestao-comunicacao.html">Gerenciar agenda, mural e newsletter</SiteLink></p>}
    <p className="account-note">Confira os conteúdos publicados na Comunidade Online.</p>
    <div className="account-actions">{user.capabilities?.create_content && <SiteLink className="btn btn-red" href="/meus-conteudos.html">{user.can_manage_editorial_groups ? "Conteúdos dos grupos" : "Meus conteúdos"}</SiteLink>}<SiteLink className="btn login-back" href="/comunidade-online.html">Comunidade Online</SiteLink><SiteLink className="btn login-back" href="/grupos.html">Conhecer os grupos</SiteLink>{user.can_manage_editorial_groups && <SiteLink className="btn btn-red" href="/gestao-grupos.html">Gerenciar meus grupos</SiteLink>}</div>
  </section></main>;
}
