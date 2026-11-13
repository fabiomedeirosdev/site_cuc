import { useEffect, useRef } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import HomePage from "./pages/HomePage.jsx";
import { LoginPage, RegisterPage, RecoverPasswordPage } from "./pages/AccessPages.jsx";
import { MemberPage, AccessDeniedPage, ExpiredLinkPage, PaymentPage } from "./pages/UtilityPages.jsx";
import { PrivacyPage, TermsPage } from "./pages/LegalPages.jsx";
import SiteLink from "./components/SiteLink.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import RequireAuth from "./auth/RequireAuth.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import { FoundersPage, ManageFoundersPage } from "./pages/FoundersPages.jsx";
import { PublicProfilesPage, PublicProfilePage, ConfirmEmailPage } from "./pages/PublicProfilesPages.jsx";
import { GroupsPage, GroupDetailPage, ColumnistsPage, ManageGroupsPage } from "./pages/GroupsPages.jsx";
import { ContentCatalogPage, ContentReadPage, MyContentPage, ContentEditorPage } from "./pages/ContentPages.jsx";
import { SubscribePage, MySubscriptionPage } from "./pages/SubscriptionPages.jsx";
import { AgendaPage, MuralPage, ManageCommunicationsPage, NewsletterActionPage } from "./pages/CommunicationsPages.jsx";
import { DashboardPage, HighlightsPage, GroupSettingsPage, NewGroupPage, AdministrationTablePage } from "./pages/ManagementPages.jsx";

const pageTitles = {
  "/fundadores.html": "Fundadores | Comunidade Unidos em Cristo",
  "/painel/fundadores": "Editar fundadores | Comunidade Unidos em Cristo",
  "/painel": "Painel de administração | Comunidade Unidos em Cristo",
  "/painel/destaques": "Destaques do site | Comunidade Unidos em Cristo",
  "/painel/grupos": "Páginas dos grupos | Comunidade Unidos em Cristo",
  "/painel/grupos/novo": "Criar grupo | Comunidade Unidos em Cristo",
  "/painel/usuarios": "Usuários | Comunidade Unidos em Cristo",
  "/painel/assinaturas": "Assinaturas | Comunidade Unidos em Cristo",
  "/painel/atendimentos": "Atendimentos | Comunidade Unidos em Cristo",
  "/": "Comunidade Unidos em Cristo", "/index.html": "Comunidade Unidos em Cristo",
  "/login.html": "Login | Comunidade Unidos em Cristo",
  "/cadastro.html": "Concluir cadastro | Comunidade Unidos em Cristo",
  "/assinatura.html": "Assinatura | Comunidade Unidos em Cristo",
  "/minha-assinatura.html": "Minha assinatura | Comunidade Unidos em Cristo",
  "/agenda.html": "Agenda | Comunidade Unidos em Cristo",
  "/mural.html": "Mural | Comunidade Unidos em Cristo",
  "/gestao-comunicacao.html": "Comunicação | Comunidade Unidos em Cristo",
  "/newsletter.html": "Newsletter | Comunidade Unidos em Cristo",
  "/recuperar-senha.html": "Recuperar senha | Comunidade Unidos em Cristo",
  "/area-associado.html": "Área do associado | Comunidade Unidos em Cristo",
  "/acesso-negado.html": "Acesso restrito | Comunidade Unidos em Cristo",
  "/link-expirado.html": "Link indisponível | Comunidade Unidos em Cristo",
  "/pagamento-sucesso.html": "Confirmação do pagamento | Comunidade Unidos em Cristo",
  "/pagamento-pendente.html": "Pagamento em análise | Comunidade Unidos em Cristo",
  "/pagamento-cancelado.html": "Pagamento não concluído | Comunidade Unidos em Cristo",
  "/politica-privacidade.html": "Política de privacidade | Comunidade Unidos em Cristo",
  "/termos.html": "Termos de uso | Comunidade Unidos em Cristo",
  "/perfil.html": "Meu perfil | Comunidade Unidos em Cristo",
  "/perfis.html": "Pessoas da comunidade | Comunidade Unidos em Cristo",
  "/confirmar-email.html": "Confirmar e-mail | Comunidade Unidos em Cristo",
  "/grupos.html": "Nossos Grupos | Comunidade Unidos em Cristo",
  "/facilitadores.html": "Facilitadores | Comunidade Unidos em Cristo",
  "/gestao-grupos.html": "Gestão dos Grupos | Comunidade Unidos em Cristo",
};

function PageMetadata() {
  const { pathname } = useLocation();
  useEffect(() => {
    document.title = pageTitles[pathname] ?? "Comunidade Unidos em Cristo";
    const accessDescriptions = {
      "/login.html": "Login da Comunidade Unidos em Cristo.",
      "/cadastro.html": "Cadastro exclusivo da Comunidade Unidos em Cristo.",
    };
    const description = pathname === "/" || pathname === "/index.html"
      ? "Comunidade Online Católica Unidos em Cristo. Fé, formação, espiritualidade e vida em comunidade."
      : accessDescriptions[pathname] ?? pageTitles[pathname] ?? "Comunidade Unidos em Cristo";
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "description";
      document.head.append(meta);
    }
    meta.content = description;
  }, [pathname]);
  return null;
}

function PageNavigation() {
  const { pathname, hash, key } = useLocation();
  const previousLocation = useRef(null);
  useEffect(() => {
    const locationId = `${pathname}${hash}:${key}`;
    const shouldFocus = Boolean(hash) || (previousLocation.current !== null && previousLocation.current !== locationId);
    previousLocation.current = locationId;
    const frame = requestAnimationFrame(() => {
      let anchorId = hash.slice(1);
      try { anchorId = decodeURIComponent(anchorId); } catch { /* Unknown malformed anchor. */ }
      const target = hash ? document.getElementById(anchorId) : document.querySelector("main");
      if (target && shouldFocus) {
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      }
      if (hash && target) {
        const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
        target.scrollIntoView({ block: "start", behavior });
      } else {
        window.scrollTo({ top: 0, behavior: "instant" });
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [pathname, hash, key]);
  return null;
}

function NotFoundPage() {
  return <main className="utility-page"><section className="utility-card status-card" aria-labelledby="not-found-title"><h1 id="not-found-title">Página não encontrada</h1><SiteLink className="btn btn-red" href="/index.html#inicio">Voltar ao início</SiteLink></section></main>;
}

export function AppRoutes() {
  return <AuthProvider>
    <PageMetadata />
    <PageNavigation />
    <Routes>
      <Route path="/fundadores.html" element={<FoundersPage />} />
      <Route path="/painel/fundadores" element={<RequireAuth><ManageFoundersPage /></RequireAuth>} />
      <Route path="/painel" element={<RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/painel/destaques" element={<RequireAuth><HighlightsPage /></RequireAuth>} />
      <Route path="/painel/grupos" element={<RequireAuth><GroupSettingsPage /></RequireAuth>} />
      <Route path="/painel/grupos/novo" element={<RequireAuth><NewGroupPage /></RequireAuth>} />
      <Route path="/painel/usuarios" element={<RequireAuth><AdministrationTablePage key="users" section="users" /></RequireAuth>} />
      <Route path="/painel/assinaturas" element={<RequireAuth><AdministrationTablePage key="subscriptions" section="subscriptions" /></RequireAuth>} />
      <Route path="/painel/atendimentos" element={<RequireAuth><AdministrationTablePage key="requests" section="requests" /></RequireAuth>} />
      <Route path="/" element={<HomePage />} />
      <Route path="/index.html" element={<HomePage />} />
      <Route path="/login.html" element={<LoginPage />} />
      <Route path="/cadastro.html" element={<RegisterPage />} />
      <Route path="/recuperar-senha.html" element={<RecoverPasswordPage />} />
      <Route path="/area-associado.html" element={<RequireAuth><MemberPage /></RequireAuth>} />
      <Route path="/perfil.html" element={<RequireAuth><ProfilePage /></RequireAuth>} />
      <Route path="/perfis.html" element={<PublicProfilesPage />} />
      <Route path="/perfis/:id" element={<PublicProfilePage />} />
      <Route path="/confirmar-email.html" element={<ConfirmEmailPage />} />
      <Route path="/grupos.html" element={<GroupsPage />} />
      <Route path="/grupos/:slug" element={<GroupDetailPage />} />
      <Route path="/facilitadores.html" element={<ColumnistsPage />} />
      <Route path="/colunistas.html" element={<Navigate to="/facilitadores.html" replace />} />
      <Route path="/gestao-grupos.html" element={<RequireAuth><ManageGroupsPage /></RequireAuth>} />
      <Route path="/comunidade-online.html" element={<ContentCatalogPage />} />
      <Route path="/conteudos/:id" element={<ContentReadPage />} />
      <Route path="/meus-conteudos.html" element={<RequireAuth><MyContentPage /></RequireAuth>} />
      <Route path="/editor/novo" element={<RequireAuth><ContentEditorPage /></RequireAuth>} />
      <Route path="/editor/:id" element={<RequireAuth><ContentEditorPage /></RequireAuth>} />
      <Route path="/assinatura.html" element={<SubscribePage />} />
      <Route path="/agenda.html" element={<AgendaPage />} />
      <Route path="/mural.html" element={<MuralPage />} />
      <Route path="/newsletter.html" element={<NewsletterActionPage />} />
      <Route path="/gestao-comunicacao.html" element={<RequireAuth><ManageCommunicationsPage /></RequireAuth>} />
      <Route path="/minha-assinatura.html" element={<RequireAuth><MySubscriptionPage /></RequireAuth>} />
      <Route path="/acesso-negado.html" element={<AccessDeniedPage />} />
      <Route path="/link-expirado.html" element={<ExpiredLinkPage />} />
      <Route path="/pagamento-sucesso.html" element={<PaymentPage state="success" />} />
      <Route path="/pagamento-pendente.html" element={<PaymentPage state="pending" />} />
      <Route path="/pagamento-cancelado.html" element={<PaymentPage state="cancelled" />} />
      <Route path="/politica-privacidade.html" element={<PrivacyPage />} />
      <Route path="/termos.html" element={<TermsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </AuthProvider>;
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
