import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import ManagementLayout from "../components/ManagementLayout.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { api } from "../api.js";
import { logo, goldenBible } from "../assets.js";
import { groupCover } from "../group-covers.js";
import { useAuth } from "../auth/AuthContext.jsx";
import TeamManager from "./TeamManager.jsx";
import { ContentCard, VideoPlayer } from "./ContentPages.jsx";
import Avatar from "../components/Avatar.jsx";
import "./groups.css";

export function useResource(loader, dependencies = []) {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    loader(controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data, error: null });
    }).catch((error) => {
      if (!controller.signal.aborted) setState({ status: "error", data: null, error });
    });
    return () => controller.abort();
  }, [...dependencies, version]);
  return { ...state, reload: () => setVersion((value) => value + 1) };
}

export function ResourceStatus({ resource }) {
  if (resource.status === "loading") return <p className="editorial-notice" role="status">Carregando…</p>;
  if (resource.status === "error") return <div className="editorial-notice" role="alert"><p>{resource.error?.status === 404 ? "Este grupo não está disponível." : "Não foi possível carregar os dados. Verifique sua conexão e tente novamente."}</p><button className="mag-button red" onClick={resource.reload}>Tentar novamente</button></div>;
  return null;
}

export function EditorialLayout({ title, intro, children }) {
  const { pathname } = useLocation();
  if (["/gestao-grupos.html", "/meus-conteudos.html", "/gestao-comunicacao.html"].includes(pathname) || pathname.startsWith("/editor/")) return <ManagementLayout title={title} intro={intro}>{children}</ManagementLayout>;
  return <div className="mag-home"><SiteLink className="skip-link" href="#editorial-content">Pular para o conteúdo</SiteLink><header className="mag-header"><div className="mag-container editorial-nav"><SiteLink className="mag-brand" href="/index.html#inicio"><img src={logo} alt="" /><span>Comunidade<br />Unidos em Cristo</span></SiteLink><nav aria-label="Navegação dos grupos"><SiteLink href="/agenda.html">Agenda</SiteLink><SiteLink href="/mural.html">Mural</SiteLink><SiteLink href="/grupos.html">Grupos</SiteLink><SiteLink href="/facilitadores.html">Facilitadores</SiteLink><SiteLink href="/perfis.html">Membros da Comunidade</SiteLink><SiteLink href="/area-associado.html">Minha conta</SiteLink></nav></div></header><main id="editorial-content" className="mag-container editorial-page" tabIndex={-1}><SiteLink className="mag-text-link" href="/index.html#inicio">← Voltar ao início</SiteLink><div className="editorial-heading"><span className="mag-kicker">Fé, formação e comunhão</span><h1>{title}</h1>{intro && <p>{intro}</p>}</div>{children}</main><footer className="editorial-footer">Comunidade Unidos em Cristo · Acolher, restaurar e transformar vidas.</footer></div>;
}

export function Pagination({ data, page, setPage }) {
  if (!data?.previous && !data?.next) return null;
  return <nav className="editorial-pagination" aria-label="Páginas do catálogo"><button className="mag-button pale" disabled={!data.previous} onClick={() => setPage(page - 1)}>Anterior</button><span>Página {page}</span><button className="mag-button pale" disabled={!data.next} onClick={() => setPage(page + 1)}>Próxima</button></nav>;
}

export function GroupsPage() {
  const { user, ensureSession } = useAuth();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const [page, setPage] = useState(1);
  const resource = useResource((signal) => api.getGroups(page, { signal }), [page]);
  return <EditorialLayout title="Nossos Grupos" intro="Conheça os trabalhos da comunidade e encontre um caminho de formação, acolhimento e serviço."><>{user?.can_create_groups && <div className="account-actions management-group-actions"><SiteLink className="mag-button red" href="/painel/grupos/novo">+ Criar novo grupo</SiteLink><SiteLink className="mag-button pale" href="/painel/grupos">Editar grupos e fotos</SiteLink></div>}</><ResourceStatus resource={resource} />{resource.data && <><div className="editorial-catalog">{resource.data.results.map((group) => <article className="editorial-group-card" key={group.slug}><img src={groupCover(group)} alt={group.cover_alt || ""} /><div><h2>{group.name}</h2><p>{group.description}</p><SiteLink className="mag-button red" href={`/grupos/${group.slug}`}>Conheça o grupo →</SiteLink></div></article>)}</div>{resource.data.count === 0 && <p className="editorial-notice">Os grupos serão apresentados aqui assim que forem disponibilizados.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</EditorialLayout>;
}

const roleLabels = { coordinator: "Coordenador", columnist: "Facilitador" };
function TeamCard({ member }) {
  return <article className="editorial-team-card"><Avatar photo={member.avatar_url} name={member.display_name} /><div><span className="mag-kicker">{roleLabels[member.role]}</span><h3>{member.profile_url ? <SiteLink href={member.profile_url}>{member.display_name}</SiteLink> : member.display_name}</h3>{member.biography && <p>{member.biography}</p>}{member.group_name && <SiteLink className="mag-text-link" href={`/grupos/${member.group_slug}`}>{member.group_name} →</SiteLink>}</div></article>;
}

export function GroupDetailPage() {
  const { slug } = useParams();
  const resource = useResource((signal) => api.getGroup(slug, { signal }), [slug]);
  const group = resource.data;
  const { user, ensureSession } = useAuth();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const [page, setPage] = useState(1);
  useEffect(() => { setPage(1); }, [slug]);
  const articles = useResource((signal) => api.getGroupArticles(slug, page, { signal }), [slug, page, user?.id, user?.exclusive_content_access]);
  return <EditorialLayout title={group?.name || "Grupo da comunidade"}><ResourceStatus resource={resource} />{group && <><section className="editorial-group-detail"><img src={groupCover(group)} alt={group.cover_alt || ""} /><div><h2>Conheça nosso trabalho</h2><p>{group.description}</p>{group.address && <p>{group.address}</p>}<VideoPlayer src={group.video_embed_url} title={group.name} /><a className="mag-button red" href={`https://wa.me/${group.whatsapp || "5511986302883"}`} target="_blank" rel="noopener noreferrer">Saiba como participar →</a></div></section><section className="editorial-team"><h2>Quem caminha com este grupo</h2>{group.team.length ? <div className="editorial-team-grid">{group.team.map((member, index) => <TeamCard key={index} member={member} />)}</div> : <p className="editorial-notice">A equipe será apresentada aqui em breve.</p>}</section><section className="editorial-team"><h2>Publicações do grupo</h2><ResourceStatus resource={articles} />{articles.data && <>{articles.data.results.length ? <div className="content-grid">{articles.data.results.map((article) => <ContentCard key={article.id} article={article} />)}</div> : <p className="editorial-notice">Ainda não há publicações disponíveis.</p>}<Pagination data={articles.data} page={page} setPage={setPage} /></>}</section><SiteLink className="mag-text-link" href="/grupos.html">← Ver todos os grupos</SiteLink></>}</EditorialLayout>;
}

export function ColumnistsPage() {
  const [page, setPage] = useState(1);
  const resource = useResource((signal) => api.getColumnists(page, { signal }), [page]);
  return <EditorialLayout title="Facilitadores" intro="Conheça as pessoas que partilham formação e espiritualidade nos grupos da comunidade."><ResourceStatus resource={resource} />{resource.data && <>{resource.data.count ? <div className="editorial-team-grid">{resource.data.results.map((member, index) => <TeamCard member={member} key={index} />)}</div> : <p className="editorial-notice">Os facilitadores serão apresentados aqui assim que seus perfis forem disponibilizados.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</EditorialLayout>;
}

function MemberEditor({ member, slug, isAdmin, onSaved }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const editable = isAdmin || member.role === "columnist";
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api.updateGroupMember(slug, member.id, { biography: form.get("biography"), is_public: form.get("is_public") === "on", ...(isAdmin ? { role: form.get("role") } : {}) });
      onSaved("Vínculo atualizado.");
    } catch (failure) { setError(failure.message || "Não foi possível salvar."); }
    finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setError("");
    try { await api.removeGroupMember(slug, member.id); onSaved("Vínculo removido. A conta foi preservada."); }
    catch (failure) { setError(failure.message || "Não foi possível remover o vínculo."); }
    finally { setBusy(false); }
  }
  return <article className="editorial-member"><h3>{member.display_name}</h3><p>{roleLabels[member.role]}</p>{editable && <details><summary>Editar vínculo</summary><form onSubmit={submit} className="editorial-form">{isAdmin && <label>Função<select name="role" defaultValue={member.role}><option value="columnist">Facilitador</option><option value="coordinator">Coordenador</option></select></label>}<label>Apresentação<textarea name="biography" maxLength={2000} defaultValue={member.biography} /></label><label className="editorial-checkbox"><input name="is_public" type="checkbox" defaultChecked={member.is_public} />Exibir nome e apresentação na página pública</label><div className="account-actions"><button className="mag-button red" disabled={busy}>Salvar vínculo</button><button className="mag-button pale" type="button" disabled={busy} onClick={() => setConfirmRemove(true)}>Remover vínculo</button></div></form>{confirmRemove && <div className="editorial-notice"><p>Remover este vínculo do grupo? A conta continuará existindo.</p><div className="account-actions"><button className="mag-button red" disabled={busy} onClick={remove}>Confirmar remoção</button><button className="mag-button pale" disabled={busy} onClick={() => setConfirmRemove(false)}>Cancelar</button></div></div>}</details>}<p role="alert" className="form-feedback">{error}</p></article>;
}

function GroupMembershipManager({ slug, isAdmin }) {
  const resource = useResource((signal) => api.getGroupMembers(slug, { signal }), [slug]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createAccount, setCreateAccount] = useState(false);
  const [message, setMessage] = useState("");
  const saved = (text) => { setMessage(text); resource.reload(); };
  async function add(event) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    setBusy(true); setError(""); setMessage("");
    try { await api.addGroupMember(slug, { email: data.get("email"), role: isAdmin ? data.get("role") : "columnist", ...(createAccount ? { create_account: true, display_name: data.get("display_name"), password: data.get("password") } : {}) }); form.reset(); saved("Vínculo adicionado. O perfil permanece privado até você habilitar sua exibição."); }
    catch (failure) { setError(failure.message || "Não foi possível adicionar o vínculo."); }
    finally { setBusy(false); }
  }
  return <><ResourceStatus resource={resource} /><p role="status" className="form-feedback">{message}</p>{resource.data && <><section className="editorial-management-box"><h2>Adicionar {isAdmin ? "integrante" : "facilitador"}</h2><label className="editorial-checkbox"><input type="checkbox" checked={createAccount} onChange={(event) => setCreateAccount(event.target.checked)} /> Criar acesso para um novo facilitador</label><p>{createAccount ? "Cadastre o nome, o e-mail e uma senha inicial para o novo facilitador." : "Informe o e-mail de uma conta ativa já cadastrada na comunidade."}</p><form className="editorial-form editorial-add-form" onSubmit={add}>{createAccount && <><label>Nome do facilitador<input name="display_name" maxLength={150} required /></label><label>Senha inicial<input name="password" type="password" minLength={8} maxLength={1024} autoComplete="new-password" required /></label></>}<label>E-mail da conta<input name="email" type="email" required autoComplete="off" maxLength={254} /></label>{isAdmin && <label>Função<select name="role"><option value="columnist">Facilitador</option><option value="coordinator">Coordenador</option></select></label>}<button className="mag-button red" disabled={busy}>{busy ? "Adicionando…" : "Adicionar vínculo"}</button></form><p className="form-feedback" role="alert">{error}</p></section><section className="editorial-members"><h2>Integrantes do grupo</h2>{resource.data.length ? resource.data.map((member) => <MemberEditor key={`${member.id}-${member.biography}-${member.is_public}-${member.role}`} member={member} slug={slug} isAdmin={isAdmin} onSaved={saved} />) : <p className="editorial-notice">Este grupo ainda não possui integrantes vinculados.</p>}</section></>}</>;
}

export function ManageGroupsPage() {
  const { user } = useAuth();
  const resource = useResource((signal) => api.getManagedGroups({ signal }));
  const [selected, setSelected] = useState("");
  const groups = resource.data?.groups || [];
  const slug = groups.some((group) => group.slug === selected) ? selected : groups[0]?.slug;
  return <EditorialLayout title="Equipes e permissões" intro="Organize a equipe e as apresentações públicas dos grupos que você coordena."><ResourceStatus resource={resource} />{resource.data && <>{resource.data.is_administrator && <TeamManager groups={groups} />}{groups.length ? <><label className="editorial-group-select">Grupo<select value={slug} onChange={(event) => setSelected(event.target.value)}>{groups.map((group) => <option key={group.slug} value={group.slug}>{group.name}{group.is_active ? "" : " (inativo)"}</option>)}</select></label><GroupMembershipManager key={slug} slug={slug} isAdmin={resource.data.is_administrator} /></> : <p className="editorial-notice">Nenhum grupo disponível para gestão. A administração precisa atribuir a você a coordenação de um grupo ativo.</p>}</>}<SiteLink className="mag-text-link" href="/area-associado.html">← Voltar à minha conta</SiteLink></EditorialLayout>;
}
