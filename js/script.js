/* =========================================================
   COMUNIDADE UNIDOS EM CRISTO
   SCRIPT.JS
   ========================================================= */


/* =========================================================
   MENU MOBILE
   ========================================================= */

const mobileToggle = document.querySelector(".mobile-toggle");
const menu = document.querySelector(".menu");

if (mobileToggle && menu) {

    mobileToggle.addEventListener("click", () => {

        const menuAberto = menu.classList.toggle("menu-aberto");

        mobileToggle.setAttribute(
            "aria-expanded",
            menuAberto
        );

    });

}


/* =========================================================
   FECHAR MENU MOBILE AO CLICAR EM UM LINK
   ========================================================= */

const menuLinks = document.querySelectorAll(".menu a");

menuLinks.forEach((link) => {

    link.addEventListener("click", () => {

        menu.classList.remove("menu-aberto");

        mobileToggle?.setAttribute(
            "aria-expanded",
            "false"
        );

    });

});


/* =========================================================
   MENU ATIVO CONFORME A SEÇÃO
   ========================================================= */

const sections = document.querySelectorAll(
    "main section[id]"
);

const navLinks = document.querySelectorAll(
    ".menu a[href^='#']"
);

const observerOptions = {
    root: null,
    rootMargin: "-35% 0px -55% 0px",
    threshold: 0
};

const sectionObserver = new IntersectionObserver(
    (entries) => {

        entries.forEach((entry) => {

            if (!entry.isIntersecting) {
                return;
            }

            const sectionId = entry.target.id;

            navLinks.forEach((link) => {

                link.classList.remove("active");

                if (
                    link.getAttribute("href") ===
                    `#${sectionId}`
                ) {

                    link.classList.add("active");

                }

            });

        });

    },
    observerOptions
);

sections.forEach((section) => {

    sectionObserver.observe(section);

});


/* =========================================================
   SCROLL SUAVE
   ========================================================= */

document.querySelectorAll(
    'a[href^="#"]'
).forEach((link) => {

    link.addEventListener("click", (event) => {

        const destino = link.getAttribute("href");

        if (
            !destino ||
            destino === "#"
        ) {
            return;
        }

        const elemento = document.querySelector(destino);

        if (!elemento) {
            return;
        }

        event.preventDefault();

        elemento.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    });

});


/* =========================================================
   BOTÕES DE CHECKOUT
   =========================================================

   IMPORTANTE:

   Por enquanto os botões estão com:

       href="#"

   Quando o sistema de pagamento estiver definido,
   vamos colocar aqui as URLs reais dos checkouts.

   Cada botão possui um identificador:

       associado-c
       associado-b
       associado-a
       pix-avulso
       outros-valores

   ========================================================= */

const checkoutLinks = {

    "associado-c": "#",

    "associado-b": "#",

    "associado-a": "#",

    "pix-avulso": "#",

    "outros-valores": "#"

};


const checkoutButtons = document.querySelectorAll(
    "[data-checkout]"
);


checkoutButtons.forEach((button) => {

    button.addEventListener("click", (event) => {

        const tipoCheckout =
            button.dataset.checkout;

        const url =
            checkoutLinks[tipoCheckout];

        /*
         * Enquanto a URL ainda não estiver cadastrada,
         * não redireciona.
         */

        if (
            !url ||
            url === "#"
        ) {

            if (
                button.getAttribute("href") &&
                button.getAttribute("href") !== "#"
            ) {
                return;
            }

            event.preventDefault();

            console.log(
                "Checkout ainda não configurado:",
                tipoCheckout
            );

            return;

        }

        /*
         * Quando colocarmos a URL verdadeira,
         * o usuário será enviado para o checkout.
         */

        window.location.href = url;

    });

});


/* =========================================================
   BOTÃO DO VÍDEO
   =========================================================

   Por enquanto o vídeo utiliza a imagem de apresentação.

   Depois podemos colocar:

   - YouTube
   - Vimeo
   - vídeo próprio
   - player incorporado

   ========================================================= */

const videoPreview =
    document.querySelector(".video-preview");

if (videoPreview) {

    videoPreview.addEventListener(
        "click",
        () => {
            const videoFrame =
                videoPreview.nextElementSibling;

            videoPreview.hidden = true;
            videoFrame.hidden = false;

            videoFrame.src += "?autoplay=1";

        }
    );

}


/* =========================================================
   ANO AUTOMÁTICO DO COPYRIGHT
   ========================================================= */

const copyright =
    document.querySelector(".copyright");

if (copyright) {

    const anoAtual =
        new Date().getFullYear();

    copyright.innerHTML =
        `© ${anoAtual} Comunidade Unidos em Cristo. Todos os direitos reservados - Desenvolvido por Fabio Medeiros.`;

}


/* =========================================================
   EFEITO NO HEADER AO ROLAR
   ========================================================= */

const header =
    document.querySelector(".site-header");


window.addEventListener(
    "scroll",
    () => {

        if (!header) {
            return;
        }

        if (window.scrollY > 50) {

            header.classList.add(
                "header-scrolled"
            );

        } else {

            header.classList.remove(
                "header-scrolled"
            );

        }

    }
);


/* =========================================================
   LOG DE INICIALIZAÇÃO
   ========================================================= */

console.log(
    "Comunidade Unidos em Cristo — site carregado."
);