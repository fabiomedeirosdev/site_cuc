export default function SocialIcon({ name }) {
  if (name === "youtube") return <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21.6 7.2c-.2-1-1-1.8-2-2C17.9 4.8 12 4.8 12 4.8s-5.9 0-7.6.4c-1 .2-1.8 1-2 2C2 8.9 2 12 2 12s0 3.1.4 4.8c.2 1 1 1.8 2 2 1.7.4 7.6.4 7.6.4s5.9 0 7.6-.4c1-.2 1.8-1 2-2 .4-1.7.4-4.8.4-4.8s0-3.1-.4-4.8Z" /><path fill="#fffdf8" d="m10 8.7 5.6 3.3-5.6 3.3Z" /></svg>;
  if (name === "instagram") return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M14.2 22v-8.9h3l.5-3.5h-3.5V7.4c0-1 .3-1.7 1.8-1.7h1.9V2.5c-.3 0-1.5-.2-2.8-.2-2.8 0-4.7 1.7-4.7 4.8v2.6H7.3v3.5h3.1V22Z" /></svg>;
}
