const shapes = {
  camera: <><path d="M3 7h4l2-3h6l2 3h4v14H3Z" /><circle cx="12" cy="14" r="4" /></>,
  link: <><path d="m10 14 4-4m-6 6-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 2 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0" transform="translate(1 0)" /></>,
  phone: <path d="m4 3 4 1 2 5-3 2a14 14 0 0 0 6 6l2-3 5 2 1 4c-8 4-22-10-17-17Z" />,
  lock: <><rect x="4" y="10" width="16" height="12" rx="2" /><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v3" /></>,
  key: <><circle cx="8" cy="8" r="5" /><path d="m11.5 11.5 10 10m-4-4 3-3m-6 0 3-3" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Zm0 0L11 13" /></>,
  save: <><path d="M3 3h15l3 3v15H3ZM7 3v6h10V3M7 21v-8h10v8" /><path d="M14 5v2" /></>,
  eye: <><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" /><circle cx="12" cy="12" r="3" /></>,
  info: <><circle cx="12" cy="12" r="10" /><path d="M12 11v6m0-11v1" /></>,
  user: <><circle cx="12" cy="7" r="3" /><path d="M5 21v-3a7 7 0 0 1 14 0v3Z" /></>,
  logout: <><path d="M10 4H4v16h6M10 12h11m-4-4 4 4-4 4" /></>,
  settings: <><path d="m9 3-1 3-3 1-2 3 2 2-1 3 2 3 3-1 3 2 3-2 3 1 2-3-1-3 2-2-2-3-3-1-1-3Z" /><circle cx="12" cy="11" r="4" /></>,
  crown: <><path d="m3 6 4 11h10l4-11-6 5-3-7-3 7ZM7 21h10" /><circle cx="3" cy="5" r="1" /><circle cx="12" cy="3" r="1" /><circle cx="21" cy="5" r="1" /></>,
  article: <><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M12 7h4M8 12h8M8 17h8" /><circle cx="8" cy="7" r=".5" /></>,
  video: <><circle cx="12" cy="12" r="10" /><path d="m10 7 7 5-7 5Z" /></>,
  audio: <><path d="M4 13V9a8 8 0 0 1 16 0v4" /><rect x="2" y="12" width="5" height="9" rx="2" /><rect x="17" y="12" width="5" height="9" rx="2" /></>,
  mail: <><rect x="2" y="4" width="20" height="16" rx="2" /><path d="m2 6 10 8L22 6" /></>,
  community: <><circle cx="12" cy="6" r="3" /><circle cx="4" cy="8" r="2.5" /><circle cx="20" cy="8" r="2.5" /><path d="M6 22v-4a6 6 0 0 1 12 0v4ZM6 13a5 5 0 0 0-5 5v3h5m12-8a5 5 0 0 1 5 5v3h-5" /></>,
  calendar: <><rect x="2" y="5" width="20" height="17" rx="2" /><path d="M6 2v6m12-6v6M2 11h20M7 15h2m6 0h2M7 18h2m6 0h2" /></>,
};

export default function AccountIcon({ name }) {
  return <svg className="account-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{shapes[name]}</svg>;
}
