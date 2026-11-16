import { useEffect, useState } from "react";
import { api } from "../api.js";
import { rhemaAppIcon } from "../assets.js";
import { currentPushSubscription, disableNotifications, enableNotifications, isInstalled, promptInstallation, supportsPush } from "../pwa.js";
import "./pwa-install.css";

export default function PwaInstallSection() {
  const [installed, setInstalled] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [instructions, setInstructions] = useState(false);
  useEffect(() => {
    let active = true;
    const markInstalled = () => setInstalled(true);
    setInstalled(isInstalled());
    window.addEventListener("rhema-app-installed", markInstalled);
    api.getPushConfig().then((config) => { if (active) setAvailable(config.enabled && supportsPush()); }).catch(() => {});
    currentPushSubscription().then((subscription) => { if (active) setEnabled(Boolean(subscription)); }).catch(() => {});
    return () => { active = false; window.removeEventListener("rhema-app-installed", markInstalled); };
  }, []);

  async function install() {
    setBusy(true); setMessage("");
    try {
      const accepted = await promptInstallation();
      setInstructions(!accepted);
      if (accepted) setMessage("Instalação solicitada. Após concluir, abra RHEMA CUC para ativar as notificações.");
    } catch { setMessage("Não foi possível abrir a instalação. Use a opção de instalar no menu do navegador."); }
    finally { setBusy(false); }
  }

  async function togglePush() {
    setBusy(true); setMessage("");
    try {
      if (enabled) await disableNotifications(api); else await enableNotifications(api);
      setEnabled(!enabled);
      setMessage(enabled ? "Notificações desativadas neste dispositivo." : "Notificações ativadas neste dispositivo.");
    } catch (error) { setMessage(error.message || "Não foi possível atualizar as notificações. Tente novamente."); }
    finally { setBusy(false); }
  }

  return <section className="rhema-pwa" aria-labelledby="rhema-pwa-title">
    <img src={rhemaAppIcon} alt="Ícone do aplicativo RHEMA CUC" width="96" height="96" loading="lazy" />
    <div className="rhema-pwa-copy"><h2 id="rhema-pwa-title">Leve a Comunidade Unidos em Cristo com você!</h2><p>Baixe o App da Comunidade e receba notificações de novas publicações, reflexões, encontros e eventos diretamente no seu celular.</p>
      <div className="rhema-pwa-actions"><button type="button" className="mag-button red" onClick={install} disabled={busy || installed}>{installed ? "RHEMA CUC instalado" : "Baixe o App da Comunidade"}</button>
        {installed && (available || enabled) && <button type="button" className="mag-button pale" onClick={togglePush} disabled={busy}>{busy ? "Aguarde…" : enabled ? "Desativar notificações" : "Ativar notificações"}</button>}</div>
      {instructions && <div className="rhema-pwa-help"><p><strong>No iPhone:</strong> abra no Safari, toque em Compartilhar e escolha “Adicionar à Tela de Início”. Mantenha o nome RHEMA CUC.</p><p><strong>No Android:</strong> abra o menu do navegador e escolha “Instalar aplicativo” ou “Adicionar à tela inicial”, quando disponível.</p><p>Depois, abra o aplicativo instalado para ativar as notificações.</p></div>}
      {installed && !available && <p className="rhema-pwa-hint">As notificações dependem do suporte do dispositivo e da disponibilidade do serviço. Você pode continuar usando o aplicativo normalmente.</p>}
      <p className="rhema-pwa-hint">As notificações são opcionais e independentes da newsletter por e-mail.</p><p role="status" aria-live="polite">{message}</p>
    </div>
  </section>;
}
