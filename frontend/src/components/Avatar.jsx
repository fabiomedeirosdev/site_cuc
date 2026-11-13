export default function Avatar({ photo, name, className = "" }) {
  return photo ? <img className={`profile-avatar ${className}`} src={photo} alt={`Foto de ${name || "integrante da comunidade"}`} /> : <span className={`profile-avatar profile-avatar-fallback ${className}`} aria-hidden="true">{(name || "C").trim().slice(0, 1).toUpperCase() || "C"}</span>;
}
