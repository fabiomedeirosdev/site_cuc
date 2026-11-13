# Padronização das mídias do frontend

Validação realizada em 13/11/2026. Alterações no código-fonte; sem publicação.

## Arquivos renomeados

21 renomeações; 26 imagens mantidas. As cinco imagens já compatíveis permaneceram com seus nomes. Todos os arquivos renomeados mantêm o conteúdo binário original, conferido por SHA-256. O formato de todas as extensões foi preservado; apenas a caixa de `.JPG` foi normalizada para `.jpg`, com a renomeação registrada no índice Git para persistir no Linux.

| Caminho anterior | Caminho atual |
| --- | --- |
| `assets/images/cuc_comundad_unidos_em_cristo.png` | `assets/images/comunidade_cuc.png` |
| `assets/images/equipe_cuc.JPG` | `assets/images/equipe_cuc.jpg` |
| `assets/logo/hero-maria.jpg` | `assets/logo/hero_maria.jpg` |
| `assets/magazine/Bíblia Aberta com Cruz e Vela.webp` | `assets/magazine/biblia_cruz.webp` |
| `assets/magazine/Bíblia Aberta com Rosário de Madeira.webp` | `assets/magazine/biblia_rosario.webp` |
| `assets/magazine/Bíblia aberta com cruzes à luz dourada.webp` | `assets/magazine/biblia_dourada.webp` |
| `assets/magazine/Bíblia e Lanterna ao Entardecer.webp` | `assets/magazine/biblia_lanterna.webp` |
| `assets/magazine/Comunidade Unidos em Cristo em Dispositivos.webp` | `assets/magazine/comunidade_dispositivos.webp` |
| `assets/magazine/Contemplação ao Amanhecer Junto à Cruz.webp` | `assets/magazine/cruz_amanhecer.webp` |
| `assets/magazine/Coração vermelho entre mãos cuidadosas.webp` | `assets/magazine/coracao_maos.webp` |
| `assets/magazine/Família Unida ao Pôr do Sol.webp` | `assets/magazine/familia_unida.webp` |
| `assets/magazine/Hóstia IHS e Cálice Dourado.webp` | `assets/magazine/hostia_calice.webp` |
| `assets/magazine/Logótipos Dourados com Maria e Pomba.png` | `assets/magazine/logos_maria_pomba.png` |
| `assets/magazine/Mockup Responsivo da Comunidade Católica.png` | `assets/magazine/comunidade_responsiva.png` |
| `assets/magazine/Mãos em oração sobre a Bíblia.webp` | `assets/magazine/maos_oracao.webp` |
| `assets/magazine/Nossa Senhora ao Entardecer.webp` | `assets/magazine/nossa_senhora.webp` |
| `assets/magazine/Nossa Senhora sob o Céu Dourado.webp` | `assets/magazine/maria_ceu_dourado.webp` |
| `assets/magazine/Ondas Vermelhas em Degradé Glossy.png` | `assets/magazine/ondas_vermelhas.png` |
| `assets/magazine/Ondas Vermelhas em Degradé Glossy.webp` | `assets/magazine/ondas_vermelhas.webp` |
| `assets/magazine/Pôr do Sol Dourado junto à Cruz e à Bíblia.webp` | `assets/magazine/biblia_cruz_entardecer.webp` |
| `assets/magazine/Silhueta Dourada ao Nascer do Sol.webp` | `assets/magazine/silhueta_amanhecer.webp` |

## Referências atualizadas

- `cuc_site_estrutura.txt`: 1 referência(s).
- `docs/fase-2.md`: 2 referência(s).
- `frontend/src/assets.js`: 16 referência(s).
- `frontend/src/pages/home.css`: 1 referência(s).
- `index.html`: 1 referência(s).

São 17 referências no React/CSS e quatro no HTML legado e documentação. Os nomes exportados por `frontend/src/assets.js` foram mantidos; banners, cards, páginas e capas de grupos continuam consumindo as mesmas imagens. A tabela dinâmica de `frontend/src/group-covers.js` usa essas exportações e não precisou de alteração.

## Validação

- `npm run build`: concluído sem erros (350 módulos, 13,88 segundos).
- Vite emitiu somente aviso de bundle JavaScript acima de 500 kB; não foram alteradas configurações ou componentes para tratar esse aviso.
- 22 caminhos literais locais de imagens conferidos no React/CSS, incluindo correspondência exata de maiúsculas e minúsculas.
- Nenhuma referência aos caminhos anteriores encontrada nos arquivos de texto do projeto fora do backend e deste relatório, incluindo caminhos codificados para URL.
- `frontend/dist/assets`: 22 imagens, um CSS e um JavaScript. Todos com nomes ASCII, sem espaços ou acentos e sem colisões de caixa. Os hashes, hífens e letras maiúsculas acrescentados pelo Vite foram preservados e são compatíveis com Linux.
- 19 referências a arquivos de `dist/assets` conferidas no HTML, CSS e JavaScript gerados.
- As quatro imagens próprias não importadas pelo frontend também foram renomeadas e preservadas na origem; o Vite continua incluindo no build apenas os arquivos utilizados.
- URLs externas, imagens recebidas da API e uploads de perfis, grupos e conteúdo foram preservados. Caminhos armazenados no banco ou retornados pela API não foram migrados nem validados em produção.
- Nenhuma alteração no backend Django, VPS, banco, dependências, layout ou identidade visual.

## Referências preexistentes fora do React

O `index.html` legado da raiz (e sua cópia em `cuc_site_estrutura.txt`) já contém seis caminhos de imagens inexistentes: `assets/logo/hero-irh.png`, `assets/video-thumb.png`, `assets/quem-somos.jpg`, `assets/fundadores-1.jpg`, `assets/fundadores-2.jpg` e `assets/sede.jpg`. Foram mantidos, pois não correspondem aos arquivos renomeados nem fazem parte do build React; o mapeamento de substituições usado pelo React está documentado em `docs/fase-2.md`.

Não restaram referências locais pendentes decorrentes destas renomeações. Não houve publicação nem validação direta na HostGator.
