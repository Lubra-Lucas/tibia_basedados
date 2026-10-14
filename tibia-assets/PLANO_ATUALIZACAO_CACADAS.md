# Plano: 100 caçadas em mapas reais, novo visual de caçadas e prey, mercado, leilão e wiki

Jogo: `E:\TIBIA SITE\tibia-idle-2d.html` (um arquivo, JS inline). Dados e ferramentas em `tibia-assets/` e `tibia-assets/ferramentas/`.
Execução em 3 etapas sequenciais (o arquivo do jogo é um só; não editar em paralelo).

## Base que já existe (reaproveitar)
- Leitura de mapas: `ler_otbm.py`, `ler_items_otb.py` (id servidor TFS 10.98 → id cliente), `renderizar_otbm.py` (classe `Pintor`), `exportar_mapa15.py` (exporta um andar/recorte para o jogo como mapa próprio: atlas PNG + `mapas15/<chave>.js` com `MAPAS[chave]` e `MAPAS_SPRITES.tiles`; já sabe colocar spawns `--spawns mob:n` e área andável).
- Cliente 15.01: `ler_dat_moderno.py` (`DatModerno`, `SprModerno`), `gerar_sprites15.py` (`Gerador.folha_criatura`, `folha_item`), `gerar_combate15.py` (`ler_monstro` lê ataques/defesas/elementos/invocações de um .lua do Canary; `invocaveis()` mostra como baixar .lua de monstros com cache em `dados/canary_magias/monstros/`).
- Catálogo: `dados/catalogo_monstros.json` (1.651 monstros com sprite: nome, pasta, arquivo, hp, exp, estrelas, look, quadros_andar, no_jogo) e `dados/monstros_canary.json` (lookType, cores, addons, cadáver, raceId, arquivo .lua).
- Itens: `dados/_items.xml` (Canary, ids = cliente: nome→id), `dados/_precos_npc.json` (preços de venda NPC), `dados_jogo.js` (`TD.itens`, `TD.mobs`, `TD.hunts`).
- Mapas baixados: `E:\TIBIA SITE\MAPAS\mapas1\*.otbm` (113), `MAPAS\Classicos\Thaismap.otbm` (continente de Thais 8.6), `dados/inventario_mapas.json` (raio-x). Todos traduzem com o items.otb 10.98.
- No jogo: `HUNTS` (montado de `TD.hunts` + `HUNT_PROPRIA` com mapas próprios), `MOBS`, `ITEMS`, `buildWorld/ensureRegion` (mapa próprio síncrono via `MAPAS[...]`), `killMob` (loot), regras `S.rules`, prey `S.prey`, `MODALS.hunts`, `MODALS.prey`, motor de combate 15.01 (`COMB15`, `MAGIAS15`, `RUNAS15`, `ataque15` para monstros com `atq15`).

## Etapa 1: dados e motor das 100 caçadas
1. **Escolher 100 monstros** de dificuldade crescente, do level 1 ao 1000:
   - fontes: monstros de Bestiário do Canary (raceId e estrelas, sem bosses, raids, eventos, armadilhas, familiares e treinos). Monstros de "quests" podem entrar se forem de Bestiário;
   - prefira sprites com 8 quadros de andar e variedade visual (não 10 trolls seguidos);
   - level recomendado: curva monotônica pela experiência, de 1 a 1000;
   - cada caçada tem 1 monstro principal e, se fizer sentido, 1 a 2 companheiros da mesma família.
2. **Nome e descrição** no estilo "Rat Cellars", "Spider Nest", "Troll Hills", "Orc Camp" (nome em inglês, descrição curta em português), numeradas HUNT 01…100.
3. **Mapas**:
   - montar uma ferramenta que encontra regiões caçáveis nos .otbm (área andável conectada de cerca de 250 a 1.500 tiles), classifica o bioma pelo chão dominante (grama, terra/caverna, areia, neve/gelo, pântano, lava/inferno, pedra/tumba, água/costa, construção) e marca se é subsolo;
   - etiquetar cada monstro com um bioma (pasta e nome do Canary: frost/ice → neve; scarab/mummy/desert → deserto; swamp/bog → pântano; demon/fire/hell → lava; undead → tumba; aquatic/deepling/quara → costa; insetos/vermes → caverna; mamíferos/humanos/orcs → grama, etc.);
   - associar cada caçada a uma região do bioma certo. Pode repetir região; não precisa usar o mapa todo;
   - exportar com o `exportar_mapa15` (recorte + andar). Regiões do mesmo .otbm podem compartilhar atlas.
4. **Tamanho e carregamento**:
   - nada de `<script>` fixo para 100 mapas: carregar o .js do mapa só ao entrar na caçada (injeção dinâmica + `await`);
   - medir o tamanho total gerado e mirar menos de ~120 MB em `mapas15/`.
5. **Pull (Cauteloso / Ousado / Agressivo)**:
   - a quantidade de spawns e o tamanho do grupo crescem conforme o modo (ex.: 6/10/16 pontos de spawn, 1/2/3 monstros por ponto);
   - escolhido na tela de preparo e salvo em `S.pull[hunt]`.
6. **Dados de cada monstro novo**:
   - baixar o .lua do Canary (com cache) e montar `MOBS[id]` completo: vida, exp, velocidade, armadura, elementos, ataques e defesas (`atq15`/`def15` para usar o `ataque15`), invocações, cadáver e loot com chance e quantidade máxima (`monster.loot`);
   - gerar a folha de sprite do 15.01 (`gerar_sprites15`) e o cadáver.
7. **Itens do loot**:
   - todo item do loot vira `ITEMS[...]` com nome, peso, preço de NPC (`_precos_npc.json`; se faltar, estimar) e ícone do 15.01 em `sprites15/itens/<id>.png` (nome → id pelo `_items.xml`);
   - aproveitar e gerar ícone 15.01 para todos os itens do jogo (equipamentos e poções) via `it.icone`, aposentando os ícones do TibiaWiki quando houver.
8. **Loot PEGAR / VENDER**:
   - configuração por item em `S.lootCfg[itemId]={pegar,vender}`;
   - no `killMob`: se "pegar" estiver desligado, não pega. Se "vender" estiver ligado, vira gold na hora pelo preço de NPC (sem peso) e conta como lucro;
   - padrão: pegar tudo com valor, vender o que não for material de imbuement nem equipamento melhor que o atual.
9. **Recorde**: os primeiros 5 minutos de cada caçada medem exp/h e lucro/h; o melhor fica em `S.recordes[hunt]`.
10. **Substituir as caçadas antigas**:
    - as 52 do tibia-map-data e a cave de rotworm 7.4 saem; a Hellgore pode virar uma das 100;
    - saves antigos: `S.loc`/`S.lastHunt` inválidos voltam para a cidade.
11. **Teste**: cada uma das 100 caçadas carrega, tem monstros andáveis e roda 2 min simulados sem erro com um personagem do level recomendado.

## Etapa 2: telas de caçada e prey
1. **Lista de caçadas** (como a imagem de referência):
   - grade de cards "HUNT 01 / nome / monstros" com o monstro animado (canvas tocando os quadros parado e andando), estrela de favorito e rodapé com o recorde ("Sem recorde ainda");
   - abas Caçadas · Bosses · Quests · Arena · Treino (as que não existem mostram "em breve"; Arena abre a arena);
   - busca, filtro por level ("só do meu level") e favoritos primeiro.
2. **Tela "Prepare sua caçada"**:
   - cabeçalho com o monstro animado, nome, estrela, descrição, level recomendado e "Seu recorde";
   - "Tamanho do pull": Cauteloso / Ousado / Agressivo;
   - "Monstros deste pull" com animação e quantidade;
   - "Loot possível": ícone, nome, raridade pela chance (Comum, Incomum, Semi-raro, Raro, Muito raro), caixas PEGAR e VENDER que gravam em `S.lootCfg`, ordenação por Valor NPC ou Peso;
   - rodapé "Iniciar caçada";
   - manter o conjunto sugerido de magias da etapa anterior (botão ou seção).
3. **Prey** (como a referência):
   - 3 slots: slot 1 livre; slot 2 "premium", liberado com gold; slot 3 "loja", liberado para sempre com Tibia Coins (TC) do mercado;
   - cada slot ativo mostra o monstro animado, o bônus (dano, defesa, exp ou loot) com %, estrelas de 1 a 10, barra de tempo restante, "Trocar o bônus — 1 wildcard", "Nova lista — grátis" (com recarga) ou com wildcard, e as opções "Troca automática do bônus" e "Travar a prey";
   - topo com wildcards (x/1000) e gold;
   - wildcards: ganhar alguns por dia de caçada e comprar com gold.
4. Visual escuro, bordas finas e títulos em Cinzel, coerente com o cabeçalho novo (ícones 15.01, sem emoji).

## Etapa 3: mercado, leilão e wiki
1. **Mercado** (menu ECONOMIA), como a referência:
   - **Abas:** Itens · Coin Market · Histórico.
   - **Itens:** busca em todos os itens do jogo; livro de ofertas de compra e venda simulado em volta do preço de NPC e da raridade; comprar e vender na hora; criar ordem com taxa de 5%, que se preenche aos poucos com o tempo (inclusive offline).
   - **Coin Market:** Tibia Coin (TC) contra ouro, com livro de ordens e preço oscilando. TC serve para o slot 3 da prey e outras liberações.
   - **Histórico:** suas transações.
   - **Topo:** TC, ouro e capacidade livre.
   - **Origem dos itens vendidos:** mochila e depot.
2. **Leilão**:
   - itens raros (raridade baixa ou valor alto) em leilão com contagem regressiva e lances de compradores simulados;
   - o jogador dá lance com ouro, ou põe um item raro dele em leilão e recebe o lance final menos a taxa.
3. **Wiki** (menu próprio no cabeçalho):
   - **Monstros:** sprite animado, vida, exp, velocidade, armadura, tabela de elementos, ataques, loot com chances e ícones, "onde encontrar" (caçadas).
   - **Itens:** ícone, tipo, atributos, peso, preço NPC, preço de mercado, "dropado por" (com link para o monstro).
   - **Magias:** por vocação, com level, mana, recarga e tipo.
   - **Caçadas:** lista com level e monstros.
   - Busca e filtros.
4. Os três entram no cabeçalho com ícones 15.01: ECONOMIA › Mercado, Leilão; um menu WIKI.

## Regras gerais para todas as etapas
- Backup do jogo antes de cada etapa: `cp tibia-idle-2d.html "$TEMP/tibia-idle-2d.antes_<etapa>.html"`.
- Validar a sintaxe com node (extrair o `<script>` inline e fazer `new Function`).
- Testar no navegador embutido (servidor local: `cd "/e/TIBIA SITE" && python -m http.server 5175 --bind 127.0.0.1` em segundo plano) sem erros no console.
- Não mexer em: `gestao-tibia.html`, pasta Downloads, arquivos do cliente em `%LOCALAPPDATA%\Temp`, conteúdo de `MAPAS/` (só ler). Não baixar nem executar programas (baixar .lua/.xml de dados do repositório do Canary é ok, com cache em `dados/`).
- Código no estilo do arquivo (compacto, comentários e textos em português).
