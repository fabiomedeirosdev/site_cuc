import { mediaOrigin, mediaUrl } from "../media-url.js";

export default function Avatar({ photo, name, className = "" }) {
  const photoUrl = mediaUrl(photo, mediaOrigin(import.meta.env.VITE_API_BASE_URL ?? "", window.location.hostname));

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
