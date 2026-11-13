# Domínio de produção: rhemacuc.com.br

O endereço principal será `https://rhemacuc.com.br`. O site e o backend compartilham a mesma origem:

| Recurso | Produção | Computador |
| --- | --- | --- |
| Site | `https://rhemacuc.com.br` | `http://127.0.0.1:5173` |
| API | `https://rhemacuc.com.br/api/...` | `/api/...` no Vite, encaminhado para `127.0.0.1:8000` |
| Fotos enviadas | `https://rhemacuc.com.br/media/...` | `/media/...` pelo proxy do Vite |
| Administração | `https://rhemacuc.com.br/admin/` | `http://127.0.0.1:8000/admin/` |

## Frontend

Manter `VITE_API_BASE_URL` vazio. As chamadas relativas `/api/...` usam o domínio aberto no navegador, preservando sessão e proteção CSRF. Assim, o build de produção não precisa conter `localhost`, nem fazer chamadas do computador para dados reais. O proxy de desenvolvimento continua restrito ao Django local.

O exemplo público está em `frontend/.env.production.example`. Conferir se o ambiente de compilação, `.env` ou `.env.local` do frontend não sobrescrevem `VITE_API_BASE_URL` com um endereço local ou de outro serviço. Gerar o build com `npm run build`.

## Backend

No servidor, usar `backend/django_platform/.env.production.example` como modelo do `.env`, preenchendo a chave secreta, PostgreSQL e os dados reais dos serviços. O arquivo privado de desenvolvimento no computador permanece intacto. Não enviar o `.env` local para produção.

O modelo configura `DJANGO_DEBUG=0`, hosts permitidos, CSRF, cookies HTTPS e:

```dotenv
PUBLIC_FRONTEND_URL=https://rhemacuc.com.br
PUBLIC_API_URL=https://rhemacuc.com.br
```

Essas URLs também são usadas no retorno do checkout, convites de cadastro, confirmação e descadastro de newsletter e links das edições. As configurações de produção têm esse domínio como padrão quando não há variáveis explícitas. Variáveis já existentes no servidor prevalecem, portanto precisam ser conferidas na instalação.

## Proxy e arquivos

`deploy/nginx/rhemacuc.conf` é um exemplo para Nginx/Linux. Ele serve `frontend/dist`, encaminha `/api/` e `/admin/` para o backend em `127.0.0.1:8000`, serve `/media/` e `/static/` e mantém o fallback das páginas React. O prefixo `/api/` é preservado ao encaminhar a requisição. O endereço com `www` e o HTTP redirecionam para o domínio principal com HTTPS.

Ajustar diretórios conforme a hospedagem. O exemplo usa `/srv/rhemacuc/frontend/dist`, `/var/lib/rhemacuc/media` e `/var/lib/rhemacuc/static`. Criar as pastas e conceder ao processo da aplicação as permissões necessárias para gravar uploads e estáticos. No ambiente de produção, aplicar as migrações e executar `python manage.py collectstatic --noinput`.

O backend deve ser iniciado por um servidor WSGI/ASGI de produção e ficar acessível somente pelo proxy, sem publicar a porta 8000 na internet. O exemplo de Nginx sobrescreve `Host` e os cabeçalhos de protocolo e IP. `DJANGO_TRUST_PROXY_HEADERS=1` habilita a leitura do protocolo HTTPS encaminhado por esse proxy. Não habilitar essa confiança se a aplicação estiver diretamente exposta a clientes que possam definir os cabeçalhos. Essa distinção evita redirecionamentos HTTPS em ciclo e mantém cookies e verificações de origem corretos. Referências: [configuração do Django](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header) e [proxy do Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).

Instalar um certificado TLS válido para `rhemacuc.com.br` e `www.rhemacuc.com.br` antes de habilitar os blocos HTTPS. O exemplo usa os caminhos usuais do certificado em `/etc/letsencrypt/live/rhemacuc.com.br/`. Os caminhos devem corresponder ao certificado efetivamente instalado. Executar `nginx -t` no servidor antes de aplicar a configuração. Não foi possível executar essa verificação de Nginx neste ambiente Windows.

## PagBank e newsletter

O webhook do produto Assinaturas deve ser cadastrado no PagBank com:

```text
https://rhemacuc.com.br/api/billing/webhooks/pagbank
```

O retorno do checkout usa `https://rhemacuc.com.br/pagamento-pendente.html`. Os convites usam `/cadastro.html#convite=...` e a newsletter usa `/newsletter.html#confirmar=...` ou `#sair=...`, sempre no domínio público configurado.

Cobranças e newsletter continuam desativadas por padrão. Configurar credenciais, atendimento, SMTP e homologação conforme as fases 6 e 7; manter as rotinas `process_billing` e `process_newsletters` agendadas no servidor. A configuração do domínio não ativa pagamentos nem mensagens por si só.

## Verificação antes de disponibilizar

Depois de apontar o DNS, instalar o certificado e iniciar frontend/proxy/backend, conferir no domínio real:

- `/api/health` e `/api/ready` respondem JSON com HTTP 200; `/api/ready` também verifica o banco.
- Login, perfil e assinatura continuam no domínio principal e mantêm a sessão.
- Upload e exibição de uma capa funcionam por `/media/`.
- Links de cadastro e newsletter usam HTTPS e o domínio correto.
- O PagBank consegue entregar o webhook sem redirecionamento.

Esta entrega prepara os arquivos e valida o comportamento da aplicação localmente. Não altera DNS, certificados, hospedagem ou cadastros do PagBank e não comprova uma publicação já concluída.

Validação da aplicação: 121 testes Django aprovados, incluindo os cenários de host, HTTPS encaminhado, cookies e CSRF no domínio de produção. Os 8 testes do cliente e o build do frontend também passaram. O arquivo de Nginx ainda exige `nginx -t` e conferência dos caminhos e certificados na hospedagem real.
