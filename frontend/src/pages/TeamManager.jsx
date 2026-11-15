import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";

const roles = [["", "Sem função geral"], ["columnist", "Facilitador"], ["founder", "Fundador"], ["developer", "Desenvolvedor"]];

export default function TeamManager({ groups }) {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const resource = useResource((signal) => api.getTeam(page, search, { signal }), [page, search]);
  const options = roles.filter(([value]) => value !== "developer" || user?.can_order_members);
  async function save(event, person) {
    event.preventDefault(); setBusy(true); setFeedback("");
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      if (person) {
        await api.updateTeamMember(person.id, { role: data.get("role"), ...(user?.can_order_members ? { position: Number(data.get("position")) } : {}) });
      } else {
        await api.addTeamMember({ email: data.get("email"), role: data.get("role"), group: data.get("group") ? Number(data.get("group")) : null, ...(data.get("password") ? { password: data.get("password"), display_name: data.get("display_name") } : {}) });
        form.reset();
      }
      setFeedback("Membro atualizado. Os vínculos existentes foram preservados."); resource.reload();
    } catch (error) { setFeedback(error.message); }
    finally { setBusy(false); }
  }
  return <section className="editorial-management-box"><h2>Membros da Comunidade</h2><p>Cadastre ou vincule uma conta. Para um novo acesso, informe também nome e senha inicial.</p>
    <form className="editorial-form" onSubmit={(event) => save(event)}>
      <label>E-mail<input name="email" type="email" required maxLength={254} /></label>
      <label>Nome do novo membro<input name="display_name" maxLength={150} /></label>
      <label>Senha inicial para novo acesso<input name="password" type="password" minLength={8} maxLength={1024} autoComplete="new-password" /></label>
      <label>Grupo<select name="group"><option value="">Atuação geral — sem grupo específico</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Função<select name="role">{options.map(([value, label]) => <option value={value} key={value}>{label}</option>)}<option value="coordinator">Coordenador (com grupo)</option></select></label>
      <button className="mag-button red" disabled={busy}>Adicionar integrante</button>
    </form>
    <p role="status" className="form-feedback">{feedback}</p>
    <form className="content-search" onSubmit={(event) => { event.preventDefault(); setSearch(query); setPage(1); }}><label>Buscar membro<input value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="mag-button pale">Buscar</button></form>
    <ResourceStatus resource={resource} />
    {resource.data && <><div className="editorial-members">{resource.data.results.map((person) => <article className="editorial-member" key={`${person.id}-${person.community_role}-${person.position}`}><h3>{person.display_name}</h3><p>{person.email}</p><form className="editorial-form" onSubmit={(event) => save(event, person)}><label>Função geral<select name="role" defaultValue={person.community_role}>{[...options, ...(person.community_role === "developer" && !user?.can_order_members ? [["developer", "Desenvolvedor"]] : [])].map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>{user?.can_order_members && <label>Ordem de exibição<input name="position" type="number" min="0" max="32767" required defaultValue={person.position} /></label>}<button className="mag-button red" disabled={busy}>Salvar membro</button></form></article>)}</div><Pagination data={resource.data} page={page} setPage={setPage} /></>}
  </section>;
}
