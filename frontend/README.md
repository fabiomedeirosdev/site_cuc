# Frontend local — React + Vite

Aplicação isolada do site estático original. As páginas React reaproveitam
`../css/style.css` e `../assets/`. A comparação com os originais e as decisões
preservadas estão documentadas em [Fase 2](../docs/fase-2.md).

```powershell
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173`. Inicie Django na porta 8000 conforme o
[guia da raiz](../README.md). O proxy Vite encaminha `/api` para a API local.
Não é necessário criar `.env` no frontend. Para outra origem local, consulte
`.env.example`; variáveis `VITE_` são públicas e nunca devem conter segredos.

`src/api.js` exporta as consultas de saúde e disponibilidade do banco para uso
em React. O cliente aceita cancelamento via `AbortSignal`, propaga erros de rede
e rejeita respostas HTTP de erro.

```powershell
npm test
npm run test:routes
npm run test:browser
npm run build
# Requer Django e PostgreSQL iniciados:
npm run test:api
```

Os testes de navegador usam o Microsoft Edge instalado e iniciam seu próprio Vite;
deixe a porta 5173 livre. Validam quatro larguras, conteúdo original, aparência e
interações, bloqueando serviços externos. Cadastro e recuperação de senha por
e-mail permanecem indisponíveis. A saída `dist/` não é publicada nesta etapa.

Na Fase 3, o login passou a autenticar no Django, com sessão em cookie protegido,
CSRF, área do associado restrita e página de perfil/troca de senha. Cadastro público
e recuperação por e-mail permanecem indisponíveis. A integração real no Edge é
iniciada pelo Django em um banco temporário; veja [Fase 3](../docs/fase-3.md).
