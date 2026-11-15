import { useEffect, useId, useState } from "react";
import { api } from "../api.js";
import { groupCover } from "../group-covers.js";
import SiteLink from "./SiteLink.jsx";

const emptyGroup = { name: "", description: "", cover: "bible", cover_url: null, cover_alt: "", is_active: true, position: 0 };

export default function GroupForm({ group, administrator, onSaved }) {
  const [form, setForm] = useState(group || emptyGroup);
  const [file, setFile] = useState(null);
  const [localPreview, setLocalPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const id = useId();
  useEffect(() => {
    if (!file) { setLocalPreview(""); return; }
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const update = (field, value) => setForm((previous) => ({ ...previous, [field]: value }));
  const preview = localPreview || (group ? groupCover(form) : null);
  function chooseFile(event) {
    const selected = event.target.files[0];
    setFeedback("");
    if (!selected) return;
    if (selected.size > 5 * 1024 * 1024) { setFeedback("A foto deve ter até 5 MB."); event.target.value = ""; return; }
    if (!["image/jpeg", "image/png", "image/webp"].includes(selected.type)) { setFeedback("Escolha uma imagem JPG, PNG ou WebP."); event.target.value = ""; return; }
    setFile(selected);
  }
  async function save(event) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setFeedback("");
    const payload = new FormData();
    for (const key of ["name", "description", "address", "whatsapp", "video_url"]) payload.append(key, form[key] || "");
    if (administrator) { payload.append("is_active", String(form.is_active)); payload.append("position", String(form.position)); }
    if (!group && !file) { setFeedback("Escolha a foto que deseja enviar."); setBusy(false); return; }
    if (file) payload.append("custom_cover", file);
    payload.append("cover_alt", form.cover_alt);
    try {
      const saved = group ? await api.updateGroupSettings(group.id, payload) : await api.createGroup(payload);
      setForm(saved); setFile(null);
      setFeedback(group ? `Página de “${saved.name}” atualizada.` : `Grupo “${saved.name}” criado.`);
      onSaved?.(saved);
    } catch (error) { setFeedback(error.message || "Não foi possível salvar o grupo. Confira os campos e tente novamente."); }
    finally { setBusy(false); }
  }
  return <form className="management-card management-form management-group-form" onSubmit={save} aria-label={group ? `Editar grupo ${group.name}` : "Criar novo grupo"}>
    {group && <h2>{form.name}</h2>}
    <fieldset disabled={busy} className="management-group-fields"><legend className="mag-sr-only">Dados do grupo</legend>
      <label>Nome do grupo<input required maxLength={120} value={form.name} onChange={(event) => update("name", event.target.value)} placeholder="Como o grupo será apresentado no site" /></label>
      <label>Apresentação<textarea required maxLength={4000} rows={5} value={form.description} onChange={(event) => update("description", event.target.value)} placeholder="Apresente a missão, as atividades e quem pode participar" /></label>
      <label>Endereço público<input maxLength={500} value={form.address || ""} onChange={(event) => update("address", event.target.value)} /></label>
      <label>WhatsApp público (país e DDD, somente números)<input maxLength={15} pattern="[0-9]{10,15}" value={form.whatsapp || ""} onChange={(event) => update("whatsapp", event.target.value)} /></label>
      <label>Vídeo de apresentação no YouTube<input type="url" maxLength={1000} value={form.video_url || ""} onChange={(event) => update("video_url", event.target.value)} /></label>
      <div className="management-upload-fields"><h3>Enviar imagem do grupo</h3><label htmlFor={`${id}-file`}>Escolher foto do grupo<input id={`${id}-file`} type="file" accept="image/jpeg,image/png,image/webp" required={!group && !file} onChange={chooseFile} aria-describedby={`${id}-limits`} /></label><p id={`${id}-limits`} className="management-hint">JPG, PNG ou WebP · até 5 MB. Recomendado: 1600 × 900 px. Mínimo: 800 × 450 px. Máximo: 4096 × 4096 px. A foto recebe recorte central em 16:9 para manter o padrão do site.</p><label>Descrição da foto<input required={Boolean(file || form.cover_url)} maxLength={200} value={form.cover_alt} onChange={(event) => update("cover_alt", event.target.value)} placeholder="Descreva a imagem para quem usa leitor de tela" /></label></div>
      <div className="management-group-preview"><span className="mag-kicker">Prévia da capa</span>{preview ? <div><img src={preview} alt={form.cover_alt || "Prévia da foto do grupo"} /><strong>{form.name || "Nome do grupo"}</strong></div> : <p>Escolha uma foto para visualizar a capa.</p>}</div>
      {administrator && <><label>Ordem de exibição<input type="number" min="0" max="32767" required value={form.position} onChange={(event) => update("position", event.target.value)} /></label><label className="management-check"><input type="checkbox" checked={form.is_active} onChange={(event) => update("is_active", event.target.checked)} />Grupo ativo no site</label><p className="management-hint">Grupos ativos aparecem no catálogo. Desativar o grupo também retira suas publicações da área pública.</p></>}
      <div className="account-actions"><button className="mag-button red" disabled={busy}>{busy ? "Salvando…" : group ? "Salvar página do grupo" : "Criar grupo"}</button>{group ? <SiteLink className="mag-text-link" href={`/grupos/${group.slug}`}>Ver página →</SiteLink> : <SiteLink className="mag-text-link" href="/painel/grupos">Cancelar</SiteLink>}</div>
    </fieldset><p className="form-feedback" role="status">{feedback}</p>
  </form>;
}
