# Fase 3 — autenticação, contas e permissões

## Regra editorial confirmada

O assinante é consumidor: pode ler artigos publicados por facilitadores, assistir aos
vídeos do YouTube incorporados no próprio site e ouvir áudios publicados. Não pode
comentar, criar, editar ou publicar conteúdo. Alterar seu nome de exibição e sua
própria senha são operações da conta, sem relação com publicação editorial.

Os players e os conteúdos pertencem à Fase 5. O papel de assinante não comprova
pagamento: o acesso exclusivo permanece fechado até a assinatura da Fase 6. Nenhum
artigo, vídeo, áudio ou comprovante financeiro fictício foi colocado na aplicação.

## Arquitetura implementada

- Preservado `auth.User`, já migrado nas etapas anteriores. `accounts.Profile`
  acrescenta nome de exibição e datas por relação individual com o usuário.
- Login por e-mail, ignorando diferenças entre maiúsculas e minúsculas. Um índice
  único em PostgreSQL impede e-mails duplicados, incluindo espaços nas extremidades.
  A migração interrompe diante de duplicatas, sem apagar ou mesclar contas.
- Senhas com o hash e os validadores nativos do Django. Identificadores internos
  de novas contas administrativas são gerados e não precisam aparecer ao assinante.
- Sessões no banco, cookies `HttpOnly` e `SameSite=Lax`, encerramento ao fechar o
  navegador e duração máxima configurada de 12 horas. Nada é gravado em
  `localStorage` ou `sessionStorage` para autenticar.
- CSRF exigido no login e nas alterações autenticadas, inclusive logout. O cliente
  obtém um token atualizado antes de cada operação que modifica dados.
- Respostas de conta com `Cache-Control: no-store`. Desativar a conta impede novos
  logins e invalida o acesso de sessões existentes na próxima requisição.
- Troca de senha exige a senha atual e valida a nova. A sessão atual é preservada;
  as outras são invalidadas ao serem usadas novamente.
- Limites locais: 10 tentativas de login/minuto, 10 trocas de senha/hora e 120
  requisições de conta/minuto. O cache atual é por processo; essa configuração
  local ainda não é uma proteção distribuída para produção.

## Papéis e permissões

| Papel | Base nesta etapa |
| --- | --- |
| Assinante | `read_articles`, `watch_videos`, `listen_audio`; sem escrita editorial |
| Facilitador | Grupo preparado; atribuições e escopo editorial serão definidos nos grupos da Fase 4 |
| Coordenador | Grupo preparado; sem administração global ou publicação automática |
| Administrador | Superusuário Django; gestão administrativa de usuários, perfis e grupos |

As migrações criam apenas os três grupos e as permissões técnicas. Não criam
usuários, pagamentos ou assinaturas. Um usuário pode acumular grupos; não há uma
única coluna de papel que impeça futura participação em vários grupos temáticos.

`IsReadOnlyConsumer` permite somente métodos de leitura quando a permissão de
consumo correspondente existe e a conta está ativa. Não substitui a verificação de
publicação do conteúdo nem da assinatura. `HasExclusiveContentAccess` nega acesso
até a implementação de direitos de assinatura; a API de conta informa
`exclusive_content_access: false` e `subscription_status: not_configured`.

O próprio usuário só pode alterar `display_name`. Tentativas de trocar e-mail,
identidade, grupos, privilégios ou estado da assinatura são rejeitadas. Não há API
pública de criação, listagem ou edição de outras contas.

## Endpoints

| Método e rota | Uso |
| --- | --- |
| `GET /api/auth/csrf` | Token CSRF para a sessão local |
| `POST /api/auth/login` | E-mail e senha; mensagem genérica quando inválidos |
| `POST /api/auth/logout` | Invalida a sessão atual |
| `GET /api/auth/me` | Dados e capacidades da própria conta |
| `PATCH /api/auth/me` | Somente nome de exibição da própria conta |
| `POST /api/auth/password` | Troca autenticada de senha |

O React protege `/area-associado.html` e `/perfil.html`. Sem sessão, redireciona
para login. Com falha de comunicação, não exibe dados privados e permite tentar
novamente. Após login, só aceita destinos internos previamente definidos. O
perfil é revalidado quando a janela volta ao primeiro plano.

## Executar e administrar localmente

Inicie o PostgreSQL isolado pelo script da raiz e aplique as migrações:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Em outro terminal, execute `npm run dev` em `frontend/` e abra
`http://127.0.0.1:5173`. Para preparar manualmente um administrador estritamente
local, use `manage.py createsuperuser` interativamente, sem credenciais reais.
Nenhum administrador permanente foi criado durante esta implementação.

O administrador entra em `http://127.0.0.1:8000/admin/` usando seu e-mail e pode
criar contas, atribuir grupos, alterar perfis e desativar usuários. Contas de
assinantes não recebem `is_staff` nem privilégios de gestão. A criação administrativa
de uma conta não ativa uma assinatura.

Cadastro público e recuperação de senha por e-mail continuam indisponíveis. O
primeiro depende do fluxo de assinatura/convite; o segundo exige uma integração
de comunicação autorizada. Nenhum e-mail, SMS ou pagamento foi enviado.

## Testes

Com o PostgreSQL local iniciado e a porta 5173 livre:

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py test apps.accounts.browser_tests --noinput
cd ../../frontend
npm test
npm run test:routes
npm run test:browser
npm run build
```

A integração de autenticação parte de `LiveServerTestCase`: usa um PostgreSQL de
teste separado, prepara contas com domínio `.invalid`, inicia Django em uma porta
local temporária e aponta o proxy do Vite para esse servidor. Ao terminar, remove
o banco de testes. O comando npm `test:auth` é interno a esse fluxo e recusa execução
avulsa para evitar testes sobre o banco de desenvolvimento.

O limite de requisições é aumentado somente dentro da integração em navegador,
pois todos os cenários compartilham um IP; os testes da API verificam a limitação
normal separadamente. Requisições externas ficam bloqueadas no Edge. Os HTMLs,
o CSS e o JavaScript do site original continuam preservados.

Os testes institucionais seguem cobrindo páginas públicas. A antiga apresentação
estática da área do associado deixa de ser usada como referência visual pública:
agora essa área requer autenticação e mostra os três tipos de consumo solicitados.
O login mantém a aparência institucional, mas passa a executar autenticação real.

Artefatos locais da integração: `.local/phase3/report/` e
`.local/phase3/screenshots/`. Eles não são publicados nem versionados.

## Resultados — 11/11/2026

- Django: 28 testes aprovados em PostgreSQL, incluindo CSRF, autenticação,
  autorização, unicidade de e-mail, desativação e invalidação de outras sessões.
- Cliente JavaScript: 7 testes aprovados; renderização React: 14 rotas verificadas.
- Integração real no Edge: 20 cenários aprovados em quatro larguras, usando um
  banco temporário, 16 contas fictícias e os servidores reais Django/Vite.
- Regressão institucional: 72 verificações aprovadas em quatro larguras, incluindo
  40 comparações visuais idênticas das páginas públicas secundárias com os HTMLs.
- `manage.py check`, conferência de migrações e build Vite aprovados.
- 12 HTMLs, CSS e JavaScript originais conferidos por SHA-256: nenhuma alteração.
- Banco de desenvolvimento após a validação: zero usuários, zero perfis e três
  grupos técnicos. O banco temporário foi removido; nenhum usuário permanente
  foi criado. Os servidores da validação foram encerrados.

Os testes de navegador foram executados no Edge com serviços externos e fontes
remotas bloqueados. Essa rodada não afirma compatibilidade validada com outros
navegadores nem valida reprodução de mídias, que ainda não foi implementada.

## Referências técnicas

- [Django: extensão do usuário existente com perfil](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#extending-the-existing-user-model).
- [DRF: autenticação por sessão e CSRF no login](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).
- [Django: invalidação de sessões após troca de senha](https://docs.djangoproject.com/en/5.2/topics/auth/default/#session-invalidation-on-password-change).
