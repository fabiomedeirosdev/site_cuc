import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import SiteLink from "../components/SiteLink.jsx";
import { logo, videoCover, foundersPhoto, headquartersPhoto, heroBible, goldenLogos, sunriseSilhouette, sunsetBible, maryAtDusk, crossAtDawn, eucharist, maryGoldenSky, caringHands, goldenBible, familyAtSunset, prayingHands, communityMockup } from "../assets.js";
import "./home.css";
import { HomeEvents, HomeMural, NewsletterSignup } from "./CommunicationsPages.jsx";
import SocialIcon from "../components/SocialIcon.jsx";
import { api } from "../api.js";
import { groupCover } from "../group-covers.js";

const navigation = [["inicio", "Início"], ["noticias", "CUC Online"], ["como-atuamos", "Grupos"], ["agenda", "Agenda"], ["quem-somos", "Sobre"], ["contato", "Contato"]];
const stories = [
  { title: "Uma só missão: viver a fé em comunidade", category: "Comunidade", image: eucharist, alt: "Hóstia IHS e cálice dourado", description: "Acolher, restaurar e transformar vidas. Conheça o carisma que une a Comunidade Unidos em Cristo.", body: "Somos uma Comunidade Católica de aliança, fundada em 2004 na cidade de São Paulo, com reconhecimento canônico da Arquidiocese. Nosso carisma é a restauração: associamos a formação humana à Palavra de Deus para olhar o ser humano em sua dimensão integral." },
  { title: "Maria, presença de amor na caminhada de fé", category: "Espiritualidade", image: maryGoldenSky, alt: "Nossa Senhora sob o céu dourado", description: "Um convite à oração, à espiritualidade e à comunhão com Cristo.", body: "A oração e a partilha da Palavra de Deus estão na origem da nossa comunidade. Caminhamos juntos para fortalecer a fé e viver o Evangelho no cuidado com as pessoas. Novos artigos de espiritualidade serão disponibilizados na comunidade online." },
  { title: "Uma história de fé, acolhimento e restauração", category: "Nossa história", image: foundersPhoto, description: "Conheça as raízes de uma missão que nasceu da oração e do serviço.", body: "Eneida Carmona e Luiz Carmona são psicólogos e fundadores da Comunidade Unidos em Cristo. A missão nasceu de encontros de oração entre casais amigos, com o desejo de partilhar a Palavra de Deus e viver a fé de forma concreta. Com o tempo, passou a oferecer formações, palestras e projetos de restauração do ser." },
];
const groups = [
  { title: "Formação e Palavra", image: goldenBible, text: "Formação humana e Palavra de Deus para crescer na fé e na vida em comunidade." },
  { title: "Rhematerapia", image: caringHands, text: "Dez oficinas voltadas à busca do autoconhecimento e à compreensão mais ampla de si." },
  { title: "Restaura-me", image: prayingHands, text: "Uma vivência do carisma da restauração, associando a Palavra de Deus à formação humana." },
  { title: "Promoção à Vida", image: familyAtSunset, text: "Acolhimento por meio do Projeto Raquel e do trabalho Gravidez em Crise." },
  { title: "Grupo C.U.R.A.", image: headquartersPhoto, text: "Apoio a dependentes e codependentes em situações relacionadas a drogas, álcool e jogos." },
];
const iconPaths = {
  book: <><path d="M3 5c3-1 6-1 9 1 3-2 6-2 9-1v15c-3-1-6-1-9 1-3-2-6-2-9-1Z" /><path d="M12 6v15" /></>,
  users: <><circle cx="12" cy="7" r="3" /><path d="M6 22v-3a6 6 0 0 1 12 0v3M4 5a3 3 0 0 0 0 6M20 5a3 3 0 0 1 0 6M2 19v-2a4 4 0 0 1 3-4M22 19v-2a4 4 0 0 0-3-4" /></>,
  user: <><circle cx="12" cy="7" r="4" /><path d="M4 22v-2a8 8 0 0 1 16 0v2Z" /></>,
  calendar: <><rect x="3" y="5" width="18" height="17" rx="2" /><path d="M7 2v6M17 2v6M3 11h18M7 15h2M12 15h2M17 15h1M7 18h2M12 18h2" /></>,
  play: <><circle cx="12" cy="12" r="10" /><path d="m10 8 6 4-6 4Z" /></>,
  layers: <><path d="m2 6 10-4 10 4-10 4ZM2 12l10 4 10-4M2 18l10 4 10-4" /></>,
  search: <><circle cx="10" cy="10" r="7" /><path d="m15 15 7 7" /></>,
  mail: <><rect x="2" y="4" width="20" height="16" rx="2" /><path d="m3 6 9 7 9-7M3 19l6-6M21 19l-6-6" /></>,
};
function Icon({ name }) { return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name] || iconPaths.book}</svg>; }

function Header({ onSearch, onAbout }) {
  const [open, setOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [active, setActive] = useState("inicio");
  const ref = useRef(null);
  const toggle = useRef(null);
  const aboutRef = useRef(null);
  const aboutToggle = useRef(null);
  const closeMenus = () => { setOpen(false); setAboutOpen(false); };
  useEffect(() => {
    const close = (event) => { if (!ref.current?.contains(event.target)) setOpen(false); if (!aboutRef.current?.contains(event.target)) setAboutOpen(false); };
    const escape = (event) => { if (event.key !== "Escape") return; if (aboutOpen) { setAboutOpen(false); aboutToggle.current?.focus(); } else if (open) { setOpen(false); toggle.current?.focus(); } };
    const media = matchMedia("(min-width: 981px)");
    const resize = () => { setAboutOpen(false); if (media.matches) setOpen(false); };
    document.addEventListener("pointerdown", close); document.addEventListener("keydown", escape); media.addEventListener("change", resize);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", escape); media.removeEventListener("change", resize); };
  }, [open, aboutOpen]);
  return <header className="mag-header" ref={ref}><div className="mag-container mag-nav">
    <SiteLink href="#inicio" className="mag-brand" onClick={closeMenus}><img src={logo} alt="" /><span>Comunidade<br />Unidos em Cristo</span></SiteLink>
    <nav id="main-menu" aria-label="Navegação principal" className={`mag-menu ${open ? "is-open" : ""}`}>{navigation.map(([id, label]) => id === "quem-somos" ? <div className="mag-about" ref={aboutRef} key={id}><button ref={aboutToggle} type="button" className="mag-about-toggle" aria-expanded={aboutOpen} aria-controls="about-community-menu" onClick={() => setAboutOpen((value) => !value)}>{label} <span aria-hidden="true">⌄</span></button><div id="about-community-menu" className="mag-about-panel" hidden={!aboutOpen}><SiteLink href="#quem-somos" onClick={() => { closeMenus(); setActive(id); onAbout(id); }}>Sobre a comunidade</SiteLink><SiteLink href="/fundadores.html" onClick={closeMenus}>Fundadores</SiteLink><SiteLink href="/facilitadores.html" onClick={closeMenus}>Facilitadores</SiteLink><SiteLink href="/perfis.html" onClick={closeMenus}>Pessoas da comunidade</SiteLink></div></div> : <SiteLink key={id} href={`#${id}`} className={active === id ? "is-active" : ""} aria-current={active === id ? "location" : undefined} onClick={() => { closeMenus(); setActive(id); }}>{label}</SiteLink>)}</nav>
    <div className="mag-nav-actions"><button className="mag-search-button" type="button" aria-label="Buscar na comunidade online" onClick={onSearch}><Icon name="search" /></button><SiteLink href="/login.html" className="mag-login"><Icon name="user" /><span>Entrar</span></SiteLink><SiteLink href="#associacao" className="mag-button gold">Seja um Associado</SiteLink></div>
    <button ref={toggle} type="button" className="mag-menu-toggle" aria-label={open ? "Fechar menu" : "Abrir menu"} aria-controls="main-menu" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "×" : "☰"}</button>
  </div></header>;
}

function DetailDialog({ detail, onClose }) {
  const dialog = useRef(null);
  useEffect(() => { if (detail) dialog.current?.showModal(); else dialog.current?.close(); }, [detail]);
  return <dialog className="mag-dialog" ref={dialog} onClose={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }} aria-labelledby="detail-title">{detail && <><button className="mag-dialog-close" type="button" aria-label="Fechar detalhes" onClick={onClose}>×</button>{detail.image && <img src={detail.image} alt="" />}<div className="mag-dialog-copy"><span className="mag-kicker">Comunidade Unidos em Cristo</span><h2 id="detail-title">{detail.title}</h2><p>{detail.body || detail.text}</p></div></>}</dialog>;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [publicGroups, setPublicGroups] = useState(null);
  const [publications, setPublications] = useState(null);
  const [publicationsError, setPublicationsError] = useState(false);
  const [selectedHighlights, setSelectedHighlights] = useState([]);
  useEffect(() => {
    const controller = new AbortController();
    async function loadHighlights() {
      const articles = [];
      let page = 1;
      let data;
      do {
        data = await api.getFeaturedArticles(page++, { signal: controller.signal });
        articles.push(...data.results);
      } while (data.next && !controller.signal.aborted);
      if (!controller.signal.aborted) setSelectedHighlights(articles.map((article) => ({
        ...article, category: article.group_name, image: article.cover_url || goldenBible,
        alt: article.cover_alt, description: article.excerpt, href: `/conteudos/${article.id}`,
      })));
    }
    loadHighlights().catch(() => { /* A apresentação institucional permanece disponível. */ });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    api.getArticles(1, "", { signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) setPublications(data.results.map((article) => ({ ...article, category: article.group_name, image: article.cover_url || goldenBible, alt: article.cover_alt })));
    }).catch(() => { if (!controller.signal.aborted) setPublicationsError(true); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    api.getGroups(1, { signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) setPublicGroups(data.results);
    }).catch(() => { /* Os atalhos institucionais continuam disponíveis sem a API. */ });
    return () => controller.abort();
  }, []);
  const groupSlugs = [null, "rhematerapia", "restaura-me", "promocao-a-vida", "grupo-cura"];
  const displayedGroups = publicGroups === null
    ? groups.map((group, index) => ({ ...group, href: groupSlugs[index] ? `/grupos/${groupSlugs[index]}` : "/grupos.html" }))
    : [{ ...groups[0], href: "/grupos.html" }, ...publicGroups.slice(0, 4).map((group) => ({ title: group.name, image: groupCover(group), href: `/grupos/${group.slug}` }))];
  const [slide, setSlide] = useState(0);
  const [detail, setDetail] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const slides = selectedHighlights.length ? selectedHighlights : [
    { ...stories[0], title: "A Missão do Cristão no Mundo de Hoje", image: sunriseSilhouette, description: "Como viver o Evangelho com coerência, esperança e testemunho na sociedade atual." },
    { ...stories[0], image: sunsetBible },
    { ...stories[1], image: maryAtDusk },
    { title: "Um lugar para acolher e caminhar juntos", category: "Nossa comunidade", image: crossAtDawn, description: "Conheça a comunidade e encontre o seu lugar nessa missão.", body: stories[0].body },
  ];
  const currentSlide = slide % slides.length;
  const featured = slides[currentSlide];
  const normalize = (text) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const filtered = (publications || []).filter((story) => normalize(`${story.title} ${story.category}`).includes(normalize(query)));
  const about = (id) => setDetail(id === "fundadores" ? stories[2] : { ...stories[0], title: "Quem Somos" });
  const pendingSubscription = () => { navigate("/assinatura.html"); };
  const search = () => { setSearchOpen(true); document.getElementById("noticias")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" }); };
  return <div className="mag-home"><SiteLink className="skip-link" href="#conteudo">Pular para o conteúdo</SiteLink><Header onSearch={search} onAbout={about} /><main id="conteudo" tabIndex={-1}>
    <section id="inicio" className="mag-hero"><div className="mag-container mag-hero-grid"><div className="mag-identity"><img src={goldenLogos} alt="" /><h1><span>Comunidade</span><br />Unidos em Cristo</h1><div className="mag-ribbon">Comunidade Online Católica</div><p>Formação <b>•</b> Espiritualidade <b>•</b> Comunhão <b>•</b> Missão</p></div><div className="mag-hero-copy"><h2>Fé, Formação<br />e Vida em<br /> Comunidade</h2><p>Artigos, reflexões, colunas,<br className="desktop-break" /> vídeos e conteúdos exclusivos<br className="desktop-break" /> para fortalecer a sua caminhada<br className="desktop-break" /> com Cristo.</p><div className="hero-actions"><SiteLink href="#associacao" className="mag-button red">Assine a Comunidade Online <span>→</span></SiteLink></div></div><div className="mag-hero-picture"><img src={heroBible} alt="Bíblia aberta com cruz e vela" /></div></div></section>
    <section className="mag-feature" aria-label="Destaques da comunidade"><div className="mag-container mag-feature-frame"><article className="mag-feature-card" aria-roledescription="slide" aria-label={`${currentSlide + 1} de ${slides.length}`}><img key={featured.image} src={featured.image} alt={featured.alt || ""} /><div className="mag-feature-shade" /><div className="mag-feature-copy" aria-live="polite"><span className="mag-tag">Em destaque</span><h2>{featured.title}</h2><p>{featured.description}</p>{featured.href ? <SiteLink className="mag-button pale" href={featured.href}>Ler conteúdo <span>→</span></SiteLink> : <button className="mag-button pale" onClick={() => setDetail(featured)}>Saiba mais <span>→</span></button>}</div><div className="mag-dots">{slides.map((item, i) => <button key={item.id || item.title} aria-label={`Ver destaque ${i + 1}`} aria-pressed={currentSlide === i} className={currentSlide === i ? "selected" : ""} onClick={() => setSlide(i)} />)}</div></article><button className="mag-carousel-arrow previous" aria-label="Destaque anterior" onClick={() => setSlide((slide + slides.length - 1) % slides.length)}>‹</button><button className="mag-carousel-arrow next" aria-label="Próximo destaque" onClick={() => setSlide((slide + 1) % slides.length)}>›</button></div></section>
    <div className="mag-container mag-body"><nav className="mag-shortcuts" aria-label="Explore a comunidade online">{[["book", "Artigos", "Editorial", "#noticias"], ["users", "Grupos", "Temáticos", "#como-atuamos"], ["user", "Facilitadores", "Convidados", "/facilitadores.html"], ["calendar", "Agenda", "de Eventos", "#agenda"], ["play", "Vídeos", "e Formações", "video"], ["layers", "Edições", "da Comunidade Online", "#associacao"]].map(([icon, line1, line2, href]) => href === "video" ? <SiteLink key={icon} href="/comunidade-online.html"><Icon name={icon} /><span>{line1}<br />{line2}</span></SiteLink> : <SiteLink key={icon} href={href} onClick={() => { if (href === "#fundadores") about("fundadores"); }}><Icon name={icon} /><span>{line1}<br />{line2}</span></SiteLink>)}</nav>
      <section id="noticias" className="mag-publications"><div className="mag-section-heading"><h2>Últimas Publicações</h2><SiteLink className="mag-text-link" href="/comunidade-online.html">Ver todos os conteúdos <span>→</span></SiteLink></div>{searchOpen && <div className="mag-search-panel"><label htmlFor="mag-search">Buscar conteúdo</label><div><Icon name="search" /><input id="mag-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Busque por título ou tema" autoFocus /><button aria-label="Fechar busca" onClick={() => { setSearchOpen(false); setQuery(""); }}>×</button></div></div>}<div className="mag-publication-grid">{filtered.slice(0, 3).map((story) => <article className="mag-publication" key={story.id}><SiteLink href={`/conteudos/${story.id}`}><div className="mag-publication-image"><img src={story.image} alt={story.alt || "Foto de capa do conteúdo"} loading="lazy" /><span className="mag-tag">{story.category}</span></div><div className="mag-publication-copy"><h3>{story.title}</h3><div className="mag-publication-meta"><span><Icon name="book" /> {story.author_name}</span><span>Leia mais →</span></div></div></SiteLink></article>)}</div>{filtered.length === 0 && <p className="mag-empty" role="status">{publicationsError ? "Os conteúdos estão temporariamente indisponíveis." : publications === null ? "Carregando publicações…" : query ? "Nenhum conteúdo encontrado. Experimente outro tema." : "Os primeiros conteúdos da comunidade serão publicados aqui em breve."}</p>}</section>
      <section id="como-atuamos" className="mag-groups"><div className="mag-groups-intro"><h2><Icon name="users" /> Nossos Grupos</h2><p>Participe dos grupos de formação, oração e serviço da nossa comunidade.</p><SiteLink className="mag-button red" href="/grupos.html">Conheça os Grupos</SiteLink></div><div className="mag-group-grid">{displayedGroups.map((group) => <SiteLink className="mag-group" key={group.href} href={group.href}><img src={group.image} alt="" loading="lazy" /><span>{group.title}</span></SiteLink>)}</div></section>
      <HomeMural /><div className="mag-lower-grid"><section id="associacao" className="mag-subscription"><div className="mag-subscription-copy"><h2>Comunidade Online<br />Unidos em Cristo</h2><p>Conteúdos exclusivos, facilitadores,<br />formação e muito mais.</p><div className="mag-price"><small>Assinatura mensal</small><strong>R$ 48,20</strong></div><button className="mag-button gold" onClick={pendingSubscription}>Assine Agora <span>→</span></button></div><div className="mag-devices"><img src={communityMockup} alt="Comunidade Unidos em Cristo no tablet e no celular" loading="lazy" /></div></section><HomeEvents /></div>
      <section className="mag-newsletter" aria-labelledby="newsletter-title"><Icon name="mail" /><div><h2 id="newsletter-title">Receba nossas novidades</h2><p>Agenda e novidades da comunidade. Grátis, mesmo sem assinatura.</p></div><NewsletterSignup /></section>
    </div></main><footer id="contato" className="mag-footer"><div className="mag-container mag-footer-grid"><div className="mag-footer-brand"><SiteLink className="mag-brand" href="#inicio"><img src={logo} alt="" /><span>Comunidade<br />Unidos em Cristo</span></SiteLink></div><div className="footer-links"><h2>Institucional</h2><button id="quem-somos" onClick={() => about("quem-somos")}>Quem Somos</button><SiteLink id="fundadores" href="/fundadores.html">Fundadores</SiteLink><SiteLink href="/fundadores.html">Nossa História</SiteLink><SiteLink href="/termos.html">Termos de uso</SiteLink></div><div className="footer-links"><h2>CUC</h2><SiteLink href="/mural.html">Mural da Comunidade</SiteLink><SiteLink href="#noticias">Artigos</SiteLink><SiteLink href="/facilitadores.html">Facilitadores</SiteLink><SiteLink href="#como-atuamos">Grupos</SiteLink></div><div className="footer-links"><h2>Ajuda</h2><SiteLink href="/area-associado.html">Área do Associado</SiteLink><SiteLink href="/minha-assinatura.html">Assinatura e cancelamento</SiteLink><button onClick={pendingSubscription}>Perguntas Frequentes</button><a href="https://wa.me/5511986302883" target="_blank" rel="noopener noreferrer">Fale Conosco</a><SiteLink href="/politica-privacidade.html">Privacidade</SiteLink><SiteLink href="#contato">Contato</SiteLink></div><div className="mag-social-column"><h2>Siga-nos</h2><div className="mag-social social"><a href="https://www.youtube.com/" aria-label="YouTube" target="_blank" rel="noopener noreferrer"><SocialIcon name="youtube" /></a><a href="https://www.instagram.com/cuc_unidosemcristo/" aria-label="Instagram" target="_blank" rel="noopener noreferrer"><SocialIcon name="instagram" /></a><a href="https://www.facebook.com/ComUnidosEmCristo" aria-label="Facebook" target="_blank" rel="noopener noreferrer"><SocialIcon name="facebook" /></a></div></div></div><div className="mag-copyright"><p>© {new Date().getFullYear()} Comunidade Unidos em Cristo. Todos os direitos reservados.</p><p>Desenvolvido por <a href="https://clica.bio/fabiomedeiroswebsite" target="_blank" rel="noopener noreferrer">@fabiomedeirosdev</a></p><p><a href="https://wa.me/5511985071279" target="_blank" rel="noopener noreferrer" aria-label="Conversar pelo WhatsApp: 11 98507 1279">11 98507 1279</a></p></div></footer><DetailDialog detail={detail} onClose={() => setDetail(null)} /></div>;
}
