import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { api } from "../api.js";
import { foundersPhoto } from "../assets.js";
import SiteLink from "../components/SiteLink.jsx";
import ManagementLayout from "../components/ManagementLayout.jsx";
import { EditorialLayout, ResourceStatus, useResource } from "./GroupsPages.jsx";
import "./founders.css";

export function FoundersPage() {
  const { user, ensureSession } = useAuth();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const resource = useResource((signal) => api.getFounders({ signal }));
  const page = resource.data;
  useEffect(() => { if (page) document.title = `${page.title} | Comunidade Unidos em Cristo`; }, [page]);
  return <EditorialLayout title={page?.title || "Nossos fundadores"} intro="Na origem da nossa caminhada, a fé, o acolhimento e o serviço.">
    {user?.roles?.includes("administrator") && <p className="founders-edit-link"><SiteLink className="mag-button pale" href="/painel/fundadores">Editar página dos fundadores</SiteLink></p>}
    <ResourceStatus resource={resource} />{page && <article className="founders-layout"><figure className="founders-portrait"><img src={page.photo_url || foundersPhoto} alt={page.photo_alt} /><figcaption>Comunidade Unidos em Cristo</figcaption></figure><div className="founders-history"><span className="mag-kicker">Uma história de fé e missão</span><div className="founders-story">{page.body}</div><SiteLink className="mag-text-link" href="/perfis.html">Conheça as pessoas da comunidade →</SiteLink></div></article>}
  </EditorialLayout>;
}

export function ManageFoundersPage() {
  const { user } = useAuth();
  const administrator = user?.roles?.includes("administrator");
  const resource = useResource((signal) => administrator ? api.getManagedFounders({ signal }) : Promise.resolve(null), [administrator]);
  const [form, setForm] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  useEffect(() => { if (resource.data) setForm(resource.data); }, [resource.data]);
  useEffect(() => {
    if (!file) { setPreview(""); if (input.current) input.current.value = ""; return; }
    const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url);
  }, [file]);
  const field = (name, value) => setForm((current) => ({ ...current, [name]: value }));
  async function save(event) {
    event.preventDefault(); setBusy(true); setFeedback(""); setError(false);
    const data = new FormData();
    for (const key of ["title", "body", "photo_alt"]) data.append(key, form[key]);
    if (file) data.append("photo", file);
    try { const saved = await api.saveFounders(data); setForm(saved); setFile(null); setFeedback("Página dos fundadores salva e publicada."); }
    catch (failure) { setError(true); setFeedback(failure.message || "Não foi possível salvar. Seu texto permanece no formulário."); }
    finally { setBusy(false); }
  }
  return <ManagementLayout title="Fundadores" intro="Cuide da foto e da história dos fundadores na página institucional da comunidade.">{administrator ? <><ResourceStatus resource={resource} />{form && <form className="management-card management-form founders-editor" onSubmit={save}>
    <div className="management-section-title"><p>As alterações ficam visíveis para todos após salvar e publicar.</p><SiteLink className="mag-text-link" href="/fundadores.html">Ver página pública ↗</SiteLink></div>
    <fieldset disabled={busy} className="founders-editor-fields"><legend className="mag-sr-only">Editar página dos fundadores</legend>
      <label>Título da página<input required maxLength={200} value={form.title} onChange={(event) => field("title", event.target.value)} /></label>
      <div className="founders-editor-columns"><section><h2>Foto dos fundadores</h2><img className="founders-photo-preview" src={preview || form.photo_url || foundersPhoto} alt={form.photo_alt || "Prévia da foto dos fundadores"} /><label>Escolher foto dos fundadores<input ref={input} type="file" accept="image/jpeg,image/png,image/webp" aria-describedby="founders-photo-help" onChange={(event) => {
        const selected = event.target.files[0]; if (!selected) return;
        setFeedback(""); setError(false);
        if (selected.size > 5 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(selected.type)) { setError(true); setFeedback("Escolha uma foto JPG, PNG ou WebP de até 5 MB."); event.target.value = ""; return; }
        setFile(selected);
      }} /></label><p id="founders-photo-help" className="management-hint">JPG, PNG ou WebP · até 5 MB. Recomendado: 1200 × 800 px. Mínimo: 600 × 300 px. Máximo: 4096 × 4096 px. A proporção da foto é preservada, sem recorte. Envie uma nova foto quando quiser substituí-la.</p><label>Descrição da foto<input required maxLength={200} value={form.photo_alt} onChange={(event) => field("photo_alt", event.target.value)} /></label></section>
      <section><label>História dos fundadores<textarea required maxLength={50000} rows={20} value={form.body} onChange={(event) => field("body", event.target.value)} /></label><p className="management-hint">Conte a história dos fundadores e sua caminhada com a comunidade. Separe os parágrafos com uma linha em branco.</p></section></div>
      <button className="mag-button red" disabled={busy}>{busy ? "Salvando…" : "Salvar e publicar"}</button>
    </fieldset><p className="form-feedback" role={error ? "alert" : "status"}>{feedback}</p>
  </form>}</> : <p className="editorial-notice" role="alert">Somente o desenvolvedor pode editar a página dos fundadores.</p>}</ManagementLayout>;
}
