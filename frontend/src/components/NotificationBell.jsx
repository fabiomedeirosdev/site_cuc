import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { api } from "../api.js";
import SiteLink from "./SiteLink.jsx";
import "./notifications.css";

const dateLabel = (date) => new Date(date).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" });

export default function NotificationBell() {
  const { user, ensureSession } = useAuth();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [position, setPosition] = useState({ left: 12, top: 60 });
  const root = useRef(null);
  const button = useRef(null);
  const heading = useRef(null);
  const activeRequest = useRef(null);
  const id = useId();
  useEffect(() => { ensureSession(); }, [ensureSession]);
  const refresh = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    try {
      const response = await api.getNotifications({ signal: controller.signal });
      if (!controller.signal.aborted) { setData(response); setError(""); }
    } catch {
      if (!controller.signal.aborted) { setData(null); setError("Não foi possível carregar as notificações."); }
    }
  }, [user?.id]);
  useEffect(() => {
    setData(null); setOpen(false); setError("");
    if (!user) return;
    refresh();
    const visibleRefresh = () => { if (document.visibilityState === "visible") refresh(); };
    const interval = setInterval(visibleRefresh, 60000);
    window.addEventListener("focus", visibleRefresh);
    window.addEventListener("community-notifications-refresh", visibleRefresh);
    document.addEventListener("visibilitychange", visibleRefresh);
    return () => { clearInterval(interval); window.removeEventListener("focus", visibleRefresh); window.removeEventListener("community-notifications-refresh", visibleRefresh); document.removeEventListener("visibilitychange", visibleRefresh); activeRequest.current?.abort(); };
  }, [user?.id, refresh]);
  useEffect(() => {
    if (!open) return;
    heading.current?.focus();
    const outside = (event) => { if (!root.current?.contains(event.target)) setOpen(false); };
    const escape = (event) => { if (event.key === "Escape") { setOpen(false); button.current?.focus(); } };
    const close = () => setOpen(false);
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    window.addEventListener("resize", close);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); window.removeEventListener("resize", close); };
  }, [open]);
  if (!user) return null;
  const count = (data?.unread_count || 0) + (data?.pending_count || 0);
  async function markRead() {
    setBusy(true); setError("");
    try { await api.readNotifications(data.as_of); await refresh(); }
    catch { setError("Não foi possível marcar as novidades como lidas."); }
    finally { setBusy(false); }
  }
  function items(rows) {
    return <ul className="notification-list">{rows.map((item) => <li key={item.id} className={item.unread ? "is-unread" : ""}><SiteLink href={item.url} onClick={() => setOpen(false)}><span className="notification-kind">{item.label}</span><strong>{item.title}</strong><time dateTime={item.at}>{dateLabel(item.at)}</time></SiteLink></li>)}</ul>;
  }
  return <div className="notification-bell" ref={root}>
    <button className="notification-toggle" type="button" ref={button} aria-label={count ? `Notificações: ${count} novidades ou atendimentos pendentes` : "Notificações"} aria-expanded={open} aria-controls={id} onClick={() => {
      const rect = button.current.getBoundingClientRect();
      setPosition({ left: Math.max(12, Math.min(window.innerWidth - 372, rect.right - 360)), top: Math.min(rect.bottom + 8, window.innerHeight - 180) });
      setOpen(!open); if (!open) refresh();
    }}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M9 21h6" /></svg>{count > 0 && <span className="notification-count" aria-hidden="true">{count > 99 ? "99+" : count}</span>}</button>
    {open && <section id={id} className="notification-dropdown" style={position} aria-label="Últimas notificações"><div className="notification-heading"><h2 ref={heading} tabIndex={-1}>Notificações</h2><button type="button" onClick={() => { setOpen(false); button.current?.focus(); }} aria-label="Fechar notificações">×</button></div>
      {error ? <div className="notification-feedback" role="alert"><p>{error}</p><button type="button" onClick={refresh}>Tentar novamente</button></div> : !data ? <p className="notification-feedback" role="status">Carregando…</p> : <>
        {data.pending?.length > 0 && <><h3 className="notification-section-title">Precisa de resposta · {data.pending_count}</h3>{items(data.pending)}</>}
        <div className="notification-updates-heading"><h3>Últimas atualizações</h3>{data.unread_count > 0 && <button type="button" disabled={busy} onClick={markRead}>{busy ? "Salvando…" : "Marcar como lidas"}</button>}</div>
        {data.updates?.length ? items(data.updates) : <p className="notification-feedback">Nenhuma novidade nos últimos 30 dias.</p>}
      </>}
    </section>}
  </div>;
}
