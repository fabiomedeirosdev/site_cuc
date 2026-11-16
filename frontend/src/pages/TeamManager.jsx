import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { Pagination, ResourceStatus, useResource } from "./GroupsPages.jsx";

const roles = [["", "Sem função geral"], ["columnist", "Facilitador(a)"], ["administration", "Administração"], ["priest", "Padre"], ["deacon", "Diácono"], ["founder", "Fundador(a)"], ["developer", "Desenvolvedor(a)"]];

export default function TeamManager({ groups }) {
  const { user, ensureSession } = useAuth();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const resource = useResource((signal) => search ? api.getTeam(page, search, { signal }) : Promise.resolve(null), [page, search]);
  const options = roles.filter(([value]) => value !== "developer" || user?.can_assign_developer);
  async function save(event) {
    event.preventDefault(); setBusy(true); setFeedback("");
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await api.addTeamMember({ email: data.get("email"), role: data.get("role"), group: data.get("group") ? Number(data.get("group")) : null, ...(data.get("password") ? { password: data.get("password"), display_name: data.get("display_name") } : {}) });
      form.reset();
      setFeedback("Membro atualizado. Os vínculos existentes foram preservados."); resource.reload(); await ensureSession(true);
    } catch (error) { setFeedback(error.message); }
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
    <p role="status" className="form-feedback">{feedback}</p>
    <form className="content-search" onSubmit={(event) => { event.preventDefault(); setSearch(query.trim()); setPage(1); }}><label>Buscar membro<input value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="mag-button pale">Buscar</button></form>
    {search && <ResourceStatus resource={resource} />}
    {search && resource.data && <>
      <ul className="editorial-members" aria-label="Resultados da busca de membros">{resource.data.results.map((person) => <li key={person.id}>
        <strong>{person.display_name}</strong> · {person.email}{" "}
        <SiteLink className="mag-text-link" href={`/painel/usuarios/${person.id}/editar`}>Ver cadastro</SiteLink>
      </li>)}</ul>
      {!resource.data.results.length && <p>Nenhum membro encontrado.</p>}
      <Pagination data={resource.data} page={page} setPage={setPage} />
    </>}
  </section>;
}
