# Notificações e atendimento — 15/11/2026

## Funcionamento

O sininho aparece para contas autenticadas na Home, em Minha Conta e no painel. O menu apresenta publicações, agenda e mural atualizados nos últimos 30 dias. O servidor aplica as regras de publicação, grupo ativo e acesso à assinatura antes de produzir as notificações. Conteúdos exclusivos não são incluídos para contas sem o acesso correspondente.

O contador reúne novidades não lidas e atendimentos pendentes. A leitura é persistida individualmente por conta. “Marcar como lidas” não encerra atendimentos nem silencia e-mails que ainda precisam de resposta. O menu consulta novidades a cada minuto enquanto a página está visível, ao recuperar o foco e ao ser aberto. Não se trata de notificação push do navegador.

Facilitador(a), Coordenador(a), Fundador(a) e Desenvolvedor(a) com função/vínculo ativo também recebem avisos dos e-mails importados da caixa comunitária. O link abre **Mensagens recebidas** (`/painel/mensagens`), onde a equipe pode consultar o texto e marcar o contato como respondido ou reabri-lo. Esse acesso não concede administração de usuários, assinaturas ou permissões. Contas comuns e staff técnico sem os papéis apropriados não podem consultar a caixa.

Solicitações existentes de reembolso e privacidade continuam exclusivas de Fundador(a)/Desenvolvedor(a), inclusive no menu de notificações.

## Caixa informada

Endereço indicado: **contato@rhemacuc.com.br**.

A conexão de recebimento ainda precisa dos dados IMAP do provedor/hospedagem. SMTP é o transporte de envio de convites e newsletters; não fornece a leitura da caixa recebida.

Configuração privada do backend, com os nomes documentados também em `.env.example`:

```dotenv
INBOX_ENABLED=0
INBOX_IMAP_HOST=
INBOX_IMAP_PORT=993
INBOX_IMAP_USER=contato@rhemacuc.com.br
INBOX_IMAP_PASSWORD=
INBOX_IMAP_FOLDER=INBOX
INBOX_WEBMAIL_URL=
```

- Preencher o host e as credenciais IMAP fornecidos pelo provedor; não presumir o host a partir do domínio.
- O importador usa IMAP com TLS e validação de certificado. Provedores que exigem OAuth sem senha de aplicativo precisam de uma integração específica; não foram homologados nesta entrega.
- `INBOX_WEBMAIL_URL`, se informado, precisa ser HTTPS e sem credenciais embutidas. Ele habilita o botão para abrir a caixa no provedor.
- Após a configuração e autorização para ativar a integração, habilitar `INBOX_ENABLED=1`.
- Não colocar credenciais no React, no Git ou em mensagens da conversa.

Comando de sincronização:

```powershell
.\.venv\Scripts\python.exe manage.py sync_inbox --limit 50
```

Executar periodicamente pelo mecanismo de tarefas existente, por exemplo a cada minuto, somente após a implantação autorizada. Nenhum agendamento de produção foi criado ou alterado. O intervalo do sininho não executa a conexão IMAP; a sincronização é feita por esse comando no backend.

O cursor de importação por caixa e UIDVALIDITY evita duplicação e permite continuar lotes posteriores sem perder mensagens além do limite. Na primeira execução, mensagens já existentes na pasta também são importadas por lotes: revisar atendimentos antigos antes de tratar toda a fila como nova. O importador não altera o estado de leitura na caixa do provedor.

Mensagens grandes, somente em HTML ou com anexos recebem uma indicação para consulta no provedor. HTML recebido não é renderizado e anexos não são publicados no site. A equipe responde usando o serviço de e-mail e depois marca o atendimento no site. O botão “Marcar como respondida” registra o atendimento; não envia uma resposta e não comprova entrega pelo provedor. A sincronização não tenta inferir respostas enviadas por outros clientes de e-mail.

## Backend e migrações

- `GET /api/notifications`: feed autorizado e contadores.
- `POST /api/notifications`: registra leitura até a data do feed, sem alterar a leitura de outras contas nem retroceder o marcador.
- `GET /api/inbox` e `GET /api/inbox/<id>`: lista e detalhe, somente equipe autorizada.
- `PATCH /api/inbox/<id>`: registra resposta ou reabre o atendimento, com CSRF e verificação de permissão no Django.
- `accounts/0007_profile_notifications_seen_at.py`: acrescenta o marcador individual de leitura.
- `core/0002_inboxmailbox_incomingmessage.py`: cria a caixa importada e seu cursor, sem apagar ou recriar tabelas existentes.

## Verificações

- 14 testes novos do Django: assinatura ativa/vencida, conteúdo exclusivo, perfil autorizado, revogação de vínculo, leitura individual, CSRF, monotonicidade da leitura, atendimento pendente e importação IMAP simulada/idempotente.
- Suíte Django completa: **213 testes aprovados** em PostgreSQL descartável.
- Cliente da API: **8 testes aprovados**.
- Navegador Edge: **8 testes aprovados** nas resoluções desktop, tablet, 390 px e 320 px; incluem dropdown, Escape, clique externo, marcador persistente, navegação para a mensagem e registro de resposta. O conteúdo de e-mail com tags permanece texto, sem execução de scripts.
- Build React aprovado; `manage.py check` e verificação de consistência das migrações aprovados.
- O provedor IMAP foi simulado. Não foram acessados e-mails reais, enviadas respostas, ativada a integração ou publicada uma versão em produção.

Para publicar: revisar o diff, realizar backup, aplicar as migrações em homologação, validar com contas dos papéis previstos e homologar a caixa real. A publicação, as migrações e o agendamento de produção dependem da autorização expressa já exigida para o projeto.
