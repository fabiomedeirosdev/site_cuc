import { useState } from "react";
import SiteLink from "../components/SiteLink.jsx";
import { api } from "../api.js";
import { EditorialLayout, ResourceStatus, useResource } from "./GroupsPages.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import "./subscription.css";

export const accessDate = (value) => value ? new Date(value).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "long", timeStyle: "short" }) : "Sem período pago confirmado";

export function LegalCheck({ checked, onChange }) {
  return <label className="billing-consent"><input type="checkbox" required checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>Li e aceito os <SiteLink href="/termos.html" target="_blank" rel="noopener noreferrer">Termos de uso</SiteLink> e a <SiteLink href="/politica-privacidade.html" target="_blank" rel="noopener noreferrer">Política de privacidade</SiteLink>.</span></label>;
}

export function SubscribePage() {
  const config = useResource((signal) => api.getBillingConfig({ signal }));
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function checkout(event) {
    event.preventDefault(); setBusy(true); setError("");
    try { const result = await api.createCheckout({ accepted, legal_version: config.data.legal_version }); window.location.assign(result.url); }
    catch (failure) { setError(failure.message || "Não foi possível abrir o checkout. Nenhuma cobrança foi realizada pelo site."); }
    finally { setBusy(false); }
  }
  return <EditorialLayout title="Assine a Comunidade Online" intro="Fé, formação e vida em comunidade, com acesso aos conteúdos exclusivos."><ResourceStatus resource={config} />{config.data && <section className="billing-offer"><div><span className="mag-kicker">Assinatura mensal</span><h2>Comunidade Online<br />Unidos em Cristo</h2><div className="billing-price">{(config.data.amount / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}<span>por mês</span></div><ul><li>Artigos e reflexões dos facilitadores</li><li>Vídeos para assistir dentro da comunidade</li><li>Renovação mensal, sem prazo mínimo de permanência</li><li>Cancelamento com preservação do período já pago</li></ul></div><div className="billing-offer-action"><h2>Como funciona</h2><ol><li>Você paga no checkout seguro do PagBank.</li><li>Após a confirmação, recebe um link por e-mail.</li><li>Cria sua conta ou vincula uma conta existente.</li></ol><p>Use no checkout um e-mail ao qual você tenha acesso. A mensalidade é recorrente, por cartão de crédito, conforme as opções apresentadas pelo PagBank.</p><form onSubmit={checkout}><LegalCheck checked={accepted} onChange={setAccepted} /><button className="mag-button red" disabled={busy || !config.data.available}>{busy ? "Abrindo checkout…" : "Ir para o pagamento seguro →"}</button></form>{config.data.sandbox && config.data.available && <p className="billing-note">Ambiente de testes do PagBank. Não utilize dados reais.</p>}{!config.data.available && <p className="billing-note" role="status">A contratação ainda não foi ativada. Nenhuma cobrança será realizada.</p>}<p role="alert" className="form-feedback">{error}</p><SiteLink className="mag-text-link" href="/minha-assinatura.html">Já assinou? Consulte sua assinatura →</SiteLink></div></section>}</EditorialLayout>;
}

export function MySubscriptionPage() {
  const { ensureSession } = useAuth();
  const resource = useResource((signal) => api.getSubscriptions({ signal }));
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [requestType, setRequestType] = useState("withdrawal");
  const [message, setMessage] = useState("");
  async function cancel(id) {
    setBusy(true); setFeedback("");
    try { const result = await api.cancelSubscription(id); setFeedback(result.detail); setConfirming(null); resource.reload(); await ensureSession(true); }
    catch (error) { setFeedback(error.message || "Não foi possível confirmar o cancelamento. Tente novamente."); }
    finally { setBusy(false); }
  }
  async function request(event, id) {
    event.preventDefault(); setBusy(true); setFeedback("");
    try { const result = await api.createConsumerRequest(id, { kind: requestType, message }); setFeedback(`Protocolo ${result.protocol}. ${result.detail}`); setMessage(""); resource.reload(); }
    catch (error) { setFeedback(error.message || "Não foi possível registrar a solicitação."); }
    finally { setBusy(false); }
  }
  return <EditorialLayout title="Minha Assinatura" intro="Consulte sua validade, encerre a renovação e acompanhe suas solicitações."><ResourceStatus resource={resource} /><p role="status" className="form-feedback">{feedback}</p>{resource.data && <>{resource.data.has_access && <div className="billing-access"><strong>Seu acesso está liberado.</strong><p>Validade: {accessDate(resource.data.access_until)} — horário de Brasília.</p></div>}{resource.data.subscriptions.length === 0 && <div className="editorial-notice"><p>Nenhuma assinatura foi vinculada a esta conta. Se você já pagou, abra o link enviado ao e-mail informado no checkout.</p><SiteLink className="mag-button red" href="/assinatura.html">Conhecer a assinatura</SiteLink></div>}{resource.data.subscriptions.map((subscription) => <section className="billing-subscription-card" key={subscription.id}><h2>Comunidade Online</h2><p><strong>Validade do período pago:</strong> {accessDate(subscription.access_until)}</p><p>{subscription.status === "CANCELED" ? "Renovação encerrada. O acesso continua até o fim do período pago." : subscription.status === "OVERDUE" ? "Há uma cobrança em atraso. O acesso depende da validade do último período pago." : `Situação da assinatura: ${({ ACTIVE: "ativa", PENDING: "aguardando confirmação", SUSPENDED: "renovação suspensa", EXPIRED: "encerrada", PENDING_ACTION: "pagamento pendente de ação" })[subscription.status] || "aguardando atualização"}.`}</p>{subscription.cancel_requested && subscription.can_cancel && <p className="billing-note">Há um pedido de cancelamento aguardando confirmação do banco. Você pode tentar novamente.</p>}{subscription.can_cancel && <button className="mag-button red" disabled={busy} onClick={() => setConfirming(subscription.id)}>Cancelar assinatura</button>}{confirming === subscription.id && <div className="editorial-notice"><h3>Cancelar as próximas cobranças?</h3><p>Seu acesso continuará até {accessDate(subscription.access_until)}. Este cancelamento não solicita automaticamente um estorno.</p><div className="account-actions"><button className="mag-button red" disabled={busy} onClick={() => cancel(subscription.id)}>Confirmar cancelamento</button><button className="mag-button pale" disabled={busy} onClick={() => setConfirming(null)}>Voltar</button></div></div>}<details className="billing-requests"><summary>Arrependimento, reembolso ou privacidade</summary><p>Para compras à distância, há direito de arrependimento no prazo legal de sete dias. Você também pode exercer os demais direitos previstos na legislação. Registre o pedido para receber um protocolo e confirmação por e-mail.</p><form onSubmit={(event) => request(event, subscription.id)}><label>Tipo de solicitação<select value={requestType} onChange={(event) => setRequestType(event.target.value)}><option value="withdrawal">Arrependimento / reembolso</option><option value="privacy">Dados pessoais e privacidade</option></select></label><label>Mensagem<textarea value={message} onChange={(event) => setMessage(event.target.value)} maxLength={4000} rows={4} /></label><button className="mag-button red" disabled={busy}>Registrar solicitação</button></form>{subscription.requests.length > 0 && <ul>{subscription.requests.map((item) => <li key={item.id}>Protocolo {item.id} · {item.resolved ? "Concluído pelo atendimento" : "Em atendimento"}</li>)}</ul>}</details></section>)}</>}<SiteLink className="mag-text-link" href="/area-associado.html">← Voltar à minha conta</SiteLink></EditorialLayout>;
}

export function ResendInviteForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  return <form className="login-form" onSubmit={async (event) => { event.preventDefault(); setBusy(true); try { const result = await api.resendInvitation(email); setFeedback(result.detail); } catch { setFeedback("Não foi possível enviar a solicitação. Tente novamente mais tarde."); } finally { setBusy(false); } }}><label>E-mail do pagamento<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><button className="mag-button red" disabled={busy}>Solicitar novo link</button><p role="status" className="form-feedback">{feedback}</p></form>;
}
