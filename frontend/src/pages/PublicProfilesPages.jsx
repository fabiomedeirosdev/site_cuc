import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Avatar from "../components/Avatar.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { EditorialLayout, Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";
import { VideoPlayer } from "./ContentPages.jsx";
import "./profiles.css";

export function PublicProfilesPage() {
  const { user, ensureSession } = useAuth();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const resource = useResource((signal) => api.getPublicProfiles(page, search, role, { signal }), [page, search, role]);
  return <EditorialLayout title="Membros da Comunidade" intro="Conheça quem caminha com a gente: coordenação, auxiliares, desenvolvedor(a) e assinantes."><div className="profile-directory-top"><p>Histórias que se encontram na fé e na vida em comunidade.</p>{user && <SiteLink className="mag-button red" href="/perfil.html">Editar meu perfil</SiteLink>}</div>
    <form className="profile-directory-search" onSubmit={(event) => { event.preventDefault(); setSearch(query); setPage(1); }}><label>Buscar por nome<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Quem você quer conhecer?" /></label><label>Função na comunidade<select value={role} onChange={(event) => { setRole(event.target.value); setPage(1); }}>{[["", "Todas as pessoas"], ["founder", "Fundador(a)"], ["developer", "Desenvolvedor(a)"], ["coordinator", "Coordenadores"], ["administration", "Administração"], ["priest", "Padre"], ["deacon", "Diácono"], ["auxiliary", "Auxiliares"], ["subscriber", "Assinantes"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><button className="mag-button pale">Buscar</button></form>
    <ResourceStatus resource={resource} />{resource.data && <><div className="profile-directory-grid">{resource.data.results.map((person) => <article className="profile-person-card" key={person.public_id}><div className="profile-card-banner" /><Avatar photo={person.avatar_url} name={person.display_name} className="profile-avatar-large" /><span className={`profile-role role-${person.role}`}>{person.role_label}</span><h2>{person.display_name}</h2><p>{person.biography ? person.biography.slice(0, 160) + (person.biography.length > 160 ? "…" : "") : "Um lugar para partilhar a fé e caminhar em comunidade."}</p><SiteLink className="mag-text-link" href={`/perfis/${person.public_id}`}>Conhecer perfil →</SiteLink></article>)}</div>{!resource.data.count && <p className="editorial-notice">Nenhum perfil encontrado para esta busca.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}
  </EditorialLayout>;
}

export function PublicProfilePage() {
  const { id } = useParams();
  const { user, ensureSession } = useAuth();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const resource = useResource((signal) => api.getPublicProfile(id, { signal }), [id]);
  const person = resource.data;
  useEffect(() => { if (person) document.title = `${person.display_name} | Membros da Comunidade`; }, [person]);
  return <EditorialLayout title="Perfil da comunidade"><SiteLink className="mag-text-link" href="/perfis.html">← Conhecer outras pessoas</SiteLink>{resource.error?.status === 404 ? <p className="editorial-notice" role="alert">Este perfil não está disponível.</p> : <ResourceStatus resource={resource} />}{person && <>
    <section className="public-profile-hero"><div className="public-profile-cover"><span>Fé, formação e vida em comunidade</span></div><div className="public-profile-identity"><Avatar photo={person.avatar_url} name={person.display_name} className="profile-avatar-hero" /><div><span className={`profile-role role-${person.role}`}>{person.role_label}</span><h2>{person.display_name}</h2><p>Comunidade Unidos em Cristo</p></div>{user?.public_id === person.public_id && <SiteLink className="mag-button pale" href="/perfil.html">Editar meu perfil</SiteLink>}</div></section>
    <div className="public-profile-columns"><section className="profile-surface"><span className="mag-kicker">Minha caminhada</span><h2>Sobre mim</h2><p className="profile-biography">{person.biography || "Esta pessoa ainda vai compartilhar sua apresentação com a comunidade."}</p>{person.video_embed_url && <section className="profile-presentation-video"><h2>Minha apresentação</h2><VideoPlayer src={person.video_embed_url} title={`Apresentação de ${person.display_name}`} /></section>}</section><aside className="profile-surface profile-contact"><span className="mag-kicker">Em comunidade</span><h2>Vamos nos conhecer</h2><p>Uma comunidade feita de pessoas, histórias e caminhos que se encontram.</p>{person.website && <a className="mag-button pale" href={person.website} target="_blank" rel="noopener noreferrer">Visitar meu site ↗</a>}{person.phone && <><h3>Telefone de contato</h3><a className="profile-phone" href={`tel:${person.phone.replace(/[^+\d]/g, "")}`}>{person.phone}</a></>}<SiteLink className="mag-text-link" href="/grupos.html">Conhecer os grupos →</SiteLink></aside></div>
  </>}</EditorialLayout>;
}

export function ConfirmEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { ensureSession } = useAuth();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("token") || "");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => { if (location.hash) navigate(location.pathname, { replace: true }); }, []);
  return <EditorialLayout title="Confirmar novo e-mail"><section className="profile-surface profile-confirm-email">{token ? <><p>Confirme para atualizar seu e-mail de acesso à comunidade.</p>{!done && <button className="mag-button red" disabled={busy} onClick={async () => {
    setBusy(true); setFeedback("");
    try { const result = await api.confirmEmailChange(token); setDone(true); setFeedback(result.detail); await ensureSession(true); }
    catch (error) { setFeedback(error.message || "Não foi possível confirmar. Solicite um novo link pelo seu perfil."); } finally { setBusy(false); }
  }}>{busy ? "Confirmando…" : "Confirmar alteração de e-mail"}</button>}<p role="status" className="form-feedback">{feedback}</p></> : <p>Abra o link de confirmação enviado ao novo endereço ou solicite uma nova alteração pelo seu perfil.</p>}<SiteLink className="mag-text-link" href="/perfil.html">Voltar ao meu perfil →</SiteLink></section></EditorialLayout>;
}
