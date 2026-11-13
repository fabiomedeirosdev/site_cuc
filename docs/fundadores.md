# Página dos fundadores

A página pública fica em `/fundadores.html`, acessível pelo menu **Sobre → Fundadores** da home e pelos links **Fundadores** e **Nossa História** no rodapé. Ela usa o visual da comunidade e apresenta a foto, o título e a história com os parágrafos escritos no painel.

O desenvolvedor edita em **Painel → Fundadores** (`/painel/fundadores`). É possível alterar o título, escrever a história, escolher uma nova foto e editar a descrição da imagem. **Salvar e publicar** atualiza a página pública. Editar apenas o texto mantém a foto atual. O formulário preserva o texto quando o salvamento falha.

O conteúdo inicial usa o texto já existente no site. Enquanto não houver foto enviada, a página utiliza `assets/images/fundadores_comunidade_cuc.png`. Uploads aceitam JPG, PNG ou WebP de até 5 MB, com mínimo de 600 × 300 px e máximo de 4096 × 4096 px; o tamanho recomendado é 1200 × 800 px. A proporção é preservada, sem recorte. O servidor remove os metadados e normaliza a foto para JPEG de até 2000 px em cada lado, sem ampliar imagens pequenas.

A API pública é `GET /api/founders`. A edição usa `GET/PATCH /api/management/founders`, restrita a superusuários ativos e protegida por sessão e CSRF. Coordenadores, auxiliares, assinantes e visitantes podem ler a página pública, mas não editá-la. O responsável pela última edição é registrado no banco sem ser exposto na resposta pública.

A migração `core.0001_founders_page` cria e preenche a página única, sem alterar os conteúdos das outras áreas. Aplicação e verificações:

```powershell
cd E:\site_cuc\backend\django_platform
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test apps.core.test_founders apps.core.test_management --noinput
.\.venv\Scripts\python.exe manage.py test apps.core.founders_browser_tests --noinput
```

A bateria no Edge usa banco, contas e fotos temporários. Verifica o dropdown, o login do desenvolvedor, o salvamento da foto e da história e o acesso de visitantes, em quatro tamanhos de tela. Relatório e capturas ficam em `.local/founders/`.
