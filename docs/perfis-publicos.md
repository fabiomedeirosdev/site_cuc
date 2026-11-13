# Perfis da comunidade

Cada conta ativa tem um perfil público em `/perfis/<identificador>`. O identificador é um UUID independente do ID interno da conta. O diretório `/perfis.html` permite conhecer as pessoas, pesquisar por nome e filtrar por função. Está acessível a visitantes, assinantes e equipe. Contas desativadas não aparecem no diretório nem têm perfil ou foto acessível.

## Apresentação e funções

Em **Meu perfil** (`/perfil.html`), cada pessoa pode editar o nome de exibição, enviar ou remover a foto, escrever uma biografia, informar um site e incluir um vídeo de apresentação do YouTube. O vídeo é exibido dentro do site usando o reprodutor com domínio `youtube-nocookie.com`. A biografia aceita texto de até 3000 caracteres. Links de site aceitam HTTP/HTTPS sem credenciais; vídeos aceitam apenas os formatos válidos de links HTTPS do YouTube.

As funções são definidas pelo sistema, sem campo de edição no perfil:

| Identificação pública | Regra |
| --- | --- |
| Desenvolvedor | Superusuário ativo; mantém as permissões administrativas existentes. |
| Coordenador | Vínculo de coordenador em grupo ativo. |
| Auxiliar | Vínculo de facilitador em grupo ativo, sem uma coordenação de maior prioridade. |
| Assinante | Demais contas ativas. A identificação não comprova um período pago. |

Somente desenvolvedor e coordenadores podem informar telefone público, opcional. A API também verifica essa regra, e o telefone deixa de ser exibido se a pessoa perde a coordenação. Site e vídeo de apresentação estão disponíveis para todos os perfis. O e-mail de acesso, senha, dados de assinatura, permissões internas e solicitações de troca de e-mail não são publicados.

As fotos aceitam JPG, PNG e WebP de até 5 MB, mínimo de 200 × 200 px e máximo de 4096 × 4096 px; recomenda-se 600 × 600 px. O servidor remove metadados e aplica recorte central quadrado, com saída WebP de até 512 × 512 px, sem ampliar imagens pequenas. Os arquivos ficam em `PROFILE_MEDIA_ROOT`, cujo padrão local é `.local/profile-media`, fora do diretório público de mídia. A imagem é servida por `/api/profiles/<identificador>/photo`, que verifica a atividade da conta em cada requisição. Substituir ou remover a foto atualiza a apresentação pública. Não exponha o diretório de arquivos por uma rota estática.

Os cartões das equipes dos grupos mostram a foto e abrem o perfil pelo nome. As páginas de leitura de conteúdo também ligam o nome do autor ao perfil. A edição pessoal é permitida a qualquer conta autenticada, inclusive assinantes, sem conceder funções da equipe ou acesso a conteúdos exclusivos.

## E-mail de acesso

O endereço de acesso é privado. Para alterá-lo, é necessário informar a senha atual, escolher um endereço ainda não usado por outra conta e confirmar um link recebido no novo endereço. O endereço atual continua válido enquanto a confirmação não for concluída.

O link tem validade de uma hora e uso único. A URL usa um fragmento removido da barra de endereço antes da confirmação explícita por POST. Apenas o hash do token é salvo. Alterar a senha ou desativar a conta invalida a confirmação. Uma nova solicitação substitui a anterior. Os dois passos têm proteção CSRF e limite de tentativas; a unicidade do endereço também é garantida pelo PostgreSQL.

A troca preserva o ID da conta, as funções, os vínculos e os períodos pagos. A preferência de newsletter do endereço anterior é desvinculada e desativada. A autorização existente no novo endereço só pode ser vinculada após a confirmação de propriedade desse endereço. O novo endereço não é inscrito automaticamente para receber mensagens se não houver consentimento prévio.

O envio de confirmação exige SMTP e remetente configurados. Enquanto a entrega estiver indisponível, o formulário informa essa condição e mantém o e-mail atual. Os testes usam exclusivamente e-mails em memória; nenhum e-mail externo é enviado.

## Atualização e verificação

A migração `accounts.0004_public_profiles` adiciona os campos e gera um UUID diferente para cada perfil existente, preservando contas e nomes. Em produção, configure `PROFILE_MEDIA_ROOT` com um diretório privado persistente e gravável pelo Django, por exemplo `/var/lib/rhemacuc/profile-media`.

```powershell
cd E:\site_cuc\backend\django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test apps.accounts.test_public_profiles apps.accounts.tests apps.editorial.tests apps.content.tests --noinput
.\.venv\Scripts\python.exe manage.py test apps.accounts.profile_browser_tests --noinput
```

A segunda bateria testa no Edge os perfis públicos de coordenadores e assinantes, a foto e o vídeo incorporado, o telefone restrito, a identificação de desenvolvedor e a confirmação do e-mail. Usa PostgreSQL temporário, fotos geradas para teste, mensagens em memória e Vite na porta 5184. Relatório e capturas em `.local/profiles/`. O frontend é verificado com `npm test` e `npm run build`.
