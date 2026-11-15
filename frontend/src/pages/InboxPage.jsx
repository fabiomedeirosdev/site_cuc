import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import ManagementLayout from "../components/ManagementLayout.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { api } from "../api.js";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";
import "./inbox.css";

const date = (value) => new Date(value).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });

function MessageDetail({ id, onSaved }) {
  const resource = useResource((signal) => api.getIncomingMessage(id, { signal }), [id]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const message = resource.data;
  return <section className="management-card inbox-detail"><ResourceStatus resource={resource} />{message && <><span className="mag-kicker">{message.responded_at ? "Resposta registrada" : "Aguardando resposta"}</span><h2>{message.subject}</h2><p className="inbox-sender">{message.sender || "Remetente não identificado"} · {date(message.received_at)}</p><p className="inbox-body">{message.body}</p><p className="management-guidance">Responda pela caixa de e-mail da comunidade. Depois, registre a resposta aqui para retirar o aviso de atendimento pendente.</p><button className="mag-button red" disabled={busy} onClick={async () => { setBusy(true); setError(""); try { await api.respondToIncomingMessage(id, !message.responded_at); resource.reload(); onSaved(); window.dispatchEvent(new Event("community-notifications-refresh")); } catch (failure) { setError(failure.message); } finally { setBusy(false); } }}>{busy ? "Salvando…" : message.responded_at ? "Reabrir atendimento" : "Marcar como respondida"}</button><p className="form-feedback" role="alert">{error}</p></>}</section>;
}

export default function InboxPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("pending");
  const resource = useResource((signal) => user?.can_handle_inbox ? api.getInbox(page, status, { signal }) : Promise.resolve(null), [page, status, user?.can_handle_inbox]);
  const selected = /^\d+$/.test(params.get("mensagem") || "") ? params.get("mensagem") : null;
  return <ManagementLayout title="Mensagens recebidas" intro="Acompanhe os contatos enviados para contato@rhemacuc.com.br.">{user?.can_handle_inbox ? <><div className="account-actions inbox-toolbar"><button className="mag-button pale" aria-pressed={status === "pending"} onClick={() => { setStatus("pending"); setPage(1); }}>Aguardando resposta</button><button className="mag-button pale" aria-pressed={status === "all"} onClick={() => { setStatus("all"); setPage(1); }}>Todas as mensagens</button><button className="mag-button pale" onClick={resource.reload}>Atualizar</button>{resource.data?.webmail_url && <a className="mag-button red" href={resource.data.webmail_url} target="_blank" rel="noopener noreferrer">Abrir caixa de e-mail ↗</a>}</div><ResourceStatus resource={resource} />{resource.data && <div className="inbox-workspace"><section className="management-card inbox-messages" aria-label="Lista de mensagens">{resource.data.results.length ? resource.data.results.map((message) => <button className={String(message.id) === selected ? "inbox-message is-selected" : "inbox-message"} key={message.id} onClick={() => setParams({ mensagem: String(message.id) })}><span>{message.responded_at ? "Respondida" : "Resposta pendente"}</span><strong>{message.subject}</strong><small>{message.sender || "Remetente não identificado"}</small><time dateTime={message.received_at}>{date(message.received_at)}</time></button>) : <p>Nenhuma mensagem {status === "pending" ? "aguardando resposta" : "recebida"}.</p>}<Pagination data={resource.data} page={page} setPage={setPage} /></section>{selected ? <MessageDetail key={selected} id={selected} onSaved={resource.reload} /> : <p className="management-card">Selecione uma mensagem para consultar o contato.</p>}</div>}</> : <p role="alert">Esta área é reservada à equipe de atendimento da comunidade.</p>}</ManagementLayout>;
}
