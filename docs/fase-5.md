# Fase 5 — Comunidade Online, artigos e vídeos

A Comunidade Online possui catálogo público, páginas de leitura e um editor para
facilitadores autorizados pela coordenação. Título, resumo, texto, foto de capa,
descrição da foto, grupo e vídeo são campos separados. Não foram criados conteúdos
ou contas permanentes de demonstração.

## Regra de autorização confirmada

O coordenador pode cadastrar, autorizar, editar a apresentação e remover os
facilitadores dos grupos ativos que coordena. Pode vincular uma conta existente
ou criar um acesso com nome, e-mail e senha inicial. A senha é validada e gravada
com hash; a conta criada não recebe privilégios técnicos. Não é enviado e-mail
automático. A pessoa pode alterar sua senha na área de perfil.

Somente o administrador atribui ou altera coordenadores e configura a estrutura
dos grupos. A coordenação não pode conceder acesso administrativo, alterar outro
coordenador ou atuar em grupos aos quais não foi vinculada.

A criação exige um vínculo de **facilitador ou coordenador** em um grupo ativo.
Pertencer apenas ao grupo global de autenticação “Facilitadores” não libera o editor.
Cada facilitador cria, edita, publica, retira de publicação e exclui seus próprios
conteúdos nos grupos aos quais está autorizado. Não pode editar conteúdos de outro
autor, mesmo dentro do mesmo grupo. O coordenador pode revisar, editar, publicar,
retirar de publicação e excluir conteúdos dos facilitadores dos grupos que coordena,
incluindo rascunhos. A autoria original é preservada, e a capa atual continua
utilizável pelo facilitador mesmo quando foi substituída durante a revisão.
O administrador pode gerenciar todos os conteúdos. Autoria e privilégios de conta
não podem ser enviados pelo formulário.

Remover o vínculo, desativar a conta ou desativar o grupo revoga a autorização e
retira as publicações daquele escopo do catálogo público. Remover o vínculo não
apaga os conteúdos; o coordenador do grupo e o administrador continuam podendo administrá-los.

## Editor e publicação

- Texto de até **200.000 caracteres**, título de até 200 e resumo de até 500.
- Barra de formatação com negrito, itálico, subtítulo, lista, citação e link.
- Texto salvo em Markdown, com prévia e renderização segura, sem execução de HTML.
- Foto de capa com upload próprio e descrição acessível; ambos exigidos para publicar.
- Rascunho e publicação com ações explícitas; exclusão pede confirmação na interface.
- Link do YouTube separado do texto, com prévia do player e reprodução incorporada
  na página de leitura. Aceita URLs HTTPS de vídeo, links curtos, Shorts e lives.
- Lista “Meus Conteúdos” com botões de criar, editar, ver publicação e excluir.

Os últimos conteúdos publicados abastecem automaticamente a home com título,
foto de capa, grupo e autoria. Rascunhos e conteúdos excluídos não aparecem ali.
O catálogo possui busca por título e paginação. Enquanto não houver publicação,
a home informa que os primeiros conteúdos serão disponibilizados, sem apresentar
artigos de demonstração como se já estivessem publicados.

A nomenclatura da interface e da documentação foi uniformizada para
**Comunidade Online**. As artes fornecidas pelo usuário são preservadas. O rodapé
da home apresenta somente YouTube, Instagram e Facebook, com ícones SVG próprios;
o contato por WhatsApp permanece no link “Fale Conosco”.

## Capas e vídeos

As fotos aceitam JPG, PNG ou WebP, com até 5 MB e 20 megapixels. O servidor verifica
a imagem, aplica a orientação, limita a dimensão a 2560 px e regrava em WebP com
nome aleatório. O arquivo original e seus metadados não são servidos. SVG e arquivos
inválidos são recusados. Um facilitador só pode atribuir capas que ele mesmo enviou;
o administrador pode escolher entre todas. As capas ficam em `.local/media/`, fora
do Git. Excluir um artigo preserva os arquivos enviados para possível reutilização.

O endereço do player é construído a partir do identificador de vídeo validado,
usando `https://www.youtube-nocookie.com/embed/`. HTML de iframe, JavaScript,
hosts externos, credenciais no endereço e portas inesperadas são recusados.
O servidor não acessa o link enviado para buscar metadados. A disponibilidade real
da reprodução depende das configurações do vídeo e do YouTube.

## Leitura pública e exclusiva

Conteúdos de visibilidade pública ficam disponíveis após publicação. A opção
“Exclusivo para assinantes” prepara a Fase 6: a capa, o título e o resumo podem
aparecer no catálogo, mas o texto e o endereço do player permanecem fechados,
inclusive para um assinante autenticado, até existir comprovação de assinatura.
O autor pode conferir o conteúdo pelo próprio editor. Não foram ativados
pagamentos, e-mails, comentários ou publicação por assinantes.

## Rotas

| Página | Uso |
| --- | --- |
| `/comunidade-online.html` | Catálogo de artigos e vídeos |
| `/conteudos/:id` | Leitura e player incorporado |
| `/meus-conteudos.html` | Lista de conteúdos do facilitador |
| `/editor/novo` | Criar conteúdo |
| `/editor/:id` | Editar conteúdo autorizado |

A área do associado mostra “Meus conteúdos” para contas com autorização de autoria.
O login preserva os destinos internos de edição e gestão.

| Método e API | Uso |
| --- | --- |
| `GET /api/articles` | Catálogo paginado, com busca `q` e filtro `group` |
| `GET /api/articles/:id` | Leitura de conteúdo publicado, com proteção de exclusividade |
| `GET /api/editorial/author-groups` | Grupos nos quais a conta pode criar |
| `GET /api/editorial/articles` | Conteúdos próprios; dos grupos coordenados para o coordenador; todos para o administrador |
| `POST /api/editorial/articles` | Criar conteúdo |
| `GET /api/editorial/articles/:id` | Abrir no editor autorizado |
| `PATCH /api/editorial/articles/:id` | Editar, publicar ou voltar a rascunho |
| `DELETE /api/editorial/articles/:id` | Excluir |
| `POST /api/editorial/covers` | Enviar capa, usando multipart e CSRF |

## Uso local

Atualize as dependências e aplique as migrações antes de iniciar o servidor:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
cd ../../frontend
npm ci
npm run dev
```

O Vite encaminha `/api` e `/media` para Django. O serviço de mídia incluído é local,
somente com `DEBUG` ativo; a hospedagem definitiva dos arquivos será configurada
na etapa de implantação. O editor utiliza `react-markdown` e `remark-gfm`; o backend
utiliza Pillow para validar e regravar imagens.

Em `/gestao-grupos.html`, o coordenador seleciona seu grupo e adiciona uma conta
existente ou marca “Criar acesso para um novo facilitador”. Depois do cadastro,
essa pessoa entra normalmente no site e abre “Meus conteúdos”. O coordenador usa
“Conteúdos dos grupos” para a revisão editorial. O cadastro pelo Django Admin
continua disponível para o administrador. Nenhuma conta administrativa foi criada automaticamente.

O diretório público usa `/facilitadores.html` e `/api/facilitators`. O endereço
antigo do diretório redireciona para o novo, e a API anterior é mantida como alias.
O nome do grupo de autenticação foi migrado para “Facilitadores”, preservando seus
vínculos. O identificador técnico `columnist` permanece no banco e na API por
compatibilidade; a interface apresenta somente “Facilitador”.

## Verificação — 12/11/2026

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py test apps.content.browser_tests --noinput
.\.venv\Scripts\python.exe manage.py test apps.editorial.browser_tests --noinput
cd ../../frontend
npm test
npm run test:routes
npm run build
```

Os testes da API cobrem autoria, escopo por grupo, exclusividade, CSRF, tamanhos,
upload, isolamento de capas, validação de links e remoção de publicações. A
integração da Fase 5 usa banco temporário, fotos temporárias e Vite na porta 5176,
sem encerrar o desenvolvimento na porta 5173. O teste prepara contas `.invalid`
e remove o banco e os arquivos ao encerrar. O player é simulado durante o teste
offline: são verificados o iframe, seu endereço permitido e sua presença na página;
essa verificação não afirma reprodução real de um vídeo externo.

Artefatos locais: `.local/phase5/report/` e `.local/phase5/screenshots/`.

Resultados: 70 testes Django, 7 testes do cliente, 22 rotas, 12 cenários reais do
editor no Edge, 16 cenários de gestão editorial e 12 verificações da
home aprovados. Conferência de migrações e build aprovados. O banco local segue
sem usuários, artigos ou capas de demonstração; os dados de teste foram removidos.
