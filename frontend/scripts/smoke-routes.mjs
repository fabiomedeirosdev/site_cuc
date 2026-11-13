import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { createServer } from "vite";

const cases = [
  ["/fundadores.html", "Nossos fundadores"],
  ["/painel/fundadores", "Verificando seu acesso"],
  ["/", "Comunidade"],
  ["/index.html", "Quem Somos"],
  ["/login.html", "Bem-vindo de volta"],
  ["/cadastro.html", "Conclua seu cadastro"],
  ["/assinatura.html", "Assine a Comunidade Online"],
  ["/minha-assinatura.html", "Verificando seu acesso"],
  ["/agenda.html", "Agenda da Comunidade"],
  ["/mural.html", "Mural da Comunidade"],
  ["/newsletter.html", "Confirmar newsletter"],
  ["/gestao-comunicacao.html", "Verificando seu acesso"],
  ["/recuperar-senha.html", "Recupere seu acesso"],
  ["/area-associado.html", "Verificando seu acesso"],
  ["/perfil.html", "Verificando seu acesso"],
  ["/comunidade-online.html", "Comunidade Online"],
  ["/conteudos/1", "Conteúdo da comunidade"],
  ["/meus-conteudos.html", "Verificando seu acesso"],
  ["/editor/novo", "Verificando seu acesso"],
  ["/grupos.html", "Nossos Grupos"],
  ["/grupos/rhematerapia", "Grupo da comunidade"],
  ["/facilitadores.html", "Facilitadores"],
  ["/gestao-grupos.html", "Verificando seu acesso"],
  ["/acesso-negado.html", "Acesso restrito"],
  ["/link-expirado.html", "Link indisponível"],
  ["/pagamento-sucesso.html", "Aguarde a confirmação do pagamento"],
  ["/pagamento-pendente.html", "Pagamento em análise"],
  ["/pagamento-cancelado.html", "Pagamento não concluído"],
  ["/politica-privacidade.html", "Política de privacidade"],
  ["/termos.html", "Termos de uso"],
];

const vite = await createServer({ server: { middlewareMode: true }, appType: "custom" });

try {
  const { AppRoutes } = await vite.ssrLoadModule("/src/App.jsx");
  for (const [path, expectedText] of cases) {
    const tree = React.createElement(
      MemoryRouter,
      { initialEntries: [path] },
      React.createElement(AppRoutes),
    );
    const markup = renderToStaticMarkup(tree);
    assert.ok(markup.includes(expectedText), `${path} did not render “${expectedText}”`);
    console.log(`PASS ${path}`);
  }
} finally {
  await vite.close();
}
