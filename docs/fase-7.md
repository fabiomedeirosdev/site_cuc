# Fase 7 — agenda, mural e newsletter

## Operação

O painel `/gestao-comunicacao.html` fica disponível na área da conta para o coordenador e para o facilitador escolhido como auxiliar. A agenda pública está em `/agenda.html` e os avisos em `/mural.html`. A home mostra os próximos eventos e as atualizações recentes do mural, usando as mesmas publicações do painel.

Na aba **Agenda**, informe título, descrição, início, término opcional e local. As datas do formulário e da apresentação usam Brasília. Salve como rascunho ou marque a publicação na agenda e no mural. Editar um evento publicado atualiza os dois lugares automaticamente; não há duas cópias para manter. É possível informar cancelamento preservando o aviso ou excluir o evento. O arquivo de eventos anteriores fica disponível na agenda pública.

Eventos são públicos por padrão. O campo **Público do conteúdo** oferece **Público — visitantes e assinantes** ou **Somente assinantes**. A segunda opção reserva o local e a descrição a pessoas com assinatura vigente e à equipe autorizada de comunicação. O título, a data, o cancelamento e a indicação de exclusividade permanecem públicos na agenda, na prévia da home e no mural. O servidor omite os detalhes reservados para visitantes e contas sem acesso pago. Rascunhos continuam privados, independentemente desse seletor. A agenda mantém a apresentação em lista de eventos com data e local; não recebe campo de imagem.

Na aba **Mural**, crie e edite avisos independentes, com imagem opcional e a mesma escolha de público. Avisos exclusivos mostram o título e um convite para entrar; texto, imagem e descrição da imagem são entregues apenas a assinantes com período pago vigente ou à equipe autorizada. Somente avisos publicados são exibidos fora do painel.

## Cartazes e imagens

Mural, edições avulsas de newsletter e boletim semanal aceitam uma imagem opcional. O campo permite enviar, visualizar, substituir e remover a imagem, com descrição obrigatória quando há imagem. Aceita JPG, PNG ou WebP de até 5 MB, mínimo de 600 × 300 px e máximo de 4096 × 4096 px. Recomendamos 1200 × 1600 px para cartazes verticais ou 1600 × 900 px na horizontal. A proporção é preservada, sem recorte, para manter textos de divulgação. O servidor remove metadados e normaliza a imagem para JPEG de até 2000 px em cada lado, sem ampliar imagens pequenas.

Os arquivos ficam em `COMMUNICATIONS_MEDIA_ROOT`, fora do diretório público de mídia; no ambiente local o padrão é `.local/communications-media`. Em produção, configure um diretório persistente e privado, como `/var/lib/rhemacuc/communications-media`, gravável pelo serviço Django e pelo trabalhador de newsletter. Não crie uma rota estática para esse diretório. O endpoint `/api/communication-images/<tipo>/<id>` verifica publicação e acesso em cada leitura e não permite cache compartilhado. Tornar um aviso exclusivo protege também uma URL de imagem obtida quando ele ainda era público. As imagens principais das newsletters enviadas são incorporadas ao e-mail por CID; a prévia usa uma cópia embutida, sem publicar nem enviar a edição.

Na aba **Equipe**, o coordenador escolhe um facilitador ativo de um grupo que coordena. Cada coordenador pode manter um auxiliar por vez. O auxiliar gerencia os três recursos, mas não pode nomear outras pessoas nem recebe acesso financeiro, de administrador ou a grupos alheios. Remover a delegação, o vínculo de facilitador, a atividade do grupo, a atividade da conta ou a coordenação retira a autorização nas próximas chamadas da API. Como agenda e mural são institucionais, coordenadores e auxiliares autorizados trabalham no mesmo calendário e mural da comunidade. A escolha do auxiliar permanece vinculada aos grupos do coordenador que concedeu a autorização.

## Newsletter

Cada edição e o boletim semanal têm escolha de público. **Público** envia a todos os endereços com consentimento confirmado, incluindo visitantes e assinantes. **Somente assinantes** exige consentimento e uma conta ativa com período pago vigente, sem bloqueio de acesso; cancelamentos com período já pago ainda válido são respeitados. A autorização é verificada ao preparar a fila e novamente em cada tentativa de entrega. A programação semanal copia sua imagem, descrição e público para a edição gerada. Avisos exclusivos do mural não têm texto nem imagem revelados no resumo público, inclusive se a restrição mudou depois da criação do resumo.

A aba **Newsletter** permite escrever o assunto e a mensagem, conferir uma prévia do e-mail e salvar rascunhos ou agendar uma edição. O modelo HTML usa as cores da comunidade, resumo dos próximos 14 dias da agenda, até quatro avisos recentes, links para o site e descadastro pessoal. Textos dos editores são escapados; não se aceita HTML arbitrário. A prévia é isolada em iframe sem execução de scripts.

A programação automática tem como padrão **segunda-feira, às 9h, no horário de Brasília**, conforme solicitado. A coordenação ou o auxiliar pode ativar, ajustar o dia e a hora e editar o assunto e a introdução. Uma edição automática é criada por semana ISO, com chave única para impedir duplicação em execuções repetidas. Se o trabalhador estiver fora do ar no horário, ele tenta a edição daquela semana na primeira execução posterior ao horário programado, sem criar boletins de semanas anteriores.

Edições agendadas ou em envio podem ser canceladas para interromper mensagens ainda pendentes. Desativar o boletim semanal também interrompe edições automáticas pendentes. E-mails já enviados, ou que o servidor SMTP já está aceitando naquele momento, não podem ser recolhidos. Mensagens concluídas não podem ser alteradas para simular outro envio.

O recebimento das edições **públicas** é gratuito e aberto a visitantes, pessoas sem conta e assinantes, mediante autorização e confirmação do e-mail. Assinar ou aceitar os termos não ativa automaticamente esse recebimento. Cancelar ou deixar vencer uma assinatura não interrompe as edições públicas autorizadas; as edições exclusivas deixam de ser entregues quando o período pago termina. Antes de cada entrega, a rotina verifica a preferência atual, o endereço, o público escolhido e a autorização da equipe responsável. Endereços individuais não são expostos na interface da coordenação nem agrupados em campos CC/CCO. O modelo do e-mail inclui um convite para conhecer a assinatura da CUC Online.

Na conta, cada pessoa pode ativar ou desativar o recebimento. Na home, qualquer visitante pode informar um e-mail válido, autorizar e confirmar pelo link pessoal de uso único, com 48 horas de validade. Nenhuma conta de acesso nem cobrança é criada nesse processo. A resposta não revela se o endereço possui conta ou assinatura. Apenas o hash do token de confirmação é guardado. A confirmação e o descadastro usam fragmentos de URL removidos do endereço pelo frontend; exigem confirmação explícita via POST, evitando que robôs de leitura de links alterem a preferência. O descadastro não exige login e não cancela eventual assinatura paga. Quando uma pessoa entra com uma conta do mesmo e-mail, sua preferência existente é vinculada sem perder a autorização ou o link de saída.

Os e-mails compartilhados com visitantes mostram somente título, data e indicação dos eventos exclusivos, sem o local reservado. A rotina também verifica se um evento foi reservado ou retirado de publicação depois que a edição entrou na fila. A migração preserva as preferências existentes, seus vínculos e links de descadastro; os novos contatos podem existir sem usuário de acesso.

## Ativação e tarefa do servidor

O transporte de newsletter vem **desativado**, por `NEWSLETTER_ENABLED=0`. O desenvolvimento continua usando e-mails em memória; nenhum e-mail real foi enviado nesta implementação. O painel permite preparar conteúdos e agendamentos enquanto o envio está desativado e informa essa situação.

Para entregar mensagens reais, configurar o SMTP já previsto na fase 6, remetente habilitado, domínio público HTTPS em `PUBLIC_FRONTEND_URL`, e-mail real de atendimento e `NEWSLETTER_ENABLED=1` no ambiente privado de produção. Verificar o recebimento no provedor, remetente, reputação do domínio e limites de envio. A credencial de SMTP nunca é enviada ao navegador. Esses recursos não substituem o acompanhamento do provedor de e-mails.

Aplicar as migrações e agendar no servidor, por exemplo a cada cinco minutos:

```powershell
cd E:\site_cuc\backend\django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py process_newsletters
```

A rotina usa um bloqueio do PostgreSQL para evitar trabalhadores simultâneos. Cada destinatário tem um registro único por edição. Entregas confirmadas não são repetidas pela próxima execução; falhas SMTP permanecem pendentes para retentativa. Como em outros envios SMTP, uma queda após o provedor aceitar a mensagem e antes da gravação local pode causar reenvio. Não há promessa de entrega exatamente uma vez nem acompanhamento automático de abertura, cliques, devoluções ou reclamações de spam. O disparo em grande volume requer acompanhar os limites do serviço contratado; o comando faz entregas sequenciais com timeout.

Não foi instalada uma tarefa automática no Windows local nem alterada hospedagem. A recorrência de produção depende de instalar e manter a execução periódica no servidor, além de habilitar o boletim no painel. A ausência de conteúdo novo não impede o boletim semanal, que usa a mensagem preparada e os itens publicados disponíveis.

## Verificação

```powershell
cd backend/django_platform
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py test apps.communications.browser_tests --noinput
.\.venv\Scripts\python.exe manage.py test apps.communications.tests apps.communications.test_images_audiences --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
cd ../../frontend
npm test
npm run test:routes
npm run build
```

Os testes Django cobrem escopo e revogação de autorização, publicação e sincronismo com o mural, reserva de detalhes dos eventos, validação de datas, consentimento, confirmação gratuita e descadastro, proteção contra HTML, envio semanal, duplicação e retentativa. A integração no Edge usa PostgreSQL e contas temporárias e Vite na porta 5178, em 1440, 1024, 390 e 320 px. E-mails são mantidos exclusivamente na memória do processo, inclusive as confirmações de visitantes. Nenhuma mensagem é entregue a serviços externos.

Artefatos de navegador em `.local/phase7`. O banco de desenvolvimento não recebe usuários ou eventos de demonstração dos testes.

Resultados da atualização: 127 testes Django e 16 cenários no Edge aprovados, incluindo a confirmação gratuita de visitantes sem criação de conta e a proteção dos eventos exclusivos. Os cenários de navegador passaram em quatro tamanhos de tela. Migrações aplicadas e sem alterações pendentes. O banco de desenvolvimento não recebe contatos, eventos nem campanhas de demonstração desses testes. A prévia HTML local pode ser regenerada a partir do modelo atualizado, sem enviar e-mails.
