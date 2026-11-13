# API Django — ambiente local

Base Django + DRF isolada do serviço anterior em `../app/`. Consulte o
[guia da raiz](../../README.md) para preparar o PostgreSQL e iniciar a plataforma.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

- `GET /api/health`: API disponível, sem consultar o banco.
- `GET /api/ready`: consulta PostgreSQL; retorna 503 se o banco estiver indisponível.
- Demais views DRF exigem autenticação por padrão.
- E-mails ficam apenas em memória; pagamentos não estão integrados.

A Fase 3 acrescenta login por e-mail, logout, perfil, troca de senha e permissões
de consumo editorial. Consulte [autenticação e contas](../../docs/fase-3.md) para
os endpoints, a administração local e os limites preservados. Cadastro público
e recuperação por e-mail continuam fechados.

O script `../../scripts/local-postgres.ps1 start` prepara automaticamente um `.env`
local sem sobrescrever configurações existentes. Para um PostgreSQL local preparado
manualmente, use `.env.example` como referência e configure somente dados locais.
Não há fallback para SQLite: execução e testes usam PostgreSQL.

Com o PostgreSQL iniciado:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --verbosity 2
# Integração opcional com Edge; deixe a porta 5173 livre:
.\.venv\Scripts\python.exe manage.py test apps.accounts.browser_tests --noinput
```

O executor usa `test_<POSTGRES_DB>`, separado do banco de desenvolvimento. O usuário
local precisa de permissão para criar esse banco. Nenhum superusuário da aplicação,
conteúdo editorial ou dado real é criado na Fase 1.
