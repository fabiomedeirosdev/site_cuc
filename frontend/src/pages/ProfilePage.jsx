import { useEffect, useRef, useState } from "react";
import SiteLink from "../components/SiteLink.jsx";
import Avatar from "../components/Avatar.jsx";
import { useAuth } from "../auth/AuthContext.jsx";
import { api } from "../api.js";
import { EditorialLayout } from "./GroupsPages.jsx";
import { getYouTubeEmbed, VideoPlayer } from "./ContentPages.jsx";
import "./profiles.css";

export default function ProfilePage() {
  const { user, updateProfile, changePassword, ensureSession } = useAuth();
  const [fields, setFields] = useState({ display_name: user.display_name || "", biography: user.biography || "", website: user.website || "", phone: user.phone || "", video_url: user.video_url || "" });
  const [file, setFile] = useState(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [preview, setPreview] = useState("");
  const photoInput = useRef(null);
  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [profileError, setProfileError] = useState(false);
  const [passwordError, setPasswordError] = useState(false);
  const [emailError, setEmailError] = useState(false);
  useEffect(() => {
    if (!file) { setPreview(""); if (photoInput.current) photoInput.current.value = ""; return; }
    const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url);
  }, [file]);
  const field = (key, value) => setFields((current) => ({ ...current, [key]: value }));
  const photo = preview || (!removePhoto ? user.avatar_url : null);
  async function saveProfile(event) {
    event.preventDefault(); setSavingProfile(true); setProfileMessage(""); setProfileError(false);
    const payload = new FormData();
    for (const key of ["display_name", "biography", "website", "video_url"]) payload.append(key, fields[key]);
    if (user.can_publish_phone) payload.append("phone", fields.phone);
    if (file) payload.append("avatar", file);
    if (removePhoto) payload.append("remove_avatar", "true");
    try { await updateProfile(payload); setFile(null); setRemovePhoto(false); setProfileMessage("Seu perfil público foi atualizado."); }
    catch (error) { setProfileError(true); setProfileMessage(error.status ? error.message : "Não foi possível salvar. Tente novamente."); }
    finally { setSavingProfile(false); }
  }
  async function savePassword(event) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    setPasswordMessage(""); setPasswordError(false);
    if (data.get("new_password") !== data.get("confirm_password")) { setPasswordError(true); setPasswordMessage("As novas senhas não coincidem."); return; }
    setSavingPassword(true);
    try { const result = await changePassword({ current_password: data.get("current_password"), new_password: data.get("new_password") }); form.reset(); setPasswordMessage(result.detail); }
    catch (error) { setPasswordError(true); setPasswordMessage(error.status ? error.message : "Não foi possível alterar a senha. Tente novamente."); }
    finally { setSavingPassword(false); }
  }
  async function saveEmail(event) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    setSavingEmail(true); setEmailMessage(""); setEmailError(false);
    try { const result = await api.requestEmailChange({ new_email: data.get("new_email"), current_password: data.get("email_password") }); form.reset(); setEmailMessage(result.detail); await ensureSession(true); }
    catch (error) { setEmailError(true); setEmailMessage(error.message || "Não foi possível solicitar a alteração."); }
    finally { setSavingEmail(false); }
  }
  return <EditorialLayout title="Meu perfil" intro="Seu lugar na comunidade. Conte sua história e apresente quem você é.">
    <div className="profile-edit-heading"><SiteLink className="mag-text-link" href="/area-associado.html">← Voltar à minha área</SiteLink>{user.public_profile_url && <SiteLink className="mag-button pale" href={user.public_profile_url}>Ver meu perfil público ↗</SiteLink>}</div>
    <div className="profile-edit-layout"><section className="profile-surface" aria-labelledby="profile-title"><div className="profile-identity"><Avatar photo={photo} name={fields.display_name} className="profile-avatar-large" /><div><span className={`profile-role role-${user.profile_role}`}>{user.profile_role_label || "Assinante"}</span><h2 id="profile-title">Minha apresentação</h2><p>Seu nome, foto e apresentação ficam visíveis para todos na comunidade. A função é definida pelo sistema.</p></div></div>
      <form className="profile-form" onSubmit={saveProfile}><fieldset disabled={savingProfile}><legend className="mag-sr-only">Editar apresentação pública</legend>
        <label htmlFor="profile-photo">Minha foto<input ref={photoInput} id="profile-photo" type="file" accept="image/jpeg,image/png,image/webp" aria-describedby="profile-photo-help" onChange={(event) => {
          const chosen = event.target.files[0]; if (!chosen) return;
          setProfileMessage(""); setProfileError(false);
          if (chosen.size > 5 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(chosen.type)) { setProfileError(true); setProfileMessage("Escolha uma foto JPG, PNG ou WebP de até 5 MB."); event.target.value = ""; return; }
          setFile(chosen); setRemovePhoto(false);
        }} /></label><p className="profile-help" id="profile-photo-help">JPG, PNG ou WebP · até 5 MB. Recomendado: 600 × 600 px. Mínimo: 200 × 200 px. Máximo: 4096 × 4096 px. A foto recebe recorte central quadrado para o avatar.</p>{photo && <button type="button" className="mag-text-link profile-remove-photo" onClick={() => { setFile(null); setRemovePhoto(true); }}>Remover minha foto</button>}
        <label htmlFor="display-name">Nome de exibição<input id="display-name" name="display_name" autoComplete="name" maxLength={150} value={fields.display_name} onChange={(event) => field("display_name", event.target.value)} /></label>
        <label>Biografia<textarea name="biography" maxLength={3000} rows={7} value={fields.biography} onChange={(event) => field("biography", event.target.value)} placeholder="Conte um pouco da sua caminhada, dos seus interesses e da sua participação na comunidade" /></label>
        <label>Meu site<input type="url" name="website" maxLength={500} value={fields.website} onChange={(event) => field("website", event.target.value)} placeholder="https://seusite.com.br" /></label>
        {user.can_publish_phone && <><label>Telefone de contato público<input type="tel" name="phone" maxLength={30} value={fields.phone} onChange={(event) => field("phone", event.target.value)} placeholder="(11) 99999-9999" /></label><p className="profile-help">Opcional. Este telefone aparece no seu perfil público. Disponível para desenvolvedor e coordenadores.</p></>}
        <label>Vídeo de apresentação no YouTube<input type="url" name="video_url" maxLength={1000} value={fields.video_url} onChange={(event) => field("video_url", event.target.value)} placeholder="https://www.youtube.com/watch?v=..." /></label><p className="profile-help">O vídeo será exibido aqui na comunidade, sem precisar sair do site.</p><VideoPlayer src={getYouTubeEmbed(fields.video_url)} title="Minha apresentação" />
        <button className="mag-button red" disabled={savingProfile}>{savingProfile ? "Salvando…" : "Salvar perfil"}</button>
      </fieldset><p className="form-feedback" role={profileError ? "alert" : "status"}>{profileMessage}</p></form>
    </section><aside className="profile-private-column"><section className="profile-surface" aria-labelledby="email-title"><span className="mag-kicker">Dados privados da conta</span><h2 id="email-title">E-mail de acesso</h2><p className="profile-private-email">{user.email}</p><p className="profile-help">Seu e-mail não aparece no perfil público. A alteração exige senha atual e confirmação no novo endereço.</p>{user.pending_email && <p className="profile-note">Aguardando confirmação em {user.pending_email}.</p>}
      <form className="profile-form" onSubmit={saveEmail}><label>Novo e-mail<input type="email" name="new_email" maxLength={254} autoComplete="email" required disabled={!user.email_change_available || savingEmail} /></label><label>Senha atual para alterar o e-mail<input type="password" name="email_password" maxLength={1024} autoComplete="current-password" required disabled={!user.email_change_available || savingEmail} /></label><button className="mag-button pale" disabled={!user.email_change_available || savingEmail}>{savingEmail ? "Solicitando…" : "Confirmar novo e-mail"}</button>{!user.email_change_available && <p className="profile-note">A confirmação por e-mail está temporariamente indisponível.</p>}<p className="form-feedback" role={emailError ? "alert" : "status"}>{emailMessage}</p></form>
    </section><section className="profile-surface" aria-labelledby="password-title"><h2 id="password-title">Alterar senha</h2><form className="profile-form" onSubmit={savePassword}>
      <label htmlFor="current-password">Senha atual<input id="current-password" name="current_password" type="password" autoComplete="current-password" maxLength={1024} required /></label><label htmlFor="new-password">Nova senha<input id="new-password" name="new_password" type="password" autoComplete="new-password" minLength={8} maxLength={1024} required /></label><label htmlFor="confirm-password">Confirme a nova senha<input id="confirm-password" name="confirm_password" type="password" autoComplete="new-password" minLength={8} maxLength={1024} required /></label><button className="mag-button red" disabled={savingPassword}>{savingPassword ? "Alterando…" : "Alterar senha"}</button><p className="form-feedback" role={passwordError ? "alert" : "status"}>{passwordMessage}</p>
    </form></section></aside></div>
  </EditorialLayout>;
}
