import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import GroupForm from "../components/GroupForm.jsx";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import ManagementLayout from "../components/ManagementLayout.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { goldenBible } from "../assets.js";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";

const date = (value) => value ? new Date(value).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" }) : "—";
const number = (value) => Number(value).toLocaleString("pt-BR");

export function DashboardPage() {
  const resource = useResource((signal) => api.getDashboard({ signal }));
  const { user } = useAuth();
  const data = resource.data;
  const labels = { contents: "Conteúdos", published: "Publicados", drafts: "Rascunhos", featured: "Em destaque", groups: "Grupos sob gestão", users: "Usuários cadastrados", subscriptions: "Contas com período pago válido", requests: "Atendimentos pendentes", events: "Próximos eventos", notices: "Avisos publicados", campaigns: "Campanhas de newsletter" };
  const highest = Math.max(1, ...(data?.activity || []).map((item) => item.total));
  return <ManagementLayout title="Visão geral" intro="Cuide da comunidade, acompanhe as publicações e mantenha o site atualizado."><ResourceStatus resource={resource} />{data && <><div className="management-section-title"><p>{data.scope} · Dados atualizados a cada consulta</p><button className="mag-button pale" onClick={resource.reload}>Atualizar dados</button></div><div className="management-stats">{Object.entries(data.totals).map(([key, value]) => <article className={`management-stat stat-${key}`} key={key}><span>{labels[key]}</span><strong>{number(value)}</strong></article>)}</div><div className="management-dashboard-grid"><section className="management-card"><span className="mag-kicker">Atividade editorial</span><h2>Publicações nos últimos 6 meses</h2><p>Quantidade de conteúdos publicados por mês na sua área de gestão.</p><div className="management-chart" role="img" aria-label={data.activity.map((item) => `${item.month}: ${item.total} publicações`).join("; ")}>{data.activity.map((item) => <div key={item.month}><strong>{item.total}</strong><div className="management-chart-track"><span style={{ height: `${item.total / highest * 100}%` }} /></div><small>{item.month}</small></div>)}</div></section><section className="management-card"><span className="mag-kicker">Seu próximo passo</span><h2>Cuide do que a comunidade vê</h2><p>Prepare uma publicação, organize a equipe e escolha os conteúdos da página inicial.</p><div className="management-quick-links">{user.capabilities?.create_content && <SiteLink href="/editor/novo">Criar publicação <span>＋</span></SiteLink>}{user.can_manage_editorial_groups && <><SiteLink href="/painel/destaques">Escolher destaques <span>✦</span></SiteLink><SiteLink href="/gestao-grupos.html">Gerenciar equipe <span>→</span></SiteLink></>}{user.can_manage_communications && <SiteLink href="/gestao-comunicacao.html">Atualizar agenda e mural <span>→</span></SiteLink>}</div></section></div><section className="management-card"><div className="management-section-title"><h2>Conteúdos atualizados recentemente</h2><SiteLink className="mag-text-link" href="/meus-conteudos.html">Ver conteúdos →</SiteLink></div><div className="management-table-scroll"><table className="management-table"><thead><tr><th>Publicação</th><th>Grupo</th><th>Situação</th><th>Atualização</th><th>Ação</th></tr></thead><tbody>{data.recent.map((article) => <tr key={article.id}><td><strong>{article.title}</strong><small>{article.author_name}</small></td><td>{article.group_name}</td><td><span className={`management-badge ${article.status}`}>{article.status === "published" ? "Publicado" : "Rascunho"}</span></td><td>{date(article.updated_at)}</td><td><SiteLink className="mag-text-link" href={`/editor/${article.id}`}>Editar →</SiteLink></td></tr>)}</tbody></table></div>{!data.recent.length && <p className="management-empty">As publicações da sua equipe aparecerão aqui.</p>}</section></>}</ManagementLayout>;
}

function HighlightCard({ article, onSaved, setFeedback }) {
  const [featured, setFeatured] = useState(article.is_featured);
  const [position, setPosition] = useState(article.featured_position);
  const [busy, setBusy] = useState(false);
  async function save(event) {
    event.preventDefault(); setBusy(true); setFeedback("");
    try { await api.updateHighlight(article.id, { is_featured: featured, featured_position: Number(position) }); setFeedback(`Destaque de “${article.title}” atualizado na página inicial.`); onSaved(); }
    catch (error) { setFeedback(error.message || "Não foi possível salvar o destaque."); }
    finally { setBusy(false); }
  }
  return <article className="management-highlight"><img src={article.cover_url || goldenBible} alt={article.cover_alt || ""} /><div><span className="mag-kicker">{article.group_name}</span><h2>{article.title}</h2><p>{article.author_name} · {article.status === "published" ? "Publicado" : "Rascunho"}</p><form onSubmit={save}><label className="management-check"><input type="checkbox" checked={featured} disabled={busy || (article.status !== "published" && !article.is_featured)} onChange={(event) => setFeatured(event.target.checked)} />Exibir em destaque na página inicial</label><label>Ordem no carrossel<input type="number" min="0" max="32767" required value={position} disabled={busy} onChange={(event) => setPosition(event.target.value)} /></label><p className="management-hint">Os menores números aparecem primeiro. Apenas conteúdos publicados e autorizados ficam visíveis.</p><div className="account-actions"><button className="mag-button red" disabled={busy}>{busy ? "Salvando…" : "Salvar destaque"}</button><SiteLink className="mag-text-link" href={`/editor/${article.id}`}>Editar conteúdo →</SiteLink></div></form></div></article>;
}

export function HighlightsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [feedback, setFeedback] = useState("");
  const resource = useResource((signal) => api.getHighlightCandidates(page, { signal }), [page]);
  return <ManagementLayout title="Destaques do site" intro="Escolha as publicações que recebem destaque e defina a ordem em que aparecem na página inicial.">{user.can_manage_editorial_groups ? <><div className="management-guidance"><span aria-hidden="true">✦</span><p>Você pode selecionar conteúdos dos grupos que coordena. A administração pode selecionar conteúdos de todos os grupos. Conteúdos exclusivos continuam exigindo assinatura para leitura.</p><SiteLink className="mag-button pale" href="/index.html#inicio">Ver página inicial ↗</SiteLink></div><p role="status" className="form-feedback">{feedback}</p><ResourceStatus resource={resource} />{resource.data && <><div className="management-highlights">{resource.data.results.map((article) => <HighlightCard article={article} key={`${article.id}-${article.updated_at}`} onSaved={resource.reload} setFeedback={setFeedback} />)}</div>{!resource.data.results.length && <p className="management-empty">Nenhum conteúdo dos seus grupos disponível. Comece criando uma publicação.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</> : <p role="alert">Somente administradores e coordenadores podem selecionar destaques.</p>}</ManagementLayout>;
}

export function GroupSettingsPage() {
  const { user } = useAuth();
  const { state } = useLocation();
  const resource = useResource((signal) => api.getGroupSettings({ signal }));
  return <ManagementLayout title="Páginas dos grupos" intro="Crie grupos e atualize suas apresentações e capas com a identidade da comunidade.">{(user.can_create_groups || user.can_manage_editorial_groups || user.roles.includes("administrator")) && <div className="management-section-title"><SiteLink className="mag-button red" href="/painel/grupos/novo">+ Criar novo grupo</SiteLink><SiteLink className="mag-text-link" href="/gestao-grupos.html">Gerenciar equipes →</SiteLink></div>}{state?.createdGroup && <p role="status" className="editorial-notice">Grupo “{state.createdGroup}” criado. A página já está disponível conforme a visibilidade escolhida.</p>}<ResourceStatus resource={resource} /><div className="management-settings-grid">{resource.data?.map((group) => <GroupForm group={group} key={group.id} administrator={user.roles.includes("administrator")} />)}</div>{resource.data?.length === 0 && <p className="management-empty">Não há grupos disponíveis para gestão.</p>}</ManagementLayout>;
}

export function NewGroupPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const allowed = user.can_create_groups || user.can_manage_editorial_groups || user.roles.includes("administrator");
  return <ManagementLayout title="Criar novo grupo" intro="Apresente um novo caminho de formação, oração e serviço para a comunidade.">{allowed ? <div className="management-new-group"><GroupForm administrator={user.roles.includes("administrator")} onSaved={(group) => navigate("/painel/grupos", { replace: true, state: { createdGroup: group.name } })} /></div> : <p role="alert">Somente administradores e coordenadores podem criar grupos.</p>}</ManagementLayout>;
}

export function AdministrationTablePage({ section }) {
  const { user } = useAuth();
  const administrator = user.roles.includes("administrator");
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState(null);
  const resource = useResource((signal) => administrator ? section === "users" ? api.getManagementUsers(page, search, { signal }) : section === "subscriptions" ? api.getManagementSubscriptions(page, { signal }) : api.getManagementRequests(page, { signal }) : Promise.resolve(null), [section, page, search, administrator]);
  async function act(row) {
    setBusy(true); setFeedback("");
    try { if (section === "users") await api.updateUserAccess(row.id, !row.is_active); else await api.resolveManagementRequest(row.id); setFeedback(section === "users" ? "Acesso atualizado." : "Atendimento marcado como concluído."); setConfirmation(null); resource.reload(); }
    catch (error) { setFeedback(error.message); }
    finally { setBusy(false); }
  }
  const titles = { users: "Usuários", subscriptions: "Assinaturas", requests: "Atendimentos" };
  return <ManagementLayout title={titles[section]} intro={section === "users" ? "Consulte os cadastros e controle o acesso à comunidade." : section === "subscriptions" ? "Acompanhe a situação e a validade dos períodos de assinatura." : "Acompanhe solicitações e registre a conclusão do atendimento."}>{administrator ? <>{section === "users" && <form className="content-search" onSubmit={(event) => { event.preventDefault(); setSearch(query); setPage(1); }}><label>Buscar por nome ou e-mail<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="mag-button red">Buscar</button></form>}{section === "subscriptions" && <p className="management-guidance">Os períodos pagos são atualizados pela confirmação do provedor de pagamento.</p>}{section === "requests" && <p className="management-guidance">Marque como concluído após atender à solicitação. Este registro não executa reembolsos nem exclusões de dados.</p>}<p role="status" className="form-feedback">{feedback}</p>{confirmation && <div className="management-card" role="alert"><p>{section === "users" ? `${confirmation.is_active ? "Suspender" : "Reativar"} o acesso de ${confirmation.email}?` : `Concluir o atendimento de ${confirmation.email}?`}</p><div className="account-actions"><button className="mag-button red" disabled={busy} onClick={() => act(confirmation)}>{busy ? "Salvando…" : "Confirmar"}</button><button className="mag-button pale" disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</button></div></div>}<ResourceStatus resource={resource} />{resource.data && <section className="management-card"><p>{number(resource.data.count)} registros</p><div className="management-table-scroll"><table className="management-table"><thead><tr>{(section === "users" ? ["Pessoa", "E-mail", "Acesso", "Cadastro", "Controle"] : section === "subscriptions" ? ["E-mail", "Situação no provedor", "Período pago até", "Cancelamento solicitado", "Verificação"] : ["E-mail", "Solicitação", "Mensagem", "Recebido em", "Atendimento"]).map((label) => <th key={label}>{label}</th>)}</tr></thead><tbody>{resource.data.results.map((row) => <tr key={row.id}>{section === "users" ? <><td><strong>{row.name}</strong>{row.is_administrator && <small>Desenvolvedor(a)</small>}</td><td>{row.email}</td><td><span className={`management-badge ${row.is_active ? "published" : "draft"}`}>{row.is_active ? "Ativo" : "Suspenso"}</span></td><td>{date(row.joined_at)}</td><td>{!row.access_protected && <button className="management-text-button" disabled={busy} onClick={() => setConfirmation(row)}>{row.is_active ? "Suspender acesso" : "Reativar acesso"}</button>}</td></> : section === "subscriptions" ? <><td>{row.email}</td><td>{row.status}</td><td>{date(row.paid_until)}</td><td>{date(row.cancel_requested_at)}</td><td>{row.safety_hold ? "Em verificação" : "Sem bloqueio"}</td></> : <><td>{row.email}</td><td>{row.kind}</td><td className="management-message">{row.message || "Sem mensagem"}</td><td>{date(row.created_at)}</td><td>{row.resolved_at ? `Concluído em ${date(row.resolved_at)}` : <button className="management-text-button" disabled={busy} onClick={() => setConfirmation(row)}>Concluir atendimento</button>}</td></>}</tr>)}</tbody></table></div>{!resource.data.results.length && <p className="management-empty">Nenhum registro encontrado.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></section>}</> : <p role="alert">Esta página é exclusiva da administração.</p>}</ManagementLayout>;
}
