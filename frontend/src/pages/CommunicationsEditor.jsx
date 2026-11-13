import { useEffect, useState } from "react";
import { api } from "../api.js";
import CommunicationImageField from "../components/CommunicationImageField.jsx";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";
import { communicationPayload, eventDate, isoInput, localInput } from "./communications-format.js";

function AudienceField({ value, onChange, weekly = false, newsletter = false }) {
  return <><label>{weekly ? "Público do boletim semanal" : "Público do conteúdo"}<select value={value ? "members" : "public"} onChange={(event) => onChange(event.target.value === "members")}><option value="public">Público — visitantes e assinantes</option><option value="members">Somente assinantes</option></select></label><p className="communications-field-help">{newsletter ? "Público: envio a todos que confirmaram o recebimento, incluindo assinantes. Somente assinantes: envio apenas a quem autorizou os e-mails e tem acesso de assinatura vigente." : "Público: todos podem consultar. Somente assinantes: o título continua visível; o conteúdo completo fica reservado a quem tem acesso vigente."}</p></>;
}

function WeeklyPanel() {
  const resource = useResource((signal) => api.getWeeklyNewsletter({ signal }));
  const [data, setData] = useState(null);
  const [file, setFile] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (resource.data) { const { delivery_available, ...fields } = resource.data; setData(fields); } }, [resource.data]);
  const field = (key, value) => setData((current) => ({ ...current, [key]: value }));
  return <section className="communications-card"><h2>Boletim semanal automático</h2><p>A edição reúne os próximos 14 dias da agenda e os avisos mais recentes do mural. O envio usa o horário de Brasília.</p><ResourceStatus resource={resource} />{data && <form className="editorial-form" onSubmit={async (event) => {
    event.preventDefault(); setBusy(true); setFeedback("");
    try { await api.saveWeeklyNewsletter(communicationPayload(data, file, removeImage)); setFile(null); setRemoveImage(false); setFeedback("Programação semanal salva."); resource.reload(); }
    catch (error) { setFeedback(error.message); } finally { setBusy(false); }
  }}>
    <label className="newsletter-consent"><input type="checkbox" checked={data.weekly_enabled} onChange={(event) => field("weekly_enabled", event.target.checked)} />Ativar boletim semanal automático</label>
    <div className="communications-fields"><label>Dia da semana<select value={data.weekday} onChange={(event) => field("weekday", Number(event.target.value))}>{["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"].map((day, index) => <option value={index} key={day}>{day}</option>)}</select></label><label>Horário de Brasília<select value={data.hour} onChange={(event) => field("hour", Number(event.target.value))}>{Array.from({ length: 24 }, (_, hour) => <option value={hour} key={hour}>{String(hour).padStart(2, "0")}:00</option>)}</select></label></div>
    <label>Assunto semanal<input value={data.subject} required maxLength={180} onChange={(event) => field("subject", event.target.value)} /></label><label>Mensagem semanal<textarea rows={5} value={data.introduction} required maxLength={10000} onChange={(event) => field("introduction", event.target.value)} /></label>
    <AudienceField value={data.is_members_only} onChange={(value) => field("is_members_only", value)} weekly newsletter />
    <CommunicationImageField imageUrl={data.image_url} imageAlt={data.image_alt} file={file} removeImage={removeImage} onFile={setFile} onAlt={(value) => field("image_alt", value)} onRemove={setRemoveImage} disabled={busy} />
    <button className="mag-button red" disabled={busy}>Salvar programação semanal</button>{resource.data?.delivery_available === false && <p className="billing-note">O envio de e-mails ainda não está ativado no servidor. Você pode preparar a programação; nenhuma mensagem será enviada enquanto essa configuração estiver pendente.</p>}
  </form>}<p role="status" className="form-feedback">{feedback}</p></section>;
}

const imageDefaults = { image_url: null, image_alt: "", is_members_only: false };
const emptyEvent = { title: "", description: "", starts_at: "", ends_at: "", location: "", is_published: false, is_cancelled: false, is_members_only: false };
const emptyNotice = { title: "", body: "", is_published: false, ...imageDefaults };
const emptyCampaign = { subject: "", introduction: "", scheduled_at: "", status: "draft", ...imageDefaults };

export default function ContentPanel({ kind }) {
  const [page, setPage] = useState(1);
  const resource = useResource((signal) => api.getCommunications(kind, page, { signal }), [kind, page]);
  const defaults = kind === "events" ? emptyEvent : kind === "notices" ? emptyNotice : emptyCampaign;
  const [form, setForm] = useState({ ...defaults });
  const [file, setFile] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [id, setId] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState("");
  const [deleting, setDeleting] = useState(null);
  const campaigns = kind === "campaigns";
  function field(name, value) { setForm((current) => ({ ...current, [name]: value })); setPreview(""); }
  function reset() { setForm({ ...defaults }); setFile(null); setRemoveImage(false); setId(null); setPreview(""); }
  function edit(item) {
    const data = Object.fromEntries(Object.keys(defaults).map((key) => [key, item[key] ?? defaults[key]]));
    for (const key of ["starts_at", "ends_at", "scheduled_at"]) if (key in data) data[key] = localInput(data[key]);
    setForm(data); setFile(null); setRemoveImage(false); setId(item.id); setPreview(""); document.getElementById("communications-editor")?.scrollIntoView({ behavior: "instant" });
  }
  function payload(status = "draft") {
    const data = { ...form };
    for (const key of ["starts_at", "ends_at", "scheduled_at"]) if (key in data) data[key] = isoInput(data[key]);
    if (campaigns) data.status = status;
    return kind === "events" ? data : communicationPayload(data, file, removeImage);
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setFeedback("");
    const status = event.nativeEvent.submitter?.value || "draft";
    try { await api.saveCommunication(kind, id, payload(status)); setFeedback(campaigns && status === "scheduled" ? "Edição agendada. A entrega depende da ativação de e-mails no servidor." : "Conteúdo salvo."); reset(); resource.reload(); }
    catch (error) { setFeedback(error.message || "Não foi possível salvar."); } finally { setBusy(false); }
  }
  return <><section className="communications-card" id="communications-editor"><h2>{id ? "Editar" : "Criar"} {campaigns ? "edição da newsletter" : kind === "events" ? "evento" : "aviso"}</h2>
    <form className="editorial-form" onSubmit={submit}>
      <label>{campaigns ? "Assunto da edição" : "Título"}<input value={campaigns ? form.subject : form.title} required maxLength={campaigns ? 180 : 200} onChange={(event) => field(campaigns ? "subject" : "title", event.target.value)} /></label>
      <label>{campaigns ? "Mensagem da edição" : kind === "events" ? "Descrição do evento" : "Texto do aviso"}<textarea value={campaigns ? form.introduction : kind === "events" ? form.description : form.body} required rows={7} maxLength={campaigns ? 10000 : 20000} onChange={(event) => field(campaigns ? "introduction" : kind === "events" ? "description" : "body", event.target.value)} /></label>
      {kind === "events" && <><div className="communications-fields"><label>Início (Brasília)<input type="datetime-local" required value={form.starts_at} onChange={(event) => field("starts_at", event.target.value)} /></label><label>Término (Brasília)<input type="datetime-local" value={form.ends_at} onChange={(event) => field("ends_at", event.target.value)} /></label></div><label>Local do evento<input required maxLength={300} value={form.location} onChange={(event) => field("location", event.target.value)} /></label><label className="newsletter-consent"><input type="checkbox" checked={form.is_cancelled} onChange={(event) => field("is_cancelled", event.target.checked)} />Informar que o evento foi cancelado</label></>}
      <AudienceField value={form.is_members_only} onChange={(value) => field("is_members_only", value)} newsletter={campaigns} />
      {kind !== "events" && <CommunicationImageField imageUrl={form.image_url} imageAlt={form.image_alt} file={file} removeImage={removeImage} onFile={(value) => { setFile(value); setPreview(""); }} onAlt={(value) => field("image_alt", value)} onRemove={(value) => { setRemoveImage(value); setPreview(""); }} disabled={busy} />}
      {campaigns ? <label>Agendar para (Brasília)<input type="datetime-local" aria-label="Agendar para (Brasília)" value={form.scheduled_at} onChange={(event) => field("scheduled_at", event.target.value)} /><small>Preencha para agendar uma edição. Para o envio recorrente, use a programação semanal abaixo.</small></label> : <label className="newsletter-consent"><input type="checkbox" checked={form.is_published} onChange={(event) => field("is_published", event.target.checked)} />Publicar {kind === "events" ? "na agenda e no mural" : "no mural"}</label>}
      <div className="account-actions"><button className="mag-button red" disabled={busy} value="draft">{campaigns ? "Salvar rascunho" : "Salvar publicação"}</button>{campaigns && <><button className="mag-button pale" value="scheduled" disabled={busy}>Agendar envio</button><button className="mag-button pale" type="button" disabled={busy} onClick={async () => {
        setBusy(true); setFeedback("");
        try { const data = payload(); if (id) data.append("campaign_id", String(id)); const result = await api.previewNewsletter(data); setPreview(result.html); }
        catch (error) { setFeedback(error.message); } finally { setBusy(false); }
      }}>Ver prévia do e-mail</button></>}<button className="mag-button pale" type="button" disabled={busy} onClick={reset}>Novo {campaigns ? "rascunho" : "conteúdo"}</button></div>
    </form>{preview && <iframe className="newsletter-preview" title="Prévia da newsletter" sandbox="" srcDoc={preview} />}<p role="status" className="form-feedback">{feedback}</p>
  </section><ResourceStatus resource={resource} />{resource.data && <><div className="communications-list">{resource.data.results.map((item) => <article className="communications-card" key={item.id}>
    <h3>{item.title || item.subject}</h3><p>{campaigns ? ({ draft: "Rascunho", scheduled: "Envio agendado", sending: "Em envio", sent: "Envio concluído", cancelled: "Envio cancelado" })[item.status] : item.is_published ? "Publicado" : "Rascunho"}{item.is_cancelled ? " · Evento cancelado" : ""}</p>
    <span className="event-audience">{item.is_members_only ? "Somente assinantes" : "Público — visitantes e assinantes"}</span>
    {item.image_url && <img className="communication-image-preview" src={item.image_url} alt={item.image_alt || ""} loading="lazy" />}
    {campaigns && <><p>{item.scheduled_at ? eventDate(item.scheduled_at) : "Sem data agendada"} · {item.sent_count} enviados · {item.pending_count} pendentes</p>{item.error && <p role="alert">{item.error}</p>}</>}
    <div className="account-actions">{(!campaigns || ["draft", "scheduled"].includes(item.status)) && <button className="mag-button pale" disabled={busy} onClick={() => edit(item)}>Editar</button>}{campaigns && ["scheduled", "sending"].includes(item.status) && <button className="mag-button pale" disabled={busy} onClick={async () => {
      setBusy(true); try { await api.saveCommunication(kind, item.id, { status: "cancelled" }); setFeedback("Envio cancelado. Mensagens ainda pendentes não serão enviadas."); if (id === item.id) reset(); resource.reload(); } catch (error) { setFeedback(error.message); } finally { setBusy(false); }
    }}>Cancelar envio</button>}{(!campaigns || item.status === "draft") && <button className="mag-button pale" disabled={busy} onClick={() => setDeleting(item.id)}>Excluir</button>}</div>
    {deleting === item.id && <div className="editorial-notice"><p>Excluir este conteúdo? {kind === "events" ? "Ele também sairá do mural. Para preservar um aviso de cancelamento, edite o evento e marque como cancelado." : "Essa ação remove a publicação."}</p><button className="mag-button red" disabled={busy} onClick={async () => {
      setBusy(true); try { await api.deleteCommunication(kind, item.id); setDeleting(null); if (id === item.id) reset(); resource.reload(); } catch (error) { setFeedback(error.message); } finally { setBusy(false); }
    }}>Confirmar exclusão</button><button className="mag-button pale" onClick={() => setDeleting(null)}>Voltar</button></div>}
  </article>)}</div><Pagination data={resource.data} page={page} setPage={setPage} /></>}{campaigns && <WeeklyPanel />}</>;
}
