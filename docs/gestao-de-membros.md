# Gestão de membros e funções

**Equipes e permissões → Membros da Comunidade** (`/gestao-grupos.html`) mantém o cadastro de integrantes com nome, e-mail, senha inicial, grupo e função. Nenhuma lista geral ou formulário de edição é aberto nessa área. A busca apresenta somente resultados compactos e paginados, com acesso ao cadastro da pessoa selecionada.

Desenvolvedores e fundadores editam nome, e-mail, biografia, site, vídeo de apresentação, função geral e ordem de exibição em **Painel → Usuários → Editar dados e função**. A rota `/painel/usuarios/:id/editar` carrega e salva exclusivamente o usuário escolhido. A exclusão continua em **Painel → Usuários**. O formulário pessoal **Meu perfil** permanece como está.

A exclusão exige confirmação na interface, remove a conta e os vínculos e interrompe o recebimento da newsletter. Os registros de pagamentos, aceites, publicações e comunicações são preservados sem vínculo com a conta excluída. Publicações sem autor deixam de aparecer na leitura pública. A própria conta não pode ser excluída por esse painel. Contas de desenvolvedores e a atribuição dessa função continuam restritas a desenvolvedores.

| Função geral | Permissões |
| --- | --- |
| Desenvolvedor(a), Fundador(a) | Gestão de membros, dados, funções e ordem de exibição, incluindo outros fundadores. |
| Administração | Permissões de coordenação nos grupos vinculados, criação de grupos e gestão de comunicação; sem gestão geral de usuários. |
| Padre, Diácono | Permissões de facilitador: criação e edição de conteúdos nos grupos vinculados e comunicação conforme delegação. |

Em **Editar usuário → Participação nos grupos**, escolha o grupo e a função de Coordenador(a) ou Facilitador(a). Os vínculos existentes aparecem preenchidos; é possível alterar a função, adicionar outro grupo ou remover um vínculo antes de salvar. Os dados, a função geral e os vínculos são salvos juntos. A apresentação e a visibilidade dos vínculos mantidos são preservadas. Alterar somente a função geral não muda os vínculos. As funções não liberam conteúdos exclusivos sem assinatura válida.

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
