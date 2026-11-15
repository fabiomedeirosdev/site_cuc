import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { EditorialLayout, Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";
import "./communications.css";
import ContentPanel from "./CommunicationsEditor.jsx";
import { eventDate } from "./communications-format.js";

export { eventDate } from "./communications-format.js";

export function HomeEvents() {
  const resource = useResource((signal) => api.getEvents(1, false, { signal }));
  return <section id="agenda" className="mag-events"><div className="mag-section-heading"><h2>Próximos Eventos</h2><SiteLink className="mag-text-link" href="/agenda.html">Ver Agenda →</SiteLink></div><ResourceStatus resource={resource} />{resource.data && (resource.data.results.length ? resource.data.results.slice(0, 3).map((event) => <SiteLink href={`/agenda.html#evento-${event.id}`} className="mag-event" key={event.id}><div className="mag-event-date"><strong>{new Date(event.starts_at).toLocaleDateString("pt-BR", { day: "2-digit", timeZone: "America/Sao_Paulo" })}</strong><span>{new Date(event.starts_at).toLocaleDateString("pt-BR", { month: "short", timeZone: "America/Sao_Paulo" })}</span></div><div><h3>{event.title}{event.is_cancelled ? " · Cancelado" : ""}</h3>{event.is_members_only && <p className="event-audience">Apenas para assinantes</p>}<p>{event.location ? event.location + " · " : ""}{new Date(event.starts_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" })}</p></div></SiteLink>) : <p className="editorial-notice">A programação será exibida assim que a equipe publicar os próximos eventos.</p>)}</section>;
}

export function HomeMural() {
  const resource = useResource((signal) => api.getMural(1, { signal }));
  return <section className="mag-mural"><div className="mag-section-heading"><h2>Mural da Comunidade</h2><SiteLink className="mag-text-link" href="/mural.html">Ver todos os avisos →</SiteLink></div><ResourceStatus resource={resource} />{resource.data && (resource.data.results.length ? <div className="mag-mural-grid">{resource.data.results.slice(0, 3).map((item) => <article key={`${item.kind}-${item.id}`}><span className="mag-kicker">{item.kind === "event" ? "Agenda atualizada" : "Aviso"}</span><h3>{item.title}</h3>{item.image_url && !item.is_locked && <img className="communication-image-preview" src={item.image_url} alt={item.image_alt || ""} loading="lazy" />}<p>{item.kind === "event" ? `${eventDate(item.starts_at)} · ${item.is_cancelled ? "Cancelado" : item.is_members_only ? "Apenas para assinantes" : item.location}` : item.is_locked ? "Aviso exclusivo para assinantes. Entre para consultar os detalhes." : (item.body || "").slice(0, 160)}</p><SiteLink className="mag-text-link" href={item.kind === "event" ? `/agenda.html#evento-${item.id}` : "/mural.html"}>Saiba mais →</SiteLink></article>)}</div> : <p className="editorial-notice">Os avisos da comunidade aparecerão aqui quando forem publicados.</p>)}</section>;
}

function EventCard({ event }) {
  const location = useLocation();
  return <article className={"communications-card " + (event.is_cancelled ? "event-cancelled" : "")} id={"evento-" + event.id}><span className="mag-kicker">{event.is_cancelled ? "Evento cancelado" : "Agenda da comunidade"}</span><h2>{event.title}</h2>{event.is_members_only && <span className="event-audience">Apenas para assinantes</span>}<p><strong>{eventDate(event.starts_at)}</strong>{event.ends_at && <> até {eventDate(event.ends_at)}</>} · horário de Brasília</p>{event.is_locked ? <div className="billing-note"><p>Este encontro é exclusivo para assinantes. Entre com uma assinatura vigente para consultar o local e os detalhes.</p><div className="account-actions"><SiteLink className="mag-button red" href="/login.html" state={{ from: location.pathname }}>Entrar</SiteLink><SiteLink className="mag-button pale" href="/assinatura.html">Conhecer a assinatura</SiteLink></div></div> : <><p>{event.location}</p><p className="communications-text">{event.description}</p></>}</article>;
}

export function AgendaPage() {
  const location = useLocation();
  const [page, setPage] = useState(1);
  const [past, setPast] = useState(false);
  const resource = useResource((signal) => api.getEvents(page, past, { signal }), [page, past]);
  useEffect(() => {
    if (resource.data && /^#evento-\d+$/.test(location.hash)) {
      const target = document.getElementById(location.hash.slice(1));
      if (target) { target.setAttribute("tabindex", "-1"); target.focus({ preventScroll: true }); target.scrollIntoView({ behavior: "instant", block: "start" }); }
    }
  }, [resource.data, location.hash]);
  return <EditorialLayout title="Agenda da Comunidade" intro="Encontros, celebrações e formações para caminharmos juntos."><div className="communications-tabs"><button className="mag-button pale" aria-pressed={!past} onClick={() => { setPast(false); setPage(1); }}>Próximos eventos</button><button className="mag-button pale" aria-pressed={past} onClick={() => { setPast(true); setPage(1); }}>Eventos anteriores</button><SiteLink className="mag-text-link" href="/mural.html">Ver mural →</SiteLink></div><ResourceStatus resource={resource} />{resource.data && <><div className="communications-list">{resource.data.results.map((event) => <EventCard event={event} key={event.id} />)}</div>{!resource.data.count && <p className="editorial-notice">Nenhum evento publicado neste período. Volte em breve para conferir a programação.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</EditorialLayout>;
}

export function MuralPage() {
  const [page, setPage] = useState(1);
  const resource = useResource((signal) => api.getMural(page, { signal }), [page]);
  return <EditorialLayout title="Mural da Comunidade" intro="Avisos e atualizações da agenda, reunidos em um só lugar."><SiteLink className="mag-text-link" href="/agenda.html">Conferir a agenda →</SiteLink><ResourceStatus resource={resource} />{resource.data && <><div className="communications-list">{resource.data.results.map((item) => item.kind === "event" ? <EventCard event={item} key={`event-${item.id}`} /> : <NoticeCard notice={item} key={`notice-${item.id}`} />)}</div>{!resource.data.count && <p className="editorial-notice">Os avisos e eventos aparecerão aqui quando forem publicados pela equipe.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</EditorialLayout>;
}

function NoticeCard({ notice }) {
  const location = useLocation();
  return <article className="communications-card"><span className="mag-kicker">Aviso da comunidade</span><h2>{notice.title}</h2>{notice.is_members_only && <span className="event-audience">Somente assinantes</span>}{notice.is_locked ? <div className="billing-note"><p>Este aviso é exclusivo para assinantes. Entre com uma assinatura vigente para consultar a imagem e os detalhes.</p><div className="account-actions"><SiteLink className="mag-button red" href="/login.html" state={{ from: location.pathname }}>Entrar</SiteLink><SiteLink className="mag-button pale" href="/assinatura.html">Conhecer a assinatura</SiteLink></div></div> : <>{notice.image_url && <img className="communication-image-preview" src={notice.image_url} alt={notice.image_alt || ""} loading="lazy" />}<p className="communications-text">{notice.body}</p></>}</article>;
}

export function NewsletterSignup() {
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  return <div className="newsletter-signup"><form onSubmit={async (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); try { const result = await api.requestNewsletter(data.get("email"), data.get("consent") === "on"); setFeedback(result.detail); } catch (error) { setFeedback(error.message || "Não foi possível solicitar a confirmação. Tente novamente."); } finally { setBusy(false); } }}><div className="newsletter-signup-row"><label className="mag-sr-only" htmlFor="newsletter-email">Seu e-mail</label><input id="newsletter-email" name="email" type="email" placeholder="Seu e-mail" required /><button type="submit" disabled={busy} className="mag-button red">{busy ? "Enviando…" : "Inscrever-se"}</button></div><label className="newsletter-consent"><input type="checkbox" name="consent" required /><span>Quero receber a newsletter semanal. Posso sair a qualquer momento. <SiteLink href="/politica-privacidade.html">Privacidade</SiteLink></span></label></form>{feedback && <p className="mag-newsletter-feedback" role="status">{feedback}</p>}</div>;
}

export function NewsletterPreference({ icon, actions } = {}) {
  const resource = useResource((signal) => api.getNewsletterPreference({ signal }));
  const [optedIn, setOptedIn] = useState(null);
  useEffect(() => { if (resource.data) setOptedIn(resource.data.opted_in); }, [resource.data]);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  return <aside className="account-subscription member-newsletter">{icon}<div><h2>Newsletter semanal</h2><p>Receba a programação e os avisos da comunidade. O recebimento é gratuito e opcional, mesmo sem assinatura.</p><ResourceStatus resource={resource} />{optedIn !== null && <label className="newsletter-consent"><input type="checkbox" checked={optedIn} disabled={busy || resource.status === "loading"} onChange={async (event) => { const value = event.target.checked; setOptedIn(value); setFeedback(""); setBusy(true); try { await api.saveNewsletterPreference(value); setFeedback(value ? "Recebimento autorizado. Você pode desativar quando quiser." : "Recebimento desativado. Sua assinatura continua inalterada."); resource.reload(); } catch (error) { setOptedIn(!value); setFeedback(error.message); } finally { setBusy(false); } }} />Quero receber a newsletter semanal</label>}<p role="status">{feedback}</p></div>{actions && <div className="member-newsletter-actions">{actions}</div>}</aside>;
}

export function NewsletterActionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useState(() => new URLSearchParams(location.hash.slice(1)));
  const action = params.has("sair") ? "unsubscribe" : "confirm";
  const token = params.get("sair") || params.get("confirmar");
  const [feedback, setFeedback] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (location.hash) navigate(location.pathname, { replace: true }); }, []);
  return <EditorialLayout title={action === "unsubscribe" ? "Sair da newsletter" : "Confirmar newsletter"} intro="Controle o recebimento das novidades da comunidade.">{!token ? <p>Abra o link recebido por e-mail ou altere a preferência na sua conta.</p> : !done && <><p>{action === "unsubscribe" ? "Confirme para deixar de receber os boletins. Isso não cancela sua assinatura." : "Confirme que deseja receber a newsletter semanal. Você poderá sair a qualquer momento."}</p><button className="mag-button red" disabled={busy} onClick={async () => { setBusy(true); try { const result = await api.newsletterAction(action, token); setFeedback(result.detail); setDone(true); } catch (error) { setFeedback(error.message); } finally { setBusy(false); } }}>{action === "unsubscribe" ? "Deixar de receber" : "Confirmar recebimento"}</button></>}<p role="status" className="form-feedback">{feedback}</p><SiteLink className="mag-text-link" href="/area-associado.html">Minha conta →</SiteLink></EditorialLayout>;
}

function DelegationPanel() {
  const resource = useResource((signal) => api.getCommunicationDelegation({ signal }));
  const [selected, setSelected] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const rows = resource.data?.delegations?.filter((row) => row.facilitator_id === Number(selected)) || [];
  return <section className="communications-card"><h2>Permissões de agenda e mural</h2><p>Desenvolvedores e fundadores autorizam cada facilitador(a). As permissões permanecem ativas até serem revogadas.</p><ResourceStatus resource={resource} />{resource.data?.can_delegate ? <><label>Facilitador(a)<select value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Selecione</option>{resource.data.candidates.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>{selected && <form key={`${selected}-${JSON.stringify(rows)}`} className="editorial-form" onSubmit={async (event) => { event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); setFeedback(""); try { await api.setCommunicationDelegate({ facilitator: Number(selected), can_edit_agenda: data.has("agenda"), can_edit_mural: data.has("mural") }); setFeedback("Permissões atualizadas."); resource.reload(); } catch (error) { setFeedback(error.message); } finally { setBusy(false); } }}><label className="editorial-checkbox"><input type="checkbox" name="agenda" defaultChecked={rows.some((row) => row.can_edit_agenda)} />Pode editar a agenda</label><label className="editorial-checkbox"><input type="checkbox" name="mural" defaultChecked={rows.some((row) => row.can_edit_mural)} />Pode editar o mural</label><button className="mag-button red" disabled={busy}>Salvar permissões</button></form>}</> : resource.data && <p>As permissões são administradas pelo(a) Desenvolvedor(a) e pelos Fundadores.</p>}<p role="status">{feedback}</p></section>;
}

export function ManageCommunicationsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState(user?.communication_sections?.[0] || "events");
  return <EditorialLayout title="Agenda, Mural e Newsletter" intro="Organize os encontros, publique os avisos e prepare os boletins da comunidade.">{user?.can_manage_communications ? <><div className="communications-tabs">{[["events", "Agenda"], ["notices", "Mural"], ["campaigns", "Newsletter"], ["team", "Equipe"]].filter(([key]) => key === "team" ? user?.can_delegate_communications : user?.communication_sections?.includes(key)).map(([key, label]) => <button className="mag-button pale" key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}</div>{tab === "team" ? <DelegationPanel /> : <ContentPanel kind={tab} key={tab} />}</> : <p className="editorial-notice">Somente a coordenação e o(a) facilitador(a) escolhido(a) podem gerenciar a comunicação da comunidade.</p>}</EditorialLayout>;
}
