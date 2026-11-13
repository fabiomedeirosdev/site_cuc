export const eventDate = (value) => new Date(value).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "long", timeStyle: "short" });
export const localInput = (value) => value ? new Date(value).toLocaleString("sv-SE", { timeZone: "America/Sao_Paulo" }).replace(" ", "T").slice(0, 16) : "";
export const isoInput = (value) => value ? new Date(`${value}:00-03:00`).toISOString() : null;

export function communicationPayload(fields, file, removeImage) {
  const data = new FormData();
  for (const [key, value] of Object.entries(fields)) if (key !== "image_url") data.append(key, value == null ? "" : String(value));
  if (file) data.append("image", file);
  if (removeImage) data.append("remove_image", "true");
  return data;
}
