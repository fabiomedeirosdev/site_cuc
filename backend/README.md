# Backend da Comunidade Unidos em Cristo

Base FastAPI para as integrações futuras do site.

## Executar localmente

No terminal, dentro de `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

A API ficará em `http://localhost:8000` e a documentação em `/docs`.

## Próximas integrações

- Criar checkout recorrente do PagSeguro/PagBank por plano.
- Validar o pagamento pelo webhook e pela API do PagSeguro.
- Persistir pagamentos, tokens e usuários em PostgreSQL.
- Enviar o link de cadastro com Brevo.
- Invalidar tokens após uso ou expiração.
- Implementar sessões seguras para o login.

As credenciais devem ficar apenas no arquivo `.env` do servidor. Nunca publique o `.env` nem coloque tokens no JavaScript do navegador.
