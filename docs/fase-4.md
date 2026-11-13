# Fase 4 — grupos temáticos e equipe editorial

O catálogo de grupos, suas páginas individuais, o diretório de facilitadores e a
gestão dos vínculos estão conectados ao Django/PostgreSQL. A home mantém suas
imagens e lê os quatro primeiros grupos ativos do catálogo. O atalho inicial
“Formação e Palavra” abre o catálogo completo, sem criar um quinto grupo fictício.
Se a API estiver indisponível, os atalhos institucionais continuam navegáveis;
o catálogo informa a falha e permite tentar novamente.

## Modelo e cadastros iniciais

`editorial.EditorialGroup` guarda nome, slug único, descrição, imagem do acervo,
ordem e estado ativo. `editorial.Membership` relaciona uma conta existente a um
grupo com função de coordenador ou facilitador, apresentação e visibilidade pública.
O banco impede vínculos duplicados e funções inválidas. Uma conta pode participar
de vários grupos, com funções diferentes em cada um.

A migração prepara apenas os quatro trabalhos descritos no site institucional:
Rhematerapia, Restaura-me, Promoção à Vida e Grupo C.U.R.A. Não cria contas,
coordenadores, facilitadores, assinaturas ou conteúdos de demonstração.

## Escopo das permissões

| Pessoa | Operações disponíveis |
| --- | --- |
| Visitante | Consultar grupos ativos e apresentações explicitamente públicas |
| Assinante ou facilitador | Consultar o catálogo; sem gestão de equipes |
| Coordenador vinculado | Cadastrar acessos e vínculos de facilitadores, editar apresentações e remover esses vínculos nos grupos ativos que coordena; gerenciar os conteúdos desses grupos |
| Administrador (superusuário) | Cadastrar grupos no Django Admin, atribuir/remover coordenadores e gerir vínculos inclusive em grupos inativos |

Os grupos globais `Coordenadores` e `Facilitadores` da Fase 3 não concedem escopo
sobre nenhum grupo temático. A autorização depende do vínculo no grupo e é
verificada a cada requisição. Não há promoção de privilégios de conta nem
concessão automática de `is_staff`, `is_superuser` ou permissões de publicação.
O cadastro de grupos e vínculos no Django Admin exige superusuário, mesmo que
um funcionário receba permissões Django genéricas sobre esses modelos.

Conforme a regra atual, o coordenador cadastra e remove facilitadores dos seus grupos.
Somente o administrador atribui coordenadores. Coordenadores não podem promover facilitadores a coordenadores, alterar coordenadores, remover o
próprio vínculo de coordenação ou modificar vínculos de outro grupo. Remover um
vínculo preserva a conta. Desativar o grupo ou remover a coordenação revoga a
gestão na próxima requisição.

## Privacidade e segurança

Novos vínculos começam privados. Para apresentar uma pessoa no site, a gestão
precisa habilitar “Exibir nome e apresentação na página pública”. E-mails,
usernames e identificadores de conta não aparecem no catálogo nem nas equipes.
Sem nome preenchido, aparece “Integrante da comunidade”. Perfis de contas
inativas e grupos inativos ficam fora da consulta pública.

A inclusão exige o e-mail exato de uma conta ativa existente; não existe busca
aberta de contas. A API não cria usuários. Escritas usam sessão e CSRF, herdam os
limites da API de conta e retornam `Cache-Control: no-store`. Alterações de vínculos
são transacionais; o grupo é bloqueado durante as operações para serializar as
escritas da API. Biografias são texto simples, sem HTML executável.

## Rotas

| Rota | Uso |
| --- | --- |
| `/grupos.html` | Catálogo público paginado |
| `/grupos/:slug` | Descrição do grupo, apresentações públicas e contato conhecido da comunidade |
| `/facilitadores.html` | Facilitadores com apresentação pública, por vínculo de grupo |
| `/gestao-grupos.html` | Gestão autenticada; sem escopo, informa que não há grupos disponíveis |

A área do associado mostra “Gerenciar meus grupos” para contas com escopo de
gestão. O login preserva o destino interno da gestão. Os links de facilitadores da
home abrem o diretório; fundadores continuam na apresentação institucional.

| Método e API | Uso |
| --- | --- |
| `GET /api/groups` | Grupos ativos, paginados |
| `GET /api/groups/:slug` | Grupo ativo e apresentações públicas |
| `GET /api/columnists` | Facilitadores públicos, paginados |
| `GET /api/editorial/groups` | Grupos que a conta pode gerenciar |
| `GET /api/editorial/groups/:slug/members` | Vínculos do grupo autorizado |
| `POST /api/editorial/groups/:slug/members` | Vincular conta existente por e-mail |
| `PATCH /api/editorial/groups/:slug/members/:id` | Alterar função permitida, apresentação e visibilidade |
| `DELETE /api/editorial/groups/:slug/members/:id` | Remover somente o vínculo |

O perfil da própria conta informa `can_manage_editorial_groups` e
`editorial_groups`. As permissões de conteúdo exclusivo continuam fechadas.

## Administração local

Com o PostgreSQL iniciado pelo script existente, aplique as migrações:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

O React continua em `http://127.0.0.1:5173`. Para preparar um administrador local,
use `manage.py createsuperuser` interativamente. Em
`http://127.0.0.1:8000/admin/`, cadastre as contas necessárias e atribua os vínculos
em “Grupos editoriais / Vínculos editoriais”. Nenhum administrador permanente foi
criado por esta implementação. O administrador pode escolher entre as imagens
de Bíblia, coração, oração, família e sede, já presentes no acervo.

## Verificação

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py test apps.editorial.browser_tests --noinput
cd ../../frontend
npm test
npm run test:routes
npm run build
```

A integração editorial usa banco temporário, contas `.invalid`, Django em porta
efêmera e Vite na porta **5175**, sem encerrar o desenvolvimento na porta 5173.
O próprio teste prepara e remove os dados. A configuração de teste permite CSRF
na origem 5175 somente durante essa integração; não altera a configuração normal.
Serviços externos são bloqueados no Edge. `npm run test:editorial` exige esse
executor Django para evitar gravações sobre o banco de desenvolvimento.

Resultados da implementação: 47 testes Django, 7 testes do cliente da API e 18
verificações de renderização de rotas aprovados. A integração real aprovou 12
cenários no Edge em 1440, 1024, 390 e 320 px, incluindo consulta pública, ausência
de escopo, escrita pelo coordenador, apresentação pública, remoção de vínculo e
atribuição de coordenador pelo administrador. Build e conferência de migrações
aprovados. Artefatos locais: `.local/phase4/report/` e
`.local/phase4/screenshots/`.

## Próxima fase

A [Fase 5 — Comunidade Online](fase-5.md) implementa artigos, editor de conteúdo,
fotos de capa e vídeos vinculados a esses grupos. Esta etapa não libera comentários ou publicação por assinantes,
não apresenta conteúdo fictício como publicado e não ativa cobranças, e-mails ou
assinaturas. O acesso exclusivo depende da Fase 6.
