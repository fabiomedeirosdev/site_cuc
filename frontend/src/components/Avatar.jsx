export default function Avatar({ photo, name, className = "" }) {
  const localPreview = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
  const configuredApiOrigin = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, "");
  // A prévia usa o proxy local; em produção, preservar o domínio da API.
  const apiOrigin = configuredApiOrigin || (localPreview ? "" : "https://api.rhemacuc.com.br");

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
