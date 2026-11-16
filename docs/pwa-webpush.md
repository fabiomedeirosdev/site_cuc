# RHEMA CUC — PWA e Web Push

A PWA usa diretamente o ícone aprovado `assets/icons/RHEMA CUC.png` e o nome
**RHEMA CUC** no manifest e no título da Tela de Início do iPhone. O quadrado
dourado, a moldura, a cruz, o coração e a pomba são preservados. A transparência
fica somente fora do quadrado arredondado; nenhum fundo externo é acrescentado.

Os PNGs `*-v3.png` de 192, 512 e 180 px preservam o canal alpha. Os arquivos de
512 px são cópias exatas do original. A versão Android não reduz o quadrado
dentro de outra área com margem: o launcher aplica o recorte da plataforma à
arte completa. O sistema/launcher pode preencher a transparência com uma cor
própria ou recortar a borda decorativa; uma PWA não controla esse preenchimento.
Veja a
[especificação de máscaras de ícones](https://www.w3.org/TR/appmanifest/#icon-masks).

Para regenerar os tamanhos a partir da imagem original, execute
`powershell -File scripts/build-pwa-icons.ps1` na raiz do projeto.
O manifest, o ícone Apple, o botão de instalação e as notificações usam a nova
versão. As URLs e a versão do cache foram alteradas para evitar reutilização
dos arquivos antigos. Depois de publicar a atualização, remova o aplicativo
antigo da tela inicial e instale novamente pelo navegador para renovar o ícone.

## Arquitetura

- Frontend: manifest, service worker de escopo `/`, instalação e consentimento
  explícito. O botão fica depois da newsletter na página inicial.
- Backend: app técnico `apps.webpush`, com `PushSubscription`, `PushNotification`
  e `PushDelivery`. Nenhum modelo de negócio ou de newsletter foi alterado.
- Uma transição de rascunho para publicado cria uma entrada de fila após o commit.
  Publicações criadas já publicadas também entram. Edições e republicações do
  mesmo objeto não criam novos disparos. Conteúdo antigo já publicado não é
  notificado retroativamente. Operações que ignoram os sinais do Django, como
  `QuerySet.update` ou SQL direto, não são um fluxo de publicação suportado.
- O comando agendado expande destinatários e envia em lotes limitados. Não há
  envio em massa durante a requisição, Redis, Celery ou serviço residente extra.
- Um lock de sessão do PostgreSQL impede sobreposição de execuções do comando.
  A fila retoma pelo cursor de dispositivos. Novas inscrições não recebem
  notificações anteriores à inscrição. Entradas com mais de 24 h não são enviadas.

## Acesso e privacidade

Visitantes inscritos podem receber novidades públicas de todos os grupos e da
agenda. Conteúdo exclusivo exige usuário ativo, sessão ainda válida e a regra de
leitura já existente: assinatura válida ou administração para artigos; assinatura
válida ou gestão da agenda para eventos. A autorização é conferida na expansão e
imediatamente antes do envio. Conteúdos retirados, autores sem autorização,
eventos cancelados e eventos passados não são enviados.

As mensagens são genéricas, sem título, resumo, local ou corpo do conteúdo. Isso
reduz a exposição na tela bloqueada, inclusive se a conta sair depois que o
provedor já aceitou uma mensagem. Ao tocar na notificação, a página mantém as
verificações normais de acesso. Notificações já entregues pelo sistema operacional
não podem ter seu recebimento retroativamente desfeito pelo servidor.

Uma chave aleatória por dispositivo comprova a posse da inscrição ao registrar,
reassociar ou cancelar. Apenas seu hash fica no banco. O vínculo autenticado
também armazena a sessão; logout desvincula as inscrições daquela sessão e
preserva somente o consentimento público. Sessão expirada, conta suspensa ou troca
de senha invalidam a autorização exclusiva. Login sincroniza uma inscrição já
autorizada, sem solicitar consentimento nem inscrever automaticamente ninguém.

Os endpoints exigem CSRF e têm limite de requisições. Somente endpoints HTTPS de
provedores conhecidos são aceitos, com validação das chaves P-256 e auth. O
servidor não aceita endereços arbitrários de destino. Chaves, tokens e respostas
detalhadas dos provedores não são gravados no log do processador.

O service worker armazena somente a página pública de indisponibilidade e ícones.
Não faz cache de API, conta, páginas autenticadas, imagens enviadas ou conteúdos
exclusivos. Links das notificações são restritos à origem do aplicativo.

Newsletter e push têm consentimentos, tabelas e processadores separados. Cancelar
um canal não cancela nem inscreve o outro.

## Preparar a implantação — execução manual na VPS

Nada nesta implementação configura automaticamente a VPS ou outro sistema.
Mantenha os caminhos, usuário de serviço e ambiente virtual próprios do RHEMA CUC.

1. Instalar as dependências atualizadas com `python -m pip install -r requirements.txt`.
2. Aplicar `python manage.py migrate`. A migração cria apenas tabelas técnicas.
3. Gerar uma única vez o par VAPID em um diretório privado, fora do Git, do
   document root e de `MEDIA_ROOT`. Exemplo Linux, com o ambiente virtual ativo:

   ```sh
   umask 077
   mkdir -p /var/lib/rhemacuc/secrets/webpush
   cd /var/lib/rhemacuc/secrets/webpush
   vapid --gen
   vapid --applicationServerKey --private-key private_key.pem
   ```

   O último comando exibe somente a chave pública para o navegador. Conservar
   `private_key.pem` em backup protegido e conceder leitura somente ao usuário da
   aplicação. Não substituir as chaves a cada deploy: isso invalida inscrições.

4. Configurar no ambiente do Django e do comando agendado:

   ```dotenv
   WEBPUSH_ENABLED=1
   WEBPUSH_PUBLIC_KEY=<applicationServerKey gerada>
   WEBPUSH_PRIVATE_KEY=/var/lib/rhemacuc/secrets/webpush/private_key.pem
   WEBPUSH_SUBJECT=mailto:<e-mail real de contato técnico>
   ```

   A chave privada é um caminho de arquivo PEM ou um valor DER em Base64,
   conforme a biblioteca pywebpush. Nunca enviar a chave privada ao frontend.

5. Gerar `npm run build` em `frontend` e publicar **todo** `frontend/dist`,
   incluindo `sw.js`, `manifest.webmanifest`, `offline.html` e `icons/`.
   Reiniciar somente o processo da API do RHEMA CUC para carregar o novo código e
   as variáveis de ambiente, depois de aplicar as migrações.
6. No servidor do frontend, `/sw.js` deve responder JavaScript, com HTTP 200,
   escopo `/` e `Cache-Control: no-cache`; `/manifest.webmanifest` deve responder
   JSON de manifest e `/icons/` deve entregar PNG. Nenhum desses caminhos pode
   cair no HTML de fallback do React. O exemplo Nginx do projeto contempla isso.
   Se a hospedagem usar Apache, reproduzir essas regras na configuração existente.
7. A PWA e o service worker pertencem à origem do **frontend**. A API pode estar
   na mesma origem ou no domínio já configurado por `VITE_API_BASE_URL`. Em
   origens separadas, conferir CORS, CSRF e cookies de sessão existentes. Não
   trocar o domínio do site para instalar a PWA.
8. Agendar, por exemplo a cada minuto, com os caminhos reais do projeto:

   ```cron
   * * * * * cd /srv/rhemacuc/backend/django_platform && .venv/bin/python manage.py process_webpush --batch-size 20 --max-seconds 25 >> /var/log/rhemacuc-webpush.log 2>&1
   ```

   O lote padrão limita expansão e envios a 20 por execução, com timeout de 5 s
   por tentativa. O prazo limita o início de novos envios; uma tentativa em curso
   pode terminar após o prazo. Ajustar o lote somente após observar uso de CPU,
   memória e tamanho da fila na VPS de 2 GB. Não alterar processos do UFODROMO.
   Permitir saída HTTPS para os provedores de push; não é necessária porta nova
   de entrada. Configurar rotação do arquivo de log da aplicação.

## Falhas e duplicidades

Respostas 404/410 removem inscrições inválidas. Falhas temporárias, limites do
provedor e erros de conexão são reagendados, com intervalo crescente e até cinco
tentativas. Outros erros permanentes encerram a entrega. O processador exibe
somente contadores e códigos de erro. A unicidade da publicação e da entrega
evita duplicidades normais; `tag` estável e `renotify: false` substituem a mesma
notificação no dispositivo. Uma falha após o provedor aceitar o envio pode causar
nova tentativa: Web Push não oferece confirmação de entrega exatamente uma vez.

O TTL no provedor é de cinco minutos. O sistema operacional decide a apresentação
e pode aplicar economia de bateria, modo Foco ou outras restrições. Web Push
funciona sem manter uma aba aberta, mas não garante entrega imediata ou quando
o navegador/aplicativo foi forçado a encerrar.

## Homologação

Testes automatizados simulam provedores: não enviam notificações reais nem usam
credenciais de produção. Cobrem opt-in anônimo, CSRF, posse do dispositivo,
permissões, expiração, logout, troca de conta, fila, criptografia, cancelamento,
erros, duplicidades, cache e navegação pelo service worker.

Em aparelhos reais, homologar em HTTPS: instalação Android; instalação no iPhone
pela opção Compartilhar → Adicionar à Tela de Início; nome RHEMA CUC; autorização
somente após toque; recebimento público e exclusivo; app fechado; abertura do
conteúdo; logout; expiração; desativação; independência da newsletter. No iPhone,
Web Push requer a PWA na Tela de Início e iOS/iPadOS 16.4 ou posterior compatível.
A instalação e a entrega efetiva em aparelhos físicos não são comprovadas pelos
testes locais.

Validação local concluída: 243 testes Django aprovados (27 específicos de Web
Push), 19 testes JavaScript, 30 rotas React e build de produção. No Edge local,
foram verificados os layouts de 390 e 1440 px, o ícone e o nome, instruções para
iPhone, acionamento de instalação simulado, registro e cache reais do service
worker e navegação sem conexão. Esses testes não equivalem à instalação no
sistema operacional nem à entrega push em Android ou iPhone físicos. Uma
repetição da suíte encontrou bloqueio de arquivo temporário no Windows; a
execução completa posterior terminou com os 243 testes aprovados.

Referências: [WebKit / iPhone](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/),
[Push API](https://developer.mozilla.org/en-US/docs/Web/API/PushManager/subscribe),
[pywebpush](https://github.com/web-push-libs/pywebpush).
