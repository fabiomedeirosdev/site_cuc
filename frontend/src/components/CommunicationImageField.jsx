import { useEffect, useId, useRef, useState } from "react";

export default function CommunicationImageField({ imageUrl, imageAlt, file, removeImage, onFile, onAlt, onRemove, disabled }) {
  const id = useId();
  const input = useRef(null);
  const [localPreview, setLocalPreview] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!file) { setLocalPreview(""); if (input.current) input.current.value = ""; return; }
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const preview = localPreview || (!removeImage ? imageUrl : null);
  return <fieldset className="communication-image-field" disabled={disabled}><legend>Imagem de divulgação (opcional)</legend>
    <label htmlFor={`${id}-file`}>Escolher imagem de divulgação<input ref={input} id={`${id}-file`} type="file" accept="image/jpeg,image/png,image/webp" aria-describedby={`${id}-help`} onChange={(event) => {
      const chosen = event.target.files[0]; if (!chosen) return;
      setError("");
      if (chosen.size > 5 * 1024 * 1024) { setError("A imagem deve ter até 5 MB."); event.target.value = ""; return; }
      if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type)) { setError("Escolha uma imagem JPG, PNG ou WebP."); event.target.value = ""; return; }
      onFile(chosen); onRemove(false);
    }} /></label>
    <p className="communications-field-help" id={`${id}-help`}>JPG, PNG ou WebP · até 5 MB. Recomendado: 1200 × 1600 px para cartazes ou 1600 × 900 px na horizontal. Mínimo: 600 × 300 px. Máximo: 4096 × 4096 px. A imagem mantém sua proporção, sem cortar textos ou detalhes.</p>
    {error && <p role="alert">{error}</p>}
    {preview && <><label>Descrição da imagem<input value={imageAlt || ""} maxLength={200} required onChange={(event) => onAlt(event.target.value)} placeholder="Descreva a imagem para quem usa leitor de tela" /></label><img className="communication-image-preview" src={preview} alt={imageAlt || "Prévia da imagem de divulgação"} /><button type="button" className="mag-text-link communication-remove-image" onClick={() => { onFile(null); onRemove(true); }}>Remover imagem</button></>}
  </fieldset>;
}
