import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import ManagementLayout from "../components/ManagementLayout.jsx";
import SiteLink from "../components/SiteLink.jsx";
import { ResourceStatus, useResource } from "./GroupsPages.jsx";

const roles = [["", "Sem função geral"], ["columnist", "Facilitador(a)"], ["administration", "Administração"], ["priest", "Padre"], ["deacon", "Diácono"], ["founder", "Fundador(a)"], ["developer", "Desenvolvedor(a)"]];

function GroupMembershipFields({ person }) {
  const empty = () => ({ group: "", role: "columnist" });
  const [memberships, setMemberships] = useState(() => person.memberships?.length ? person.memberships : [empty()]);
  const groups = person.available_groups || [];
  function update(index, field, value) {
    setMemberships((rows) => rows.map((row, current) => current === index ? { ...row, [field]: value } : row));
  }
  return <div className="editorial-form" role="group" aria-label="Participação nos grupos">
    <h3>Participação nos grupos</h3>
    {memberships.map((membership, index) => <div className="editorial-form" key={index}>
      <label>Grupo<select name="membership_group" value={membership.group} onChange={(event) => update(index, "group", event.target.value)}>
        <option value="">Sem grupo específico</option>
        {groups.map((group) => <option key={group.id} value={group.id} disabled={memberships.some((row, current) => current !== index && String(row.group) === String(group.id))}>{group.name}{group.is_active === false ? " (inativo)" : ""}</option>)}
      </select></label>
      <label>Função no grupo<select name="membership_role" value={membership.role} disabled={!membership.group} onChange={(event) => update(index, "role", event.target.value)}>
        <option value="columnist">Facilitador(a)</option>
        <option value="coordinator">Coordenador(a)</option>
      </select></label>
      {membership.group && <button type="button" className="management-text-button" onClick={() => setMemberships((rows) => rows.length === 1 ? [empty()] : rows.filter((_, current) => current !== index))}>Remover grupo</button>}
    </div>)}
    {memberships.length < groups.length && <button type="button" className="mag-button pale" onClick={() => setMemberships((rows) => [...rows, empty()])}>Adicionar outro grupo</button>}
  </div>;
}

export default function ManageUserPage() {
  const { id } = useParams();
  const { user, ensureSession } = useAuth();
  const administrator = user.roles.includes("administrator");
  const resource = useResource((signal) => administrator ? api.getTeamMember(id, { signal }) : Promise.resolve(null), [id, administrator]);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const person = resource.data?.id === Number(id) ? resource.data : null;
  const allowed = person && (person.role !== "developer" || user.can_assign_developer);
  const options = roles.filter(([role]) => role !== "developer" || user.can_assign_developer || person?.community_role === "developer");

  async function save(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const groupIds = data.getAll("membership_group");
    const groupRoles = Array.from(event.currentTarget.querySelectorAll('select[name="membership_role"]'), (select) => select.value);
    setBusy(true); setFeedback("");
    try {
      await api.updateTeamMember(id, {
        role: data.get("role"), display_name: data.get("display_name"), email: data.get("email"),
        first_name: data.get("first_name"), last_name: data.get("last_name"),
        biography: data.get("biography"), website: data.get("website"), video_url: data.get("video_url"),
        memberships: groupIds.flatMap((group, index) => group ? [{ group: Number(group), role: groupRoles[index] }] : []),
        ...(user.can_order_members ? { position: Number(data.get("position")) } : {}),
      });
      setFeedback("Dados e função atualizados.");
      resource.reload();
      if (Number(id) === user.id) await ensureSession(true);
    } catch (error) { setFeedback(error.message); }
    finally { setBusy(false); }
  }

  return <ManagementLayout title="Editar usuário" intro="Atualize os dados e a função da pessoa selecionada.">
    <SiteLink className="mag-text-link" href="/painel/usuarios">← Voltar para Usuários</SiteLink>
    {!administrator ? <p role="alert">Esta página é exclusiva da administração.</p> : <>
      <ResourceStatus resource={resource} />
      <p role="status" className="form-feedback">{feedback}</p>
      {person && <section className="management-card">
        <h2>{person.display_name}</h2><p>{person.email}</p>
        {!allowed && <p role="alert">Esta conta é administrada pelo(a) Desenvolvedor(a).</p>}
        <form className="editorial-form" key={`${id}-${person.email}`} onSubmit={save}>
          <fieldset className="editorial-form management-user-fields" disabled={busy || !allowed}>
            <legend>Dados do usuário</legend>
            <label>Nome de exibição<input name="display_name" defaultValue={person.display_name} maxLength={150} required /></label>
            <label>Nome<input name="first_name" defaultValue={person.first_name} maxLength={150} /></label>
            <label>Sobrenome<input name="last_name" defaultValue={person.last_name} maxLength={150} /></label>
            <label>E-mail<input name="email" type="email" defaultValue={person.email} maxLength={254} required /></label>
            <label>Biografia<textarea name="biography" defaultValue={person.biography} maxLength={3000} /></label>
            <label>Site<input name="website" type="url" defaultValue={person.website} maxLength={500} /></label>
            <label>Vídeo de apresentação<input name="video_url" type="url" defaultValue={person.video_url} maxLength={1000} /></label>
            <label>Função geral<select name="role" defaultValue={person.community_role}>{options.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <GroupMembershipFields person={person} />
            {user.can_order_members && <label>Ordem de exibição<input name="position" type="number" min="0" max="32767" required defaultValue={person.position} /></label>}
            <div className="account-actions"><button className="mag-button red" disabled={busy || !allowed}>{busy ? "Salvando…" : "Salvar alterações"}</button><SiteLink className="mag-button pale" href="/painel/usuarios">Cancelar</SiteLink></div>
          </fieldset>
        </form>
      </section>}
    </>}
  </ManagementLayout>;
}
