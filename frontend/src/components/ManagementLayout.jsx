import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import SiteLink from "./SiteLink.jsx";
import { logo } from "../assets.js";
import NotificationBell from "./NotificationBell.jsx";
import Avatar from "./Avatar.jsx";
import "../pages/management.css";

export default function ManagementLayout({ title, intro, children }) {
  const { user } = useAuth();
  const administrator = user?.roles?.includes("administrator");
  const allowed = user?.can_access_panel || user?.can_handle_inbox || administrator;
  const links = [["/painel", "◈", "Visão geral"], ["/perfil.html", "◎", "Meu perfil"]];
  if (user?.capabilities?.create_content) links.push(["/meus-conteudos.html", "▤", "Conteúdos"], ["/editor/novo", "+", "Criar publicação"]);
  if (user?.can_manage_editorial_groups) links.push(["/painel/destaques", "✦", "Destaques do site"], ["/gestao-grupos.html", "♧", "Equipes e permissões"], ["/painel/grupos", "▦", "Páginas dos grupos"]);
  if (user?.can_manage_communications) links.push(["/gestao-comunicacao.html", "◷", "Agenda, mural e newsletter"]);
  if (user?.can_handle_inbox) links.push(["/painel/mensagens", "✉", "Mensagens recebidas"]);
  if (!user?.can_access_panel && !administrator) links.shift();
  if (administrator) links.push(["/painel/fundadores", "✧", "Fundadores"], ["/painel/usuarios", "◎", "Usuários"], ["/painel/assinaturas", "▣", "Assinaturas"], ["/painel/atendimentos", "✉", "Atendimentos"]);
  return <div className="mag-home management-app"><SiteLink className="skip-link" href="#management-main">Pular para o conteúdo</SiteLink><header className="mag-header"><div className="management-topbar"><SiteLink href="/index.html" className="mag-brand"><img src={logo} alt="" /><span>Comunidade<br />Unidos em Cristo</span></SiteLink><span className="management-label">Administração da comunidade</span><NotificationBell /><SiteLink className="management-view-site" href="/index.html">Ver o site ↗</SiteLink></div></header><div className="management-workspace"><aside className="management-sidebar"><div className="management-profile"><Avatar photo={user?.avatar_url} name={user?.display_name} /><div><strong>{user?.display_name || "Equipe CUC"}</strong><small>{user?.profile_role_label || (administrator ? "Desenvolvedor(a)" : user?.can_manage_editorial_groups ? "Coordenador(a)" : "Auxiliar")}</small></div></div>{allowed && <nav aria-label="Administração">{links.map(([to, icon, label]) => <NavLink key={to} to={to} end className={({ isActive }) => isActive ? "is-active" : ""}><span aria-hidden="true">{icon}</span>{label}</NavLink>)}</nav>}<SiteLink className="management-account" href="/area-associado.html">Minha conta e sair →</SiteLink><p className="management-motto">Acolher, restaurar<br />e transformar vidas.</p></aside><main className="management-main" id="management-main" tabIndex={-1}><div className="management-heading"><span className="mag-kicker">Comunidade Unidos em Cristo · Gestão</span><h1>{allowed ? title : "Acesso restrito"}</h1>{allowed && intro && <p>{intro}</p>}</div>{allowed ? children : <p className="editorial-notice" role="alert">Seu perfil não tem permissão para acessar a administração.</p>}<footer className="management-footer">Comunidade Unidos em Cristo · Painel de administração</footer></main></div></div>;
}
