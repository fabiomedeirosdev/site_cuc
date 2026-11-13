# Painel de administração da CUC

O painel fica em `/painel`, no mesmo domínio do site. Após entrar, a equipe também pode acessá-lo pelo botão **Abrir painel de administração** na área da conta.

A identificação pessoal dos superusuários é **Desenvolvedor**, definida pelo sistema. O menu **Meu perfil** permite editar a apresentação pública. Consulte [perfis públicos](perfis-publicos.md) para fotos, biografias, contatos e troca de e-mail.

O painel usa o logo, vermelho, dourado, fundo claro e títulos do site. O menu está presente na visão geral, no editor, na gestão dos conteúdos, grupos, equipes, agenda, mural, newsletter, usuários, assinaturas e atendimentos. Em telas pequenas, o menu permite rolagem horizontal. As páginas técnicas em `/admin/` também herdam a identidade visual, com um link para o painel.

## O que cada perfil controla

| Perfil | Acesso |
| --- | --- |
| Administrador (superusuário ativo) | Indicadores gerais, conteúdos, destaques, páginas dos grupos, equipes, comunicação, consulta de usuários e assinaturas, suspensão/reativação de contas comuns e conclusão de atendimentos. |
| Coordenador com vínculo em grupo ativo | Indicadores e conteúdos do seu escopo, seleção e ordem dos destaques dos grupos que coordena, apresentação dos grupos, equipe e comunicação conforme as permissões existentes. |
| Facilitador com vínculo ativo | Indicadores e conteúdos que pode editar. Comunicação quando houver delegação válida. Não escolhe destaques. |
| Assinante | Área da conta e conteúdos liberados pelo período pago. Não acessa a administração. |

As permissões são verificadas pelo Django a cada requisição. A interface não concede funções administrativas. Contas de equipe com `is_staff`, superusuários e a própria conta administrativa são protegidas contra suspensão pelo painel.

## Criar grupos e escolher capas

Administradores e coordenadores com vínculo em grupo ativo podem usar **Criar novo grupo**, disponível no catálogo de grupos, na gestão de equipes e em **Páginas dos grupos**. O formulário também pode ser aberto em `/painel/grupos/novo`. Facilitadores, assinantes e visitantes não têm permissão para criar grupos. Um coordenador que cria um grupo recebe automaticamente um vínculo privado de coordenador nesse grupo e pode gerenciar sua página e equipe.

Informe o nome e a apresentação. Em **Enviar imagem do grupo**, use **Escolher foto do grupo** para enviar a capa. O formulário oferece apenas upload; grupos existentes mantêm suas capas até que uma nova foto seja enviada. A imagem aparece no catálogo, na página do grupo e nos cartões da home quando o grupo estiver entre os primeiros quatro grupos ativos. A ordem de exibição e a ativação permanecem sob controle do administrador.

O upload aceita **JPG, PNG e WebP**, com arquivo de **até 5 MB**, dimensões mínimas de **800 × 450 px** e máximas de **4096 × 4096 px**. O tamanho recomendado é **1600 × 900 px**. A imagem recebe um recorte central em **16:9**, sem ampliar imagens menores, é convertida para WebP e tem os metadados removidos. A descrição da foto própria é obrigatória para acessibilidade. Os limites são informados abaixo do campo e validados no backend, incluindo o conteúdo real do arquivo.

A migração `editorial.0004_group_custom_cover` acrescenta a capa própria e sua descrição, preservando as imagens e os grupos atuais. Se o backend foi iniciado com `--noreload`, reinicie-o após atualizar o código. Os testes de criação, permissões e imagens são executados com:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.editorial.test_group_creation apps.editorial.tests apps.core.test_management --noinput
.\.venv\Scripts\python.exe manage.py test apps.editorial.group_browser_tests --noinput
```

O segundo comando verifica no Edge, em quatro tamanhos de tela, a criação por um coordenador, a correção de uma foto pequena demais, a exibição da foto na home e a substituição da capa por uma nova foto. Os relatórios e capturas ficam em `.local/groups-live/`.

## Escolher um destaque

1. Acesse **Destaques do site**.
2. Escolha um conteúdo publicado, com capa, em um grupo ativo.
3. Marque **Exibir em destaque na página inicial**.
4. Informe a **Ordem no carrossel** e clique em **Salvar destaque**.

Números menores aparecem primeiro; empates usam a publicação mais recente e o ID. O carrossel consulta os destaques salvos e abre a página do conteúdo. O resumo e a capa de conteúdos exclusivos podem aparecer, mas a leitura integral continua exigindo assinatura. Rascunhos, grupos desativados e conteúdos de autores sem autorização não são exibidos. Desmarcar o destaque e salvar retira o conteúdo do carrossel. Quando não há destaques disponíveis, o carrossel mantém as apresentações institucionais do site.

Os indicadores são contagens reais consultadas na API. O gráfico mostra publicações por mês nos últimos seis meses; não representa visitas. A consulta de assinaturas não altera períodos pagos. Marcar um atendimento como concluído registra o atendimento e não executa reembolso ou exclusão de dados.

## Atualização e validação

No diretório `backend/django_platform`, com o ambiente virtual configurado:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py test apps.core.test_management apps.content.tests apps.accounts.tests apps.editorial.tests apps.communications.tests --noinput
.\.venv\Scripts\python.exe manage.py test apps.core.management_browser_tests --noinput
```

No diretório `frontend`:

```powershell
npm test
npm run test:management
npm run build
```

A migração `content.0002_article_highlights` adiciona a seleção e a ordem dos destaques, sem selecionar publicações existentes automaticamente. O teste `management_browser_tests` usa contas e PostgreSQL temporários para validar login, seleção pelo administrador, exibição na home, proteção da leitura exclusiva e retirada pelo coordenador. A bateria de interface usa respostas controladas para conferir as telas e os controles em quatro tamanhos. Relatórios e capturas ficam em `.local/management/` e `.local/management-live/`.
