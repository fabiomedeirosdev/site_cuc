# Fase 6 — assinatura e proteção da Comunidade Online

Implementação local de R$ 48,20 por mês, com PagBank/PagSeguro. A integração vem desativada (`BILLING_ENABLED=0`); os testes não efetuam cobranças e usam e-mails somente em memória. Não foi realizada homologação na conta do estabelecimento.

## Fluxo implementado

1. A home direciona para `/assinatura.html`, com preço, recorrência, condições e aceite dos termos e da política de privacidade.
2. O servidor cria um checkout recorrente mensal. O valor é fixado no servidor, em centavos; o navegador não escolhe valor, plano ou privilégios. A reutilização de checkout e a chave de idempotência evitam duplicação nas tentativas.
3. O pagamento acontece no PagBank. O retorno à página de pagamento não comprova aprovação nem libera conteúdo.
4. O webhook de assinaturas informa o identificador. O servidor consulta a API autenticada do PagBank e confere plano criado pelo site, valor, moeda, identidade e situação. O corpo enviado ao webhook não comprova pagamento.
5. Um ciclo confirmado em `ACTIVE` registra o vencimento informado pelo banco. Eventos repetidos não somam meses; eventos antigos não reduzem nem renovam o período.
6. O pagamento confirmado gera um convite por e-mail. O token tem 48 horas de validade, é de uso único e seu hash é armazenado. O endereço usa fragmento, removido pelo React, para evitar o envio do token na URL HTTP e no referenciador.
7. O convite cria somente uma conta de assinante. Uma conta existente exige login para vinculação e não tem sua senha alterada pelo convite. O aceite da versão dos documentos fica registrado.
8. `/minha-assinatura.html` exibe validade, cancelamento da renovação e solicitações de atendimento com protocolo. Uma falha do banco é mostrada como pendência; o pedido fica salvo para retentativa.

   O acesso fica em destaque na conta, antes dos conteúdos, pelo botão “Gerenciar ou cancelar assinatura”, e no rodapé da home por “Assinatura e cancelamento”. Na assinatura, o botão vermelho “Cancelar assinatura” fica visível fora de menus e exige somente uma confirmação, exibindo a validade restante.
9. Cancelar a renovação preserva o último vencimento confirmado. Com 15 dias restantes, ficam os 15 dias; com 1 dia, fica 1 dia. Atraso não concede mês adicional. O servidor verifica o acesso a cada leitura, mesmo com sessão aberta. Texto e URL incorporada do vídeo não são enviados quando o acesso expirou. A resposta privada tem `Cache-Control: no-store`.

Assinantes não recebem permissões de facilitador, coordenador ou administrador. As atribuições editoriais da fase 5 continuam independentes.

## Configuração antes de aceitar pagamentos

Preencher no ambiente privado do servidor, sem publicar credenciais no frontend ou no Git:

- `PAGBANK_ENVIRONMENT=sandbox` para homologação; `production` somente depois de validar os cenários na conta do estabelecimento.
- `PAGBANK_CHECKOUT_TOKEN` e `PAGBANK_RECURRING_TOKEN`, com habilitação para os respectivos produtos. As APIs de Checkout e Assinaturas têm endereços e requisitos próprios. A modalidade recorrente usada aqui é por cartão de crédito; não promete Pix ou boleto recorrente.
- `PUBLIC_FRONTEND_URL` e `PUBLIC_API_URL`, públicos e HTTPS. A API recebe o webhook e o frontend recebe o visitante.
- `MERCHANT_LEGAL_NAME`, `MERCHANT_DOCUMENT`, `MERCHANT_ADDRESS` e `MERCHANT_CONTACT_EMAIL`, com os dados reais do fornecedor. Esses dados são exibidos nos documentos. O checkout permanece indisponível quando faltam os dados necessários.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS` e `DEFAULT_FROM_EMAIL`, com domínio/remetente habilitado. Sem SMTP, desenvolvimento usa memória e não entrega e-mail. Produção exige SMTP e remetente configurados.
- `BILLING_ENABLED=1`, somente após a configuração e homologação. O preço é `4820` e a versão atual é `2026-11-12-v1`, definidos no servidor.

Na configuração de **webhooks do produto Assinaturas do PagBank**, cadastrar `https://rhemacuc.com.br/api/billing/webhooks/pagbank` para os eventos `subscription.*`. Site e API usam o mesmo domínio em produção, conforme [a configuração de hospedagem](producao-rhemacuc.md). Notificações de pagamento do checkout, sozinhas, não substituem esse cadastro. Confirmar entrega e retentativa de eventos na homologação.

Aplicar migrações com `python manage.py migrate`. Agendar no servidor `python manage.py process_billing`, por exemplo a cada cinco minutos, com execução única por vez. O comando consulta assinaturas conhecidas, retenta pedidos de cancelamento e e-mails pendentes. A expiração de acesso independe desse agendamento. Assinaturas novas dependem do recebimento do webhook; acompanhar o painel do PagBank e suas falhas de entrega.

## Homologação e limites operacionais

- Confirmar na conta habilitada o formato real do retorno de criação do checkout, `recurrence_plan.id`, a URL `PAY`, o vínculo do plano com a assinatura, os tokens e a entrega dos eventos.
- O adaptador considera o estado `ACTIVE` como comprovação de pagamento no ciclo vigente, conforme a documentação do PagBank, e usa `next_invoice_at` como vencimento. Não deduz um mês pago de um evento `CANCELED`, `OVERDUE`, `TRIAL` ou de um retorno de navegador. Validar a precisão de data e horário do ciclo com o banco.
- Se o **primeiro** retrato recebido já estiver cancelado e o site nunca registrou o ciclo ativo, ele não inventa um período pago. Essa recuperação exige conciliação do histórico financeiro com o estabelecimento antes da ativação real. O comando atual reconcilia somente assinaturas já conhecidas.
- Reembolso e chargeback não são automáticos nesta entrega. Eventos financeiros que não sejam `subscription.*` não são interpretados como crédito ou débito. Os pedidos de arrependimento/privacidade recebem protocolo e confirmação e aparecem no Django Admin; o atendimento deve efetuar e acompanhar o tratamento financeiro no PagBank. O protocolo nunca é apresentado como estorno concluído.
- Após verificar um estorno ou contestação, o administrador técnico pode marcar `safety_hold` no registro de assinatura para suspender o acesso sem apagar o histórico. Não editar vencimento ou inserir períodos manualmente. Alterações da identidade financeira também exigem conferência.
- O painel financeiro e os protocolos estão restritos ao superusuário. Coordenadores continuam responsáveis pela gestão de facilitadores; não recebem acesso financeiro por essa atribuição.
- Falhas de SMTP ficam como tarefas pendentes. A entrega usa chave de deduplicação, mas, como em SMTP em geral, uma queda após a aceitação do e-mail e antes da gravação local pode causar reenvio. Um novo convite invalida o anterior.
- Os documentos foram adaptados ao comportamento implementado. Completar a identificação do fornecedor e conferir os procedimentos de atendimento, conservação de dados, reembolso e prazos com a operação responsável antes de contratar com consumidores.

## Verificação local

- `python manage.py test --noinput`: regressão das APIs, autorização, conteúdo e regras de assinatura.
- `python manage.py test apps.billing.browser_tests --noinput`: Edge em 1440, 1024, 390 e 320 px; banco temporário, API Django real, apenas PagBank simulado e e-mail em memória. Checkout com aceite, convite de novo assinante, vinculação de conta existente, vídeo protegido, cancelamento preservando validade, protocolo e assinante vencido.
- `npm test`, `npm run test:routes` e `npm run build` no frontend.

Os relatórios de navegador ficam em `.local/phase6`, sem publicar tokens ou credenciais. Os testes de assinatura desativam traces para evitar capturar os convites mesmo sendo dados fictícios.

Resultados locais: 94 testes Django, 8 testes do cliente, 24 rotas, 16 cenários de assinatura no Edge e 24 verificações das páginas públicas alteradas aprovados. Build e conferência de migrações aprovados. API local atualizada; checkout real desativado. Banco de desenvolvimento sem usuários, checkouts ou assinaturas de demonstração.

## Fontes oficiais consultadas

- [Checkout recorrente PagBank](https://developer.pagbank.com.br/docs/checkout) e [objeto do checkout](https://developer.pagbank.com.br/reference/objeto-checkout).
- [Situações da assinatura](https://developer.pagbank.com.br/docs/assinaturas), [consulta autenticada](https://developer.pagbank.com.br/reference/consultar-assinatura) e [objeto da assinatura](https://developer.pagbank.com.br/reference/objeto-assinatura).
- [Webhooks de assinaturas](https://developer.pagbank.com.br/reference/webhooks-assinaturas), [cancelamento](https://developer.pagbank.com.br/reference/cancelar-assinatura) e [autenticação e habilitação](https://developer.pagbank.com.br/docs/autenticacao-pagamentos-recorrentes).
- [Código de Defesa do Consumidor, art. 49](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm), [Decreto 7.962/2013](https://www2.camara.leg.br/legin/fed/decret/2013/decreto-7962-15-marco-2013-775557-publicacaooriginal-139266-pe.html) e [direitos dos titulares — ANPD](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares).
