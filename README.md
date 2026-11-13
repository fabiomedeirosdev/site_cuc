# Comunidade Unidos em Cristo — desenvolvimento local

Domínio definitivo: **https://rhemacuc.com.br**. A API de produção ficará no mesmo
domínio, em `/api/`, com desenvolvimento local preservado. Consulte
[configuração de produção](docs/producao-rhemacuc.md) para os modelos de ambiente,
proxy, HTTPS, fotos e links de e-mail.

A migração está isolada do site institucional original. Os HTMLs da raiz,
`css/`, `js/` e `assets/` continuam no lugar. O serviço anterior em `backend/app/`
também foi preservado; não é necessário iniciá-lo para usar a plataforma Django.

## Estrutura

- `frontend/`: React + Vite; reaproveita CSS e imagens institucionais.
- `backend/django_platform/`: Django + Django REST Framework e PostgreSQL.
- `scripts/local-postgres.ps1`: cria, inicia, consulta e encerra somente o banco local deste projeto.
- `.local/postgres/`: dados e log do PostgreSQL local, ignorados pelo Git.

## Preparar no Windows

Requisitos: Node.js 20.19+ ou 22.12+ (incluindo versões posteriores compatíveis),
Python 3.12+ e binários PostgreSQL 16+ instalados. Execute os comandos na raiz:

```powershell
cd frontend
npm ci
cd ../backend/django_platform
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ../..
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\local-postgres.ps1 start
```

O script procura os binários em `C:\Program Files\PostgreSQL`. Para outra instalação,
acrescente `-PostgresBin 'C:\caminho\bin'`. Ele cria o cluster em `.local/postgres/data`,
o banco `cuc_local` e um `.env` ignorado pelo Git com senha aleatória apenas de desenvolvimento.
Um `.env` já existente é preservado; se sua configuração não corresponder ao cluster,
o script interrompe a operação. Não use credenciais ou bancos de produção.

Inicie a API em um terminal:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Inicie o React em outro terminal:

```powershell
cd frontend
npm run dev
```

Abra `http://127.0.0.1:5173`. O Vite encaminha `/api` para Django em
`http://127.0.0.1:8000`; o PostgreSQL escuta somente `127.0.0.1:55432`.
O site estático original não depende desses servidores.

## Verificar

Com o PostgreSQL iniciado:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
cd ../../frontend
npm test
npm run test:routes
npm run build
```

Com Django também iniciado, `npm run test:api` valida a sequência
cliente JavaScript → proxy Vite → Django → PostgreSQL. O teste cria e encerra seu
próprio servidor Vite, sem ocupar a porta do desenvolvimento.

`GET /api/health` verifica a API sem depender do banco. `GET /api/ready` executa
uma consulta no PostgreSQL: responde 200 quando disponível ou 503 quando indisponível,
sem revelar detalhes da conexão. Os testes Django usam um banco PostgreSQL
temporário separado, `test_cuc_local`, criado e removido pelo executor de testes.

Para encerrar, use Ctrl+C nos terminais de Django e Vite e execute na raiz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\local-postgres.ps1 stop
```

O comando `status` consulta a instância. Os dados locais permanecem após `stop`.
Não há alteração de serviços do Windows, VPS, DNS ou hospedagem.

## Limites desta etapa

As fases locais de estrutura e migração institucional estão documentadas aqui e
em [Fase 2 — páginas React](docs/fase-2.md). A autenticação está descrita em
[Fase 3 — contas e permissões](docs/fase-3.md).
Novas views DRF exigem autenticação por padrão, com exceções explícitas para saúde.
Em desenvolvimento, e-mails usam memória do processo e cobranças ficam desativadas.
A [Fase 6 — assinatura e proteção](docs/fase-6.md) implementa o fluxo PagBank,
convite, validade e cancelamento. A ativação real depende de credenciais,
SMTP, dados do fornecedor e homologação. O backend anterior não deve ser iniciado
neste fluxo local.

Grupos editoriais, coordenadores e facilitadores estão implementados na Fase 4.
Artigos e vídeos estão implementados na Fase 5. Assinaturas de R$ 48,20/mês e
agenda pertencem às fases seguintes. Não há comentários
ou publicações livres de assinantes, nem dados editoriais inventados nesta fase.
Na Fase 3, o usuário Django existente foi preservado e estendido por perfil,
sem apagar tabelas ou criar contas reais. Permissões de leitura não comprovam
assinatura ativa; a liberação exclusiva permanece para a Fase 6.

## Validação da Fase 1 — 11/11/2026

- Dependências Python: `pip check` sem conflitos; `manage.py check` sem problemas.
- Migrações técnicas aplicadas no PostgreSQL 16 local.
- API: 8 testes aprovados, incluindo conexão PostgreSQL, resposta 503, CORS,
  exigência de autenticação e backend de e-mail em memória.
- Cliente JavaScript: 4 testes aprovados.
- Rotas React preexistentes: 13 verificações de renderização aprovadas.
- Integração HTTP: API, banco pelo proxy Vite e entrada React aprovados.
- Build Vite aprovado. Validação visual em navegador pendente para a Fase 2.

Os servidores usados na validação foram encerrados; siga os comandos acima para
retomar o ambiente. Nenhuma publicação ou integração externa foi executada.

## Fase 2 — páginas institucionais em React

As 12 páginas existentes mantêm conteúdo, cores, logotipos e fotografias do projeto,
com navegação interna em React e ajustes de menu, âncoras e teclado. Os arquivos
originais foram preservados e conferidos por SHA-256. Foram aprovadas 80 verificações
no Edge em quatro larguras, incluindo 44 comparações visuais das páginas secundárias,
além das 13 verificações de rotas, 4 testes do cliente da API e build final.

Execute `npm run test:browser` em `frontend/` para repetir os testes no Edge instalado,
com a porta 5173 livre. O executor bloqueia serviços externos e encerra seu Vite.
As fontes remotas ficam bloqueadas nos testes; a aplicação preserva seus links
originais. Veja o [relatório da Fase 2](docs/fase-2.md) para as imagens aproveitadas,
o vídeo oficial pendente, os limites da validação e os textos legais demonstrativos.

O resultado da Fase 2 está preservado como referência histórica. O login e a área
do associado evoluíram na Fase 3; cadastro e recuperação por e-mail continuam fechados.

## Fase 3 — autenticação e permissões

Login por e-mail e senha, sessão protegida, logout, perfil próprio e troca de senha
implementados. A área do associado exige sessão válida e apresenta os tipos de
consumo autorizados: artigos, vídeos do YouTube dentro do site e áudios. Assinantes
não comentam, criam, editam ou publicam conteúdo. Grupos de coordenadores e
facilitadores estão preparados, sem conceder permissões editoriais globais.

O banco de desenvolvimento permanece sem usuários reais ou de demonstração.
As migrações criam apenas perfis e metadados de permissão. A gestão administrativa
é feita pelo Django Admin local; consulte [Fase 3](docs/fase-3.md).

Para repetir a integração completa em um banco temporário separado:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py test apps.accounts.browser_tests --noinput
```

O PostgreSQL local precisa estar iniciado e a porta 5173 livre. O executor prepara
contas fictícias, inicia seus servidores e remove o banco de teste ao encerrar.
Nenhuma integração de e-mail, assinatura financeira ou player foi ativada nesta fase.

Validação da Fase 3: 28 testes Django, 7 do cliente, 14 rotas e 92 cenários no Edge
(20 de autenticação real e 72 de regressão institucional) aprovados, além do build.
O banco temporário e as contas fictícias foram removidos. O relatório detalha
os limites da validação e as funcionalidades previstas para as próximas fases.

## Fase 4 — grupos e equipe editorial

Catálogo público em `/grupos.html`, páginas individuais, diretório de facilitadores
e gestão de vínculos em `/gestao-grupos.html`. Coordenadores cadastram acessos e
vínculos de facilitadores, editam apresentações e removem vínculos nos seus grupos.
Somente o administrador atribui coordenadores. A home consulta os grupos cadastrados e preserva o acervo
visual aprovado. As apresentações começam privadas e não expõem e-mails.

As migrações preparam os quatro trabalhos institucionais existentes, sem criar
contas. O cadastro administrativo fica no Django Admin local. Consulte
[Fase 4 — grupos e equipe editorial](docs/fase-4.md) para as regras e instruções.
Validação: 47 testes Django, 7 do cliente, 18 rotas e 12 cenários reais no Edge
aprovados, além do build. A integração usa banco temporário e Vite na porta 5175:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py test apps.editorial.browser_tests --noinput
```

## Fase 5 — Comunidade Online

Artigos e vídeos em `/comunidade-online.html`; editor em `/editor/novo` e lista
pessoal em `/meus-conteudos.html`. Facilitadores cadastrados pela coordenação podem
criar, editar, publicar e excluir seus próprios conteúdos. O coordenador pode gerir
todos os conteúdos dos seus grupos, preservando a autoria. O editor separa título,
resumo, texto de até 200 mil caracteres, foto de capa e link do YouTube. O leitor
assiste ao vídeo dentro da página. As capas e os títulos publicados abastecem a
home automaticamente. O rodapé usa somente os ícones de YouTube, Instagram e Facebook.

O upload exige Pillow nas dependências do backend. As fotos ficam em
`.local/media/`, com validação e regravação. Conteúdos exclusivos continuam fechados
até a Fase 6. Não há contas nem conteúdos fictícios permanentes.
Veja [Fase 5 — Comunidade Online](docs/fase-5.md) para uso, permissões e limites.

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py test apps.content.browser_tests --noinput
```

A integração usa banco e fotos temporários, Vite na porta 5176 e serviços externos
bloqueados. Foram aprovados 70 testes Django, 7 do cliente, 22 rotas, 12 cenários do
editor, 16 de gestão dos facilitadores no Edge e 12 verificações da home, além do build.

## Fase 7 — agenda, mural e newsletter

Agenda pública em `/agenda.html`, mural em `/mural.html` e gestão em
`/gestao-comunicacao.html`, acessível pela conta. Coordenadores podem escolher
um facilitador auxiliar. Eventos publicados atualizam a home e o mural.
A newsletter tem prévia, edições agendadas, consentimento opcional e boletim
semanal configurável, com padrão segunda-feira às 9h de Brasília.

O envio real vem desativado: exige SMTP, `NEWSLETTER_ENABLED=1` e execução
periódica de `python manage.py process_newsletters` no servidor. Consulte
[Fase 7 — uso e ativação](docs/fase-7.md) para permissões, fluxo e limites.
## Painel de administração

A equipe autorizada acessa `/painel`, com a identidade visual da CUC, indicadores, gráfico editorial, tabelas e controles. Administradores e coordenadores podem selecionar e ordenar destaques da home. Consulte [o guia do painel](docs/painel-administracao.md) para permissões, migração e testes.

A página **Sobre → Fundadores** tem foto, título e história editáveis pelo desenvolvedor em `/painel/fundadores`. Consulte [o guia da página dos fundadores](docs/fundadores.md).

O diretório `/perfis.html` apresenta as pessoas da comunidade, com páginas públicas de foto, biografia, site e vídeo. A edição fica em `/perfil.html`; telefone público é reservado ao desenvolvedor e aos coordenadores. Consulte [perfis e troca de e-mail](docs/perfis-publicos.md).
