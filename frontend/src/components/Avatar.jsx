export default function Avatar({ photo, name, className = "" }) {
  const apiOrigin = "https://api.rhemacuc.com.br";

  const photoUrl = photo?.startsWith("/api/")
    ? `${apiOrigin}${photo}`
    : photo;

  return photoUrl ? (
    <img
      className={`profile-avatar ${className}`}
      src={photoUrl}
      alt={`Foto de ${name || "integrante da comunidade"}`}
    />
  ) : (
    <span
      className={`profile-avatar profile-avatar-fallback ${className}`}
      aria-hidden="true"
    >
      {(name || "C").trim().slice(0, 1).toUpperCase() || "C"}
    </span>
  );
}
