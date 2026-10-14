# Ideias tiradas do Huntera (exploração só de leitura, conta do Lubra)

## Caçada
- **Janela "Aventuras"** com abas: Caçadas · Bosses · Quests · Arena · Treino.
- **Catálogo de caçadas numeradas** (81), com busca, favoritos (estrela) e "Encontrar time".
- **Preparar a caçada** antes de iniciar:
  - Tamanho do pull: Cauteloso / Ousado / Agressivo (quantos monstros puxa por vez).
  - Monstros daquele pull.
  - Loot possível com raridade (Comum, Incomum, Semi-raro), ordenável por valor no NPC ou por peso.
  - Duas caixas por item: **PEGAR** e **VENDER** (venda automática). Substitui a regra única de "pegar lixo".
  - **Recorde pessoal** por hunt, a partir de uma caçada de 5 minutos.
- **Postura:** Defesa total / Equilibrado / Ataque total.
- **Distância dos inimigos:** 1 = perseguir; 2 a 4 = manter distância (paladinos e magos).
- **Alvo:** Mais próximo, Boss, Seguir o líder, Menor/Maior vida, Menor/Maior % de vida.

## Hotbar
- **Builder da action bar:** conjuntos por vocação com postura, alvo e distância; "Ordenar automaticamente"; **copiar e importar conjunto por código** (compartilhar build).
- **Barra de regras nos slots de equipamento:** troca peças sozinha nas lutas (ex.: anel ou amuleto só quando o HP cai).

## Bosses, Quests, Arena
- **Bosses diários** (Faceless Bane, Timira, Urmahlullu…) com salas em grupo, roteiros, invasões e recompensas.
- **Quests clássicas** viradas em missões com contagem de kills (ex.: 0/2.500) e salas.
- **Arena:** 10 bosses em sequência, 5 minutos por boss, taxa de entrada.

## Treino (ótimo para idle)
- Escolher a skill (club, sword, axe, distance, shielding, magic).
- **Treino online** num boneco, no dobro do ritmo de uma caçada.
- **Treino offline** na metade do ritmo, por até 12 h.
- **Treinar sozinho** depois de 2 minutos parado na cidade.
- Armas de exercício (com cargas).

## Prey
- Slot com criatura, bônus (dano, exp, loot, defesa) e **nível em estrelas (1 a 10)**, além do tempo restante em barra.
- **Wildcards:** trocar o bônus, lista nova grátis, troca automática do bônus, travar a criatura.
- 3 slots: 1 grátis, 1 premium, 1 comprado.

## Cyclopedia (wiki dentro do jogo)
- Itens (1.031) por categoria, com ataque, defesa e peso, **"dropado por"** com link para o monstro e "ver no leilão".
- Bestiary e Bosstiary.

## Personagem
- Abas: Personagem, Outfit, Proficiência, Deaths.
- **Detalhes de combate:** dano mín–máx, armadura, defesa, crítico, life e mana leech, efeitos da forja, dano por tier e por bestiário.
- **Proteções por elemento** (físico, fogo, gelo, terra, energia, morte, sagrado).
- **Bônus de exp detalhado:** bestiário, guild, level, scroll, premium.
- Progresso do bestiário (x/186).

## Economia e sistemas
- **Forja:** fusão de 2 itens iguais vira o tier seguinte. Custa gold + dust; o exalted core sobe a chance de 50% para 65%. Na falha, ninguém perde item. Efeitos: Onslaught, Ruse, Momentum, Transcendence.
- **Imbuements:** só nos itens com slots (ex.: Sword com 2 slots), nos níveis Basic, Intricate e Powerful, com o custo mostrado antes.
- **Guia** de várias páginas na primeira vez que se abre um sistema.
- Ranking por level, magic level, cada skill e **fishing**; ranking de guilds.
- Stamina comprável com gold; venda rápida com prévia do que vai ser vendido.

## Durante a caçada (observado caçando em Rotworm Caves com o Lubra, Paladin lv 21)
- **Indo até a hunt:** o personagem **anda pela cidade até um portal** ("Indo até o portal da caçada…", com Cancelar), em vez de teletransportar. A cidade tem gráfico completo (muros com bordas certas, placas, postes, canteiros, escadas).
- **Botões da caçada** (no lugar dos da cidade): Detalhes da caçada · Despachar loot · Sair da caçada. Dá para mudar PEGAR e VENDER do loot sem sair da hunt.
- **Loot da sessão:** janela no canto com "clique para pegar — expira em 15 min".
- **Iluminação de caverna:** escuro com uma luz quente em volta do personagem e áreas claras onde entra luz de cima.
- **Personagem:** passos animados (as pernas trocam a cada passo), vira para a direção em que anda e a câmera desliza suave seguindo.
- **Monstros:** sprites grandes; o alvo fica com quadrado vermelho, nome em verde e barra de vida pequena em cima.
- **Números:** dano em vermelho subindo em cima do monstro; **"+109 XP" em branco ao lado do personagem** (no nosso jogo a exp aparece em cima do monstro).
- **Restos:** cadáveres, poças de sangue e pedregulhos ficam no chão por um tempo; buracos (tocas) de onde os rotworms saem.
- **Log de combate** em aba própria do chat (estava vazio neste personagem).
- **Analisador de caçada** (exp/h, lucro/h, próximo level) é só para premium.
- Não deu para ver magias: a hotbar do Lubra está vazia, então ele só usa o ataque básico à distância (a flecha voa rápido demais para aparecer nas capturas).

## Gráfico e animação (andando por Thais com o Lubra)
- **De onde vêm os gráficos:** o Huntera baixa os arquivos oficiais do cliente moderno do Tibia, versão 13.32:
  - `things/1332/catalog-content.json`;
  - `appearances-….dat` (protobuf com a definição de cada item, outfit e efeito);
  - ~170 folhas `sprites-….bmp.lzma`.
  
  É por isso que Thais fica idêntica à original: cada item do mapa usa o sprite exato do cliente, com bordas, muros e telhados certos. O mapa deve vir de um servidor tipo Canary, cujos ids de item são os mesmos do cliente.
- **Andar:** WASD anda um tile por vez e clicar no chão leva o personagem até lá. O deslize entre tiles é contínuo, a câmera fica presa no personagem e as pernas trocam durante o passo.
- **Thais:** calçamento de pedra, casas de enxaimel (madeira e reboco) com janelas e escadas encostadas, postes de luz, canteiros de grama com bordas suaves e placas. Tudo é sprite do cliente, sem nada desenhado à mão.

## O que aplicamos no nosso jogo
- Personagem com a roupa do **Tibia 7.4**, que tem quadros de andar de verdade:
  - 4 direções × 3 fases (parado + 2 passos);
  - colorida pela máscara com a paleta de 133 cores, como no cliente;
  - gerada por `ferramentas/gerar_roupas74.py`.
- As pernas trocam a cada meio passo, e parado volta à fase 0.
- A posição desenhada segue o relógio real (60 fps), não os degraus de 100 ms da simulação. Passos seguidos emendam sem pausa. Vale também para os monstros.
- WASD para andar à mão; o automático volta 3 s depois da última tecla.

## Prioridade sugerida para o nosso jogo
1. Tela "Preparar caçada" (pull + loot com PEGAR/VENDER + recorde de 5 min).
2. Postura e distância dos inimigos, e mais modos de alvo.
3. Treino (online, offline e automático quando parado na cidade).
4. Janela de personagem com detalhes de combate e bônus de exp detalhado.
5. Prey com estrelas e wildcards.
6. Cyclopedia com "dropado por".
7. Forja por fusão de itens iguais + efeitos.
8. Arena de bosses em sequência.
