# Gestão de membros e funções

Desenvolvedores e fundadores podem editar nome, e-mail, biografia, site, vídeo de apresentação, função geral e ordem de exibição em **Equipes e permissões → Membros da Comunidade** (`/gestao-grupos.html`). A página **Painel → Usuários** também oferece acesso à edição e à exclusão.

A exclusão exige confirmação na interface, remove a conta e os vínculos e interrompe o recebimento da newsletter. Os registros de pagamentos, aceites, publicações e comunicações são preservados sem vínculo com a conta excluída. Publicações sem autor deixam de aparecer na leitura pública. A própria conta não pode ser excluída por esse painel. Contas de desenvolvedores e a atribuição dessa função continuam restritas a desenvolvedores.

| Função geral | Permissões |
| --- | --- |
| Desenvolvedor(a), Fundador(a) | Gestão de membros, dados, funções e ordem de exibição, incluindo outros fundadores. |
| Administração | Permissões de coordenação nos grupos vinculados, criação de grupos e gestão de comunicação; sem gestão geral de usuários. |
| Padre, Diácono | Permissões de facilitador: criação e edição de conteúdos nos grupos vinculados e comunicação conforme delegação. |

Os vínculos existentes com grupos permanecem ao editar a função geral. A função de coordenador de um grupo é editada na equipe desse grupo. As funções não liberam conteúdos exclusivos sem assinatura válida.

Antes de executar a versão atualizada do backend, aplique as migrações:

```powershell
cd E:\site_cuc\backend\django_platform
.\.venv\Scripts\python.exe manage.py migrate
```

As migrações incluem as opções de função e permitem preservar registros históricos após excluir uma conta.

Verificação das permissões e da exclusão:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.core.test_member_management apps.core.test_management apps.core.test_community_improvements --noinput
```
