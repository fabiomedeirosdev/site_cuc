import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SiteLink from "../components/SiteLink.jsx";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { goldenBible } from "../assets.js";
import { EditorialLayout, Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";
import "./content.css";

export function getYouTubeEmbed(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) return "";
    const parts = url.pathname.split("/").filter(Boolean);
    let id = "";
    if (url.hostname === "youtu.be" && parts.length === 1) id = parts[0];
    if (["youtube.com", "www.youtube.com", "m.youtube.com", "www.youtube-nocookie.com"].includes(url.hostname)) {
      if (url.pathname === "/watch") id = url.searchParams.get("v") || "";
      else if (parts.length === 2 && ["embed", "shorts", "live"].includes(parts[0])) id = parts[1];
    }
    return /^[\w-]{11}$/.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : "";
  } catch { return ""; }
}

export function VideoPlayer({ src, title }) {
  if (!src) return null;
  return <div className="content-video"><iframe src={src} title={`Vídeo: ${title || "Conteúdo da comunidade"}`} allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowFullScreen loading="lazy" referrerPolicy="strict-origin-when-cross-origin" /></div>;
}

export function ArticleBody({ children }) {
  return <div className="content-prose"><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{ a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>, img: ({ alt }) => <em>{alt || "Imagem"} (use a foto de capa para ilustrar o conteúdo)</em> }}>{children || ""}</ReactMarkdown></div>;
}

const dateLabel = (value) => value ? new Date(value).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" }) : "";
export function ContentCard({ article }) {
  return <article className="content-card"><SiteLink href={`/conteudos/${article.id}`}><img src={article.cover_url || goldenBible} alt={article.cover_alt || ""} loading="lazy" /><div><span className="mag-kicker">{article.group_name}{article.has_video ? " · Vídeo" : ""}</span><h2>{article.title}</h2>{article.excerpt && <p>{article.excerpt}</p>}<div className="content-byline"><span>{article.author_name}</span><time dateTime={article.published_at}>{dateLabel(article.published_at)}</time></div>{article.is_locked && <span className="content-badge">Exclusivo</span>}</div></SiteLink></article>;
}

export function ContentCatalogPage() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const resource = useResource((signal) => api.getArticles(page, search, { signal }), [page, search]);
  return <EditorialLayout title="Comunidade Online" intro="Artigos, reflexões e vídeos para fortalecer sua caminhada de fé."><form className="content-search" onSubmit={(event) => { event.preventDefault(); setPage(1); setSearch(query); }}><label htmlFor="content-search">Buscar conteúdos<input id="content-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="O que você deseja ler ou assistir?" /></label><button className="mag-button red">Buscar</button></form><ResourceStatus resource={resource} />{resource.data && <>{resource.data.count ? <div className="content-grid">{resource.data.results.map((article) => <ContentCard key={article.id} article={article} />)}</div> : <p className="editorial-notice">{search ? "Nenhum conteúdo encontrado para esta busca." : "Os primeiros conteúdos da comunidade serão publicados aqui em breve."}</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></>}</EditorialLayout>;
}

export function ContentReadPage() {
  const { id } = useParams();
  const resource = useResource((signal) => api.getArticle(id, { signal }), [id]);
  const article = resource.data;
  useEffect(() => { if (article) document.title = `${article.title} | Comunidade Online Unidos em Cristo`; }, [article?.title]);
  return <EditorialLayout title={article?.title || "Conteúdo da comunidade"}><ResourceStatus resource={resource} />{article && <article className="content-reading"><div className="content-byline"><span>{article.author_profile_url ? <SiteLink href={article.author_profile_url}>{article.author_name}</SiteLink> : article.author_name} · {article.group_name}</span><time dateTime={article.published_at}>{dateLabel(article.published_at)}</time></div>{article.cover_url && <img className="content-reading-cover" src={article.cover_url} alt={article.cover_alt} />}{article.excerpt && <p className="content-lead">{article.excerpt}</p>}{article.is_locked ? <div className="editorial-notice"><h2>Conteúdo exclusivo da Comunidade Online</h2><p>Entre com sua conta com assinatura válida ou assine para acessar este conteúdo.</p><div className="account-actions"><SiteLink className="mag-button red" href="/assinatura.html">Assinar Comunidade Online</SiteLink><SiteLink className="mag-button pale" href="/login.html">Entrar</SiteLink></div></div> : <><ArticleBody>{article.body}</ArticleBody><VideoPlayer src={article.video_embed_url} title={article.title} /></>}<SiteLink className="mag-text-link" href="/comunidade-online.html">← Ver todos os conteúdos</SiteLink></article>}</EditorialLayout>;
}

export function MyContentPage() {
  const { user } = useAuth();
  const managing = user?.can_manage_editorial_groups;
  const [page, setPage] = useState(1);
  const [feedback, setFeedback] = useState("");
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);
  const resource = useResource(async (signal) => {
    const [articles, groups] = await Promise.all([api.getEditorArticles(page, { signal }), api.getAuthorGroups({ signal })]);
    return { articles, groups };
  }, [page]);
  async function remove(id) {
    setBusy(true); setFeedback("");
    try { await api.deleteArticle(id); setDeleting(null); setFeedback("Conteúdo excluído."); if (resource.data.articles.results.length === 1 && page > 1) setPage(page - 1); else resource.reload(); }
    catch (error) { setFeedback(error.message || "Não foi possível excluir o conteúdo."); }
    finally { setBusy(false); }
  }
  return <EditorialLayout title={managing ? "Conteúdos dos Grupos" : "Meus Conteúdos"} intro={managing ? "Revise e gerencie os conteúdos dos facilitadores dos grupos que você coordena." : "Crie artigos e vídeos, prepare rascunhos e acompanhe suas publicações."}><ResourceStatus resource={resource} /><p role="status" className="form-feedback">{feedback}</p>{resource.data && <>{resource.data.groups.length > 0 ? <><SiteLink className="mag-button red" href="/editor/novo">+ Criar conteúdo</SiteLink><div className="content-manage-list">{resource.data.articles.results.map((article) => <article className="content-manage-card" key={article.id}><img src={article.cover_url || goldenBible} alt="" /><div><span className="content-badge">{article.status === "published" ? "Publicado" : "Rascunho"}</span><h2>{article.title}</h2><p>{article.group_name} · {article.author_name}</p><div className="account-actions"><SiteLink className="mag-button pale" href={`/editor/${article.id}`}>Editar</SiteLink>{article.status === "published" && <SiteLink className="mag-text-link" href={`/conteudos/${article.id}`}>Ver publicação</SiteLink>}<button className="content-delete" onClick={() => setDeleting(article.id)}>Excluir</button></div>{deleting === article.id && <div className="editorial-notice"><p>Excluir este conteúdo? Ele será removido da comunidade e da home.</p><div className="account-actions"><button className="mag-button red" disabled={busy} onClick={() => remove(article.id)}>Confirmar exclusão</button><button className="mag-button pale" disabled={busy} onClick={() => setDeleting(null)}>Cancelar</button></div></div>}</div></article>)}</div>{resource.data.articles.count === 0 && <div className="editorial-notice">Ainda não há conteúdos disponíveis para gestão. Comece pelo seu primeiro artigo ou vídeo.</div>}<Pagination data={resource.data.articles} page={page} setPage={setPage} /></> : <p className="editorial-notice">A criação de conteúdo exige um vínculo de facilitador ou coordenador em um grupo ativo.</p>}</>}</EditorialLayout>;
}

const emptyArticle = { title: "", excerpt: "", body: "", group: "", cover: null, cover_url: "", cover_alt: "", video_url: "", audience: "public", status: "draft" };
export function ContentEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const text = useRef(null);
  const [form, setForm] = useState(emptyArticle);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState("");
  const resource = useResource(async (signal) => {
    const [groups, article] = await Promise.all([api.getAuthorGroups({ signal }), id ? api.getEditorArticle(id, { signal }) : Promise.resolve(null)]);
    return { groups, article };
  }, [id]);
  useEffect(() => { if (resource.data) setForm(resource.data.article || { ...emptyArticle, group: resource.data.groups[0]?.id || "" }); }, [resource.data]);
  const update = (field, value) => setForm((old) => ({ ...old, [field]: value }));
  async function upload(event) {
    const file = event.target.files[0]; if (!file) return;
    setFeedback("");
    if (file.size > 5 * 1024 * 1024) { setFeedback("A foto deve ter até 5 MB."); return; }
    setUploading(true);
    try { const cover = await api.uploadCover(file); setForm((old) => ({ ...old, cover: cover.id, cover_url: cover.url })); }
    catch (error) { setFeedback(error.message || "Não foi possível enviar a foto."); }
    finally { setUploading(false); }
  }
  function format(before, after = "") {
    const element = text.current;
    if (!element) return;
    const start = element.selectionStart; const end = element.selectionEnd;
    const value = form.body.slice(0, start) + before + form.body.slice(start, end) + after + form.body.slice(end);
    if (value.length <= 200000) update("body", value);
    requestAnimationFrame(() => { element.focus(); element.setSelectionRange(start + before.length, end + before.length); });
  }
  async function save(event) {
    event.preventDefault(); if (uploading || busy) return;
    const status = event.nativeEvent.submitter?.value || "draft";
    setBusy(true); setFeedback("");
    const fields = ["title", "excerpt", "body", "group", "cover", "cover_alt", "video_url", "audience"];
    const payload = Object.fromEntries(fields.map((field) => [field, form[field]])); payload.status = status;
    try {
      const article = id ? await api.updateArticle(id, payload) : await api.createArticle(payload);
      setForm(article);
      setFeedback(status === "published" ? "Conteúdo publicado. A foto e o título já aparecem na comunidade e na home." : "Rascunho salvo.");
      if (!id) navigate(`/editor/${article.id}`, { replace: true });
    } catch (error) { setFeedback(error.message || "Não foi possível salvar. Seu texto permanece no editor."); }
    finally { setBusy(false); }
  }
  const video = getYouTubeEmbed(form.video_url);
  return <EditorialLayout title={id ? "Editar Conteúdo" : "Criar Conteúdo"} intro="Sua voz, sua experiência e sua fé a serviço da comunidade."><SiteLink className="mag-text-link" href="/meus-conteudos.html">← Meus conteúdos</SiteLink><ResourceStatus resource={resource} />{resource.data && <>{resource.data.groups.length ? <form className="content-editor" onSubmit={save}><div className="content-editor-main"><label>Título<input name="title" value={form.title} onChange={(event) => update("title", event.target.value)} maxLength={200} required placeholder="Dê um título ao seu conteúdo" /></label><label>Resumo<textarea value={form.excerpt} onChange={(event) => update("excerpt", event.target.value)} maxLength={500} rows={3} placeholder="Uma breve apresentação para os leitores" /></label><div className="content-editor-label">Texto do conteúdo <span>{form.body.length.toLocaleString("pt-BR")} / 200.000 caracteres</span></div><div className="content-tabs"><button type="button" aria-pressed={!preview} onClick={() => setPreview(false)}>Escrever</button><button type="button" aria-pressed={preview} onClick={() => setPreview(true)}>Prévia</button></div>{preview ? <div className="content-preview"><ArticleBody>{form.body || "Seu texto aparecerá aqui."}</ArticleBody></div> : <><div className="content-toolbar" aria-label="Formatação do texto">{[["Negrito", "**", "**", "B"], ["Itálico", "*", "*", "I"], ["Subtítulo", "\n## ", "", "H2"], ["Lista", "\n- ", "", "• Lista"], ["Citação", "\n> ", "", "❞"], ["Inserir link", "[", "](https://)", "Link"]].map(([label, before, after, mark]) => <button type="button" key={label} aria-label={label} title={label} onClick={() => format(before, after)}>{mark}</button>)}</div><textarea className="content-body-input" ref={text} aria-label="Texto do conteúdo" value={form.body} onChange={(event) => update("body", event.target.value)} maxLength={200000} placeholder="Escreva com liberdade. Use a barra acima para formatar seu texto." /></>}<label>Link do vídeo do YouTube<input type="url" value={form.video_url} onChange={(event) => update("video_url", event.target.value)} placeholder="https://www.youtube.com/watch?v=..." /></label>{form.video_url && !video && <p className="content-hint">Informe um link HTTPS de vídeo do YouTube para ver a prévia.</p>}<VideoPlayer src={video} title={form.title} /></div><aside className="content-editor-aside"><div className="content-editor-panel"><h2>Foto de capa</h2><p>Ela também será usada para apresentar seu conteúdo na home.</p>{form.cover_url && <img className="content-cover-preview" src={form.cover_url} alt={form.cover_alt || "Prévia da foto de capa"} />}<label>Escolher foto<input type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} disabled={uploading || busy} /></label><small>JPG, PNG ou WebP · até 5 MB</small>{uploading && <p role="status">Enviando foto…</p>}<label>Descrição da foto<input value={form.cover_alt} onChange={(event) => update("cover_alt", event.target.value)} maxLength={200} placeholder="Descreva o que aparece na imagem" /></label></div><div className="content-editor-panel"><h2>Publicação</h2><label>Grupo<select value={form.group} onChange={(event) => update("group", event.target.value)} required>{resource.data.groups.map((group) => <option value={group.id} key={group.id}>{group.name}</option>)}</select></label><label>Visibilidade<select value={form.audience} onChange={(event) => update("audience", event.target.value)}><option value="public">Público</option><option value="members">Exclusivo para assinantes</option></select></label>{form.audience === "members" && <p className="content-hint">O texto e o vídeo serão liberados somente para contas com um período de assinatura pago e válido.</p>}<span className="content-badge">{form.status === "published" ? "Publicado" : "Rascunho"}</span><button className="mag-button pale" type="submit" value="draft" disabled={busy || uploading}>Salvar rascunho</button><button className="mag-button red" type="submit" value="published" disabled={busy || uploading}>{busy ? "Salvando…" : form.status === "published" ? "Salvar alterações" : "Publicar"}</button>{id && form.status === "published" && <SiteLink className="mag-text-link" href={`/conteudos/${id}`}>Ver publicação →</SiteLink>}</div></aside><p className="content-editor-feedback" role="status">{feedback}</p></form> : <p className="editorial-notice">Somente facilitadores e coordenadores vinculados a um grupo ativo podem criar conteúdos.</p>}</>}</EditorialLayout>;
}
