# Melhorias da Comunidade Unidos em Cristo — 14/11/2026

## 1. Auditoria do que já existia

- **Publicações públicas/exclusivas: parcialmente implementadas no fluxo solicitado.** `Article.audience` e seu seletor já existiam no editor. O Django já ocultava o corpo e o vídeo das publicações exclusivas para quem não tinha período pago. A página individual do grupo ainda não listava as publicações. A implementação reutiliza os modelos, endpoints, políticas e cartões existentes.
- **Coordenador e Facilitador:** já eram representados pelos vínculos editoriais de cada grupo. Esses vínculos, nomes, restrições e permissões editoriais foram preservados. Não foi criado outro tipo de coordenador.
- **Fundador:** existia uma página institucional, mas não uma função administrativa de conta. O Desenvolvedor existente era identificado pelo superusuário técnico.
- **Delegação de comunicação:** existia um responsável por coordenador, com acesso conjunto à agenda, mural e newsletter. Não havia controles independentes de agenda e mural.
- **Equipes e permissões:** exigia um grupo e repetia links de criação/edição de grupos. Os perfis já existiam independentemente de vínculo, mas não havia atribuição de funções gerais por esse formulário.
- **Ordenação:** grupos já possuíam `position`; perfis eram ordenados pela última atualização e vínculos pela função.
- **Pagamento:** há uma integração PagBank implementada em código, apesar de o README antigo ainda dizer que pagamentos não estão integrados. O checkout envia o preço em centavos e gera seu plano recorrente. A sincronização financeira compara o valor com o checkout original, não com o preço atual de novas contratações.
- **Contato:** reutilizado o WhatsApp institucional `5511986302883`, presente no rodapé e nas páginas públicas. O número do desenvolvedor não foi utilizado.

## 2. Implementação

- Home: texto solicitado, preço R$ 48,00 e opção de contribuição maior com a mensagem exata no WhatsApp. Após a revisão visual solicitada, a contribuição passou a uma faixa vermelha fina e independente abaixo do quadro da assinatura, com texto branco e botão dourado “Clique aqui →”, seguindo a referência enviada.
- Favicon: arquivo original `assets/magazine/logos_maria_pomba.png`, o mesmo exibido na primeira seção da Home. Vite inclui o arquivo no build; a imagem não foi modificada.
- Preço de novas contratações: configuração do servidor e padrão de novos checkouts passam a 4800 centavos. A página de assinatura já lê o valor da API. Os termos foram atualizados. Não existe migração de dados para alterar checkouts, pagamentos ou assinaturas anteriores.
- Grupos: a página individual exibe publicações paginadas com os cartões existentes. O editor mantém o seletor público/exclusivo para criação e edição. A API autenticada permite a leitura por assinantes com acesso vigente e administradores autorizados; visitantes e assinantes vencidos não recebem corpo, vídeo ou resumo exclusivo. Os metadados de apresentação continuam públicos para permitir a indicação de conteúdo exclusivo.
- Endereço, WhatsApp próprio e vídeo de apresentação do grupo são opcionais, públicos e editados na gestão de grupos. Grupos antigos permanecem válidos com campos vazios e usam o contato institucional como alternativa. URLs de vídeo são validadas e convertidas para o player existente.
- Fundador e Desenvolvedor podem ser atribuídos como funções gerais do perfil, sem tornar a conta staff ou superusuário. O superusuário técnico existente continua identificado como Desenvolvedor. Fundador tem administração geral na aplicação; a ordem de membros e a atribuição da função Desenvolvedor ficam reservadas ao Desenvolvedor.
- O formulário geral de membros aceita um grupo ou **Atuação geral — sem grupo específico**, inclusive para cadastrar novos acessos. Sem grupo e sem função, nenhuma permissão é concedida. A coordenação continua dependendo de vínculo com um grupo. Vínculos anteriores não são apagados nem substituídos automaticamente.
- Agenda e mural: somente Desenvolvedor e Fundador administram novas delegações, com dois controles independentes e revogação de autorizações anteriores. Vários facilitadores podem ser autorizados. O servidor verifica a seção em cada operação de leitura administrativa, criação, alteração e exclusão. Delegados novos não recebem newsletter nem administração completa por esse mecanismo.
- Permissões atuais de edição da coordenação e autorizações antigas de comunicação são preservadas na migração. Coordenadores deixam de administrar delegações, conforme a exigência expressa de reservá-las a Desenvolvedor/Fundador. A visibilidade da agenda não foi alterada.
- Removidos apenas os links duplicados para criar/editar grupos na interface de equipes. A gestão de grupos, fotos, endpoints e registros continua disponível em sua página própria.
- Nomenclatura pública atualizada para **Membros da Comunidade**, mantendo as rotas.
- `Profile.position`: ordem numérica manual, editável apenas pelo Desenvolvedor na aplicação e no inline existente do Django Admin. Aplicada ao diretório de membros, facilitadores e equipes públicas de grupos, com desempate estável por identificadores, sem prioridade automática por papel. Facilitadores de atuação geral também podem aparecer no diretório sem grupo.
- `Avatar.jsx` foi preservado integralmente, incluindo a correção do domínio das imagens `/api/`.

## 3. Arquivos alterados

Os caminhos abaixo são relativos à raiz do repositório.

| Área | Arquivos |
| --- | --- |
| Contas e papéis | `backend/django_platform/apps/accounts/{admin.py,models.py,policies.py,profile_views.py,serializers.py}` |
| Grupos e equipes | `backend/django_platform/apps/editorial/{models.py,policies.py,serializers.py,views.py}` |
| Publicações | `backend/django_platform/apps/content/{policies.py,serializers.py,views.py}` |
| Comunicação | `backend/django_platform/apps/communications/{models.py,policies.py,serializers.py,views.py,tests.py}` |
| Administração | `backend/django_platform/apps/core/{management_views.py,team_views.py,urls.py,test_community_improvements.py}` |
| Assinaturas | `backend/django_platform/apps/billing/{models.py,tests.py,browser_tests.py}`, `backend/django_platform/config/settings.py`, `backend/django_platform/.env.example` |
| Interface | `frontend/index.html`, `frontend/src/{App.jsx,api-client.js}`, `frontend/src/components/GroupForm.jsx` |
| Páginas | `frontend/src/pages/{HomePage.jsx,home.css,LegalPages.jsx,PublicProfilesPages.jsx,GroupsPages.jsx,TeamManager.jsx,CommunicationsPages.jsx}` |
| Testes de navegador | `frontend/playwright.community.config.js`, `frontend/tests/{home.spec.js,community-improvements.spec.js}` |
| Relatório | `docs/melhorias-comunidade-2026-11-14.md` |

As quatro migrações também fazem parte da alteração, conforme a próxima seção.

## 4. Migrações necessárias

1. `accounts/0005_profile_community_role_profile_position.py`: adiciona função geral e ordem, inicialmente vazias/zero, sem promover contas existentes.
2. `billing/0002_alter_checkout_amount.py`: muda o padrão para novos checkouts; não atualiza valores de registros anteriores.
3. `communications/0005_delegation_can_edit_agenda_delegation_can_edit_mural_and_more.py`: acrescenta os controles, preservando os acessos antigos, e permite múltiplas delegações por administrador. Mantém unicidade por administrador/facilitador e não apaga registros.
4. `editorial/0005_editorialgroup_address_editorialgroup_video_url_and_more.py`: acrescenta contatos e vídeo opcionais.

Não há remoção de tabelas, exclusão de registros ou migração destrutiva. As migrações foram exercitadas somente em banco descartável de testes. Não foram aplicadas no banco de desenvolvimento existente nem em produção.

## 5. Validação

- `manage.py check`: sem problemas.
- `manage.py makemigrations --check --dry-run`: **No changes detected**, confirmado ao final; os modelos e as quatro migrações estão incluídos.
- Suíte Django final: **199 testes aprovados**, incluindo permissões, acesso público/exclusivo, período vencido, Fundador, cadastro sem grupo, delegações, ordem, cobrança antiga, contatos públicos dos grupos e facilitadores gerais.
- Cliente de API: **8 testes aprovados** (`npm test`).
- React: **build aprovado** (`npm run build`). Vite mantém aviso sobre o tamanho do bundle; não foi feita divisão/refatoração fora do escopo.
- Edge com APIs simuladas: **8 testes aprovados**, nas resoluções 1440, 1024, 390 e 320 px. Cobrem Home, favicon, preço, mensagem WhatsApp, formulário sem grupo, ordem e controles independentes. Sem erros JavaScript ou rolagem horizontal nos cenários verificados.
- A suíte institucional mais antiga foi explorada: o teste da Home acusa uma lista de rotas desatualizada que não reconhece `/fundadores.html`, já existente. Essa suíte não foi usada como critério de aprovação destas mudanças. A configuração dedicada verifica as telas alteradas.
- `git diff --check`: sem erros de conteúdo; Git avisa apenas da conversão de finais de linha em um arquivo de teste.

O usuário do banco local existente, em `127.0.0.1:5432`, não pode criar bancos de teste. Foi usado um PostgreSQL descartável em `127.0.0.1:55433`, sem alterar o `.env` ou os dados existentes. O sandbox também bloqueou temporários de imagens e processos do navegador/build, então as execuções necessárias foram repetidas com a aprovação nativa.

## 6. Pendências e limites

- Não foi feita uma transação real nem consulta autenticada ao PagBank de produção. Os testes validam o payload enviado pelo código e a reconciliação, com provedor simulado.
- O fluxo atual cria o plano recorrente no checkout; não há um ID de plano externo fixo a atualizar no código. Se a operação usar links ou planos criados manualmente no painel do PagBank fora desse fluxo, será necessário criar/ajustar **apenas a oferta para novas contratações**, mantendo os contratos existentes.
- Homologar no sandbox PagBank a criação de checkout e recorrência de R$ 48,00, incluindo confirmação, convite, renovação e cancelamento, antes de abrir contratações em produção.
- Atribuir os fundadores reais e configurar as posições manualmente após a publicação autorizada. Ninguém foi promovido automaticamente e não foram inferidos nomes/cadastros reais a partir da página institucional.
- O favicon reutiliza a imagem original, que é grande. Ela foi preservada sem redesenho ou redução, conforme solicitado.
- A validação de navegador específica usa dados simulados; não substitui a conferência com cadastros reais em homologação.

## 7. Procedimento seguro de publicação — somente após autorização

1. Revisar o diff e preparar backup verificável do PostgreSQL e das mídias. Registrar a versão atual para eventual reversão do código.
2. Publicar primeiro em homologação com a mesma versão do código de backend/frontend. Conferir `manage.py check` e `manage.py migrate --plan` no ambiente correto.
3. Aplicar as quatro migrações em homologação com `manage.py migrate`. Repetir a validação dos papéis, revogação das duas permissões separadamente e conteúdo público/exclusivo usando sessões distintas.
4. Homologar o PagBank em sandbox. Verificar R$ 48,00 no checkout e no plano recorrente efetivamente criado. Conferir que assinaturas anteriores a R$ 48,20 continuam sendo reconciliadas pelo checkout original.
5. Com autorização expressa para produção, aplicar o código e as migrações revisadas conforme o procedimento de implantação já existente; disponibilizar o build React. Não alterar infraestrutura nem contratos antigos como parte desta atualização.
6. Pelo Desenvolvedor, atribuir Fundador às contas corretas, revisar delegações antigas, cadastrar a ordem manual e conferir uma conta anônima, uma vencida e uma assinante ativa.
7. Em caso de problema, interromper novas contratações pelo procedimento operacional existente e avaliar a reversão do código. Não reverter as migrações com remoção de colunas e perda dos novos dados sem análise e autorização.

Nenhum deploy, reinício de serviço de produção ou migração em produção foi executado. O UFODROMO não foi alterado.
