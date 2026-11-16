export function mediaOrigin(baseUrl = "", hostname = "") {
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(hostname);
  return baseUrl.trim().replace(/\/+$/, "") || (local ? "" : "https://api.rhemacuc.com.br");
}

export function mediaUrl(path, origin = "") {
  return typeof path === "string" && (path.startsWith("/api/") || path.startsWith("/media/"))
    ? `${origin.replace(/\/+$/, "")}${path}` : path;
}

const imageFields = new Set(["avatar_url", "cover_url", "photo_url", "image_url"]);

export function resolveImageUrls(data, origin) {
  if (Array.isArray(data)) return data.map((item) => resolveImageUrls(item, origin));
  if (!data || typeof data !== "object") return data;
  return Object.fromEntries(Object.entries(data).map(([key, value]) => [
    key, imageFields.has(key) ? mediaUrl(value, origin) : resolveImageUrls(value, origin),
  ]));
}
