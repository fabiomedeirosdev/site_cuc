import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";

const roles = [["", "Sem função geral"], ["columnist", "Facilitador(a)"], ["administration", "Administração"], ["priest", "Padre"], ["deacon", "Diácono"], ["founder", "Fundador(a)"], ["developer", "Desenvolvedor(a)"]];

export default function TeamManager({ groups }) {
  const { user, ensureSession } = useAuth();
  const [deleting, setDeleting] = useState(null);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("membro") || "");
  const [search, setSearch] = useState(() => new URLSearchParams(window.location.search).get("membro") || "");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const resource = useResource((signal) => api.getTeam(page, search, { signal }), [page, search]);
  const options = roles.filter(([value]) => value !== "developer" || user?.can_assign_developer);
  async function save(event, person) {
    event.preventDefault(); setBusy(true); setFeedback("");
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      if (person) {
        await api.updateTeamMember(person.id, { role: data.get("role"), display_name: data.get("display_name"), email: data.get("email"), biography: data.get("biography"), website: data.get("website"), video_url: data.get("video_url"), first_name: data.get("first_name"), last_name: data.get("last_name"), ...(user?.can_order_members ? { position: Number(data.get("position")) } : {}) });
      } else {
        await api.addTeamMember({ email: data.get("email"), role: data.get("role"), group: data.get("group") ? Number(data.get("group")) : null, ...(data.get("password") ? { password: data.get("password"), display_name: data.get("display_name") } : {}) });
        form.reset();
      }
      setFeedback("Membro atualizado. Os vínculos existentes foram preservados."); resource.reload(); await ensureSession(true);
    } catch (error) { setFeedback(error.message); }
    finally { setBusy(false); }
  }
  async function remove(person) {
    setBusy(true); setFeedback("");
    try { await api.deleteTeamMember(person.id); setDeleting(null); setFeedback("Membro excluído."); resource.reload(); }
    catch (error) { setFeedback(error.message); }
    finally { setBusy(false); }
  }
  return <section className="editorial-management-box"><h2>Membros da Comunidade</h2><p>Cadastre ou vincule uma conta. Para um novo acesso, informe também nome e senha inicial.</p>
    <form className="editorial-form" onSubmit={(event) => save(event)}>
      <label>E-mail<input name="email" type="email" required maxLength={254} /></label>
      <label>Nome do novo membro<input name="display_name" maxLength={150} /></label>
      <label>Senha inicial para novo acesso<input name="password" type="password" minLength={8} maxLength={1024} autoComplete="new-password" /></label>
      <label>Grupo<select name="group"><option value="">Atuação geral — sem grupo específico</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Função<select name="role">{options.map(([value, label]) => <option value={value} key={value}>{label}</option>)}<option value="coordinator">Coordenador(a) (com grupo)</option></select></label>
      <button className="mag-button red" disabled={busy}>Adicionar integrante</button>
    </form>
    <p role="status" className="form-feedback">{feedback}</p>{deleting && <div className="editorial-notice" role="alert"><p>Excluir a conta de {deleting.display_name} ({deleting.email})? O acesso e os vínculos serão removidos. Os registros históricos serão preservados. Esta ação não pode ser desfeita.</p><div className="account-actions"><button className="mag-button red" disabled={busy} onClick={() => remove(deleting)}>Confirmar exclusão</button><button className="mag-button pale" disabled={busy} onClick={() => setDeleting(null)}>Cancelar</button></div></div>}
    <form className="content-search" onSubmit={(event) => { event.preventDefault(); setSearch(query); setPage(1); }}><label>Buscar membro<input value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="mag-button pale">Buscar</button></form>
    <ResourceStatus resource={resource} />
    {resource.data && <>
      <div className="editorial-members">{resource.data.results.map((person) => <article className="editorial-member" key={JSON.stringify(person)}>
        <h3>{person.display_name}</h3><p>{person.email}</p>
        <form className="editorial-form" onSubmit={(event) => save(event, person)}>
          <fieldset className="editorial-form" disabled={busy || (person.role === "developer" && !user?.can_assign_developer)}>
            <legend>Dados do membro</legend>
            <label>Nome de exibição<input name="display_name" defaultValue={person.display_name} maxLength={150} required /></label>
            <label>Nome<input name="first_name" defaultValue={person.first_name} maxLength={150} /></label>
            <label>Sobrenome<input name="last_name" defaultValue={person.last_name} maxLength={150} /></label>
            <label>E-mail<input name="email" type="email" defaultValue={person.email} maxLength={254} required /></label>
            <label>Biografia<textarea name="biography" defaultValue={person.biography} maxLength={3000} /></label>
            <label>Site<input name="website" type="url" defaultValue={person.website} maxLength={500} /></label>
            <label>Vídeo de apresentação<input name="video_url" type="url" defaultValue={person.video_url} maxLength={1000} /></label>
            <label>Função geral<select name="role" defaultValue={person.community_role}>{[...options, ...(person.community_role === "developer" && !user?.can_assign_developer ? [["developer", "Desenvolvedor(a)"]] : [])].map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            {user?.can_order_members && <label>Ordem de exibição<input name="position" type="number" min="0" max="32767" required defaultValue={person.position} /></label>}
            <button className="mag-button red" disabled={busy}>Salvar membro</button>
          </fieldset>
        </form>
        {person.id !== user.id && (person.role !== "developer" || user?.can_assign_developer) && <button type="button" className="content-delete" disabled={busy} onClick={() => setDeleting(person)}>Excluir membro</button>}
      </article>)}</div>
      <Pagination data={resource.data} page={page} setPage={setPage} />
    </>}
  </section>;
}
