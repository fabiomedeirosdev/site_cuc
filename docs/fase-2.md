# Fase 2 — migração institucional para React

## Escopo

A aplicação React mantém as URLs `.html` e o acesso pela raiz `/`. O site estático,
o CSS original, o JavaScript original, as fotografias e os logotipos permanecem no
repositório. As correções de layout são locais ao React, em `frontend/src/app.css`.
Nenhuma configuração de hospedagem ou produção foi modificada.

| Página preservada | Componente React |
| --- | --- |
| `index.html` e `/` | `HomePage.jsx` |
| `login.html` | `LoginPage` em `AccessPages.jsx` |
| `cadastro.html` | `RegisterPage` em `AccessPages.jsx` |
| `recuperar-senha.html` | `RecoverPasswordPage` em `AccessPages.jsx` |
| `area-associado.html` | `MemberPage` em `UtilityPages.jsx` |
| `acesso-negado.html` | `AccessDeniedPage` em `UtilityPages.jsx` |
| `link-expirado.html` | `ExpiredLinkPage` em `UtilityPages.jsx` |
| `pagamento-sucesso.html` | `PaymentPage` em `UtilityPages.jsx` |
| `pagamento-pendente.html` | `PaymentPage` em `UtilityPages.jsx` |
| `pagamento-cancelado.html` | `PaymentPage` em `UtilityPages.jsx` |
| `politica-privacidade.html` | `PrivacyPage` em `LegalPages.jsx` |
| `termos.html` | `TermsPage` em `LegalPages.jsx` |

## Ajustes realizados

- Restaurados os ícones, o símbolo do rodapé e os textos da página inicial conforme
  o HTML existente. Mantidos cores, fotografias, nomes e valores institucionais.
- Navegação interna com React Router, preservando as URLs, as âncoras e o botão
  Voltar do navegador. As seções ficam abaixo do cabeçalho fixo ao navegar.
- Menu móvel com estado acessível, fechamento por Escape, seleção, clique externo
  e mudança para desktop. Navegação ativa identifica a seção atual.
- Atalho de teclado para pular ao conteúdo; foco transferido após navegação sem
  retirar o primeiro Tab do usuário no carregamento inicial.
- Retorno visível dos formulários ainda sem autenticação. Os campos mantêm os tipos,
  requisitos, preenchimento automático e validação nativa originais. Dados digitados
  não são enviados nem persistidos nesta fase.
- Botões de contribuição informam indisponibilidade sem navegar para cobrança ou
  WhatsApp. Os valores de R$ 35, R$ 65 e R$ 120 são os planos institucionais legados;
  não definem a assinatura da comunidade online, de R$ 48,20/mês, prevista na Fase 6.
- Instagram, Facebook e WhatsApp usam somente os endereços registrados em
  `cuc_site_estrutura.txt`. Os testes verificam os destinos sem acessar esses serviços.

## Imagens e vídeo

O HTML antigo aponta para seis caminhos inexistentes. A versão React usa arquivos
institucionais já presentes, sem gerar fotografias ou inventar pessoas:

| Referência antiga ausente | Arquivo disponível aproveitado |
| --- | --- |
| `assets/logo/hero-irh.png` | `assets/logo/rhematerapia.png` |
| `assets/video-thumb.png` | `assets/images/cuc_comundad_unidos_em_cristo.png` |
| `assets/quem-somos.jpg` | `assets/images/equipe_cuc.JPG` |
| `assets/fundadores-1.jpg` e `assets/fundadores-2.jpg` | `assets/images/fundadores_comunidade_cuc.png` |
| `assets/sede.jpg` | `assets/images/sede_cuc.png` |

A foto disponível dos fundadores é exibida uma vez. O segundo arquivo antigo não
foi recriado. Os arquivos de mídia existentes não foram modificados.

A versão React anterior continha um vídeo incorporado sem referência no HTML ou
na documentação institucional. Essa incorporação foi removida. O botão mantém a
capa institucional e informa que o vídeo ainda está indisponível. A URL oficial
do vídeo e a do canal YouTube continuam pendentes; o link genérico do YouTube foi
preservado como no HTML original.

## Validação reproduzível

```powershell
cd frontend
npm test
npm run test:routes
npm run test:browser
npm run build
```

Os testes de navegador usam Playwright com o Microsoft Edge já instalado, em modo
headless. O Vite é iniciado e encerrado pelo executor. Não é necessário iniciar
Django ou PostgreSQL nesta fase. A porta 5173 deve estar livre.

A suíte contém 20 verificações em cada largura: 1440, 1024, 390 e 320 pixels.
Compara textos, títulos, campos, imagens carregadas e ausência de rolagem horizontal
nas 12 páginas. Também valida rotas, âncoras, navegação sem recarregamento, foco,
menu móvel, formulários e botões ainda sem integração.

As 11 páginas secundárias são renderizadas separadamente a partir dos HTMLs preservados,
usando o mesmo CSS. As capturas completas são comparadas byte a byte. A inicial
tem comparação de conteúdo e identidade visual, inspeção das capturas e validação
de imagens, pois as seis referências ausentes inviabilizam comparação idêntica com
o HTML antigo sem corrigir o original.

Requisições externas são bloqueadas nos testes, inclusive Google Fonts. Assim, a
comparação usa as fontes alternativas já definidas no CSS em ambas as versões.
Os links de fontes originais permanecem na aplicação. A conferência com fontes
remotas disponíveis e em outros navegadores permanece uma limitação desta rodada.

Capturas: `.local/phase2/screenshots/`. Relatório da última execução:
`.local/phase2/report/index.html`. Esses artefatos são locais e ignorados pelo Git.
Os hashes dos HTMLs, CSS e JavaScript originais foram registrados antes das edições
para conferir sua preservação ao final.

## Resultados — 11/11/2026

- 80 verificações no Edge aprovadas: 20 em cada uma das quatro larguras.
- 44 comparações visuais idênticas com os HTMLs das 11 páginas secundárias.
- 13 verificações de renderização das rotas e 4 testes do cliente da API aprovados.
- Build final Vite aprovado.
- Preservação dos 12 HTMLs originais, `css/style.css` e `js/script.js` confirmada
  por SHA-256, em relação ao início desta etapa.
- A revisão adicional de navegação identificou e corrigiu o destaque de Contato
  ao chegar ao rodapé. Também foi preservada a rolagem suave para quem não solicita
  movimento reduzido. A revalidação cobre links diretos, teclado e menu móvel.

Os preços, os textos legais e os conteúdos institucionais não foram redefinidos.
A execução fica restrita ao ambiente local e o executor encerra seus servidores.

## Próxima fase e decisões preservadas

A Fase 3 implementará autenticação real, usuários, perfis e permissões. A área do
associado e as páginas de pagamento são somente apresentações herdadas do site;
não comprovam login, autorização ou pagamento. Nenhum conteúdo exclusivo real
deve ser colocado nessas páginas antes das fases de proteção.

As páginas legais mantêm integralmente os textos existentes, inclusive o aviso de
conteúdo demonstrativo e revisão antes da publicação. A migração não cria textos
legais oficiais nem define políticas comerciais. Não foram adicionados conteúdos
editoriais, comentários de assinantes, grupos ou serviços financeiros.
