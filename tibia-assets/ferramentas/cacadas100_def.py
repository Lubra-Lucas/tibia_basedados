#!/usr/bin/env python3
"""Definição editorial das 100 caçadas: monstro principal, companheiros, nome (inglês), descrição (português) e biomas aceitos.

Cada linha: (principal, [companheiros], 'Nome da caçada', 'descrição curta', [biomas em ordem de preferência], opções)
 opções (dict, opcional): 'mapa' + 'z' (+ 'regiao' = índice em regioes_cacada.json) para forçar o recorte; 'sub' True/False para exigir subsolo/superfície.
O level recomendado sai da experiência do principal (curva logarítmica 1→1000) em gerar_cacadas100.py.
Biomas: grama, terra, areia, neve, pantano, lava, pedra, agua, construcao.
"""

CACADAS = [
    # ---- level 1 a ~15 (experiência até 100)
    ('Rat', ['Cave Rat'], 'Rat Cellars', 'Porões úmidos infestados de ratos: o primeiro passo de todo aventureiro.', ['construcao', 'terra'], {}),
    ('Snake', [], 'Snake Pit', 'Um fosso quente cheio de cobras pequenas e rápidas.', ['terra', 'areia'], {}),
    ('Spider', ['Poison Spider'], 'Spider Nest', 'Teias por toda parte. Cuidado com o veneno das aranhas.', ['terra', 'pantano'], {}),
    ('Wolf', ['Fox'], 'Wolf Den', 'Matilhas de lobos e raposas rondam esta floresta.', ['grama'], {}),
    ('Azure Frog', ['Orchid Frog', 'Coral Frog'], 'Frog Marsh', 'Pântano barulhento tomado por sapos coloridos.', ['pantano'], {}),
    ('Troll', ['Island Troll'], 'Troll Hills', 'Colinas rochosas onde trolls atacam quem passa.', ['grama', 'terra'], {}),
    ('Winter Wolf', [], 'Frost Wolf Trail', 'Lobos de pelo branco caçam em silêncio na neve.', ['neve'], {}),
    ('Bear', ['Panda'], 'Bear Woods', 'Ursos e pandas protegem uma floresta cheia de vida.', ['grama'], {}),
    ('Wasp', ['Bug'], 'Wasp Hive', 'Vespas furiosas guardam o ninho numa clareira.', ['grama'], {}),
    ('Goblin', ['Goblin Scavenger'], 'Goblin Burrows', 'Goblins vivem em túneis apertados cheios de tralha.', ['terra'], {}),
    ('Orc', ['Orc Spearman'], 'Orc Camp', 'Acampamento orc com lanceiros vigiando a entrada.', ['grama'], {}),
    ('Polar Bear', [], 'Polar Den', 'Ursos polares enormes patrulham a geleira.', ['neve'], {}),
    ('Crab', [], 'Crab Shore', 'Praia de areia fofa com caranguejos agressivos.', ['areia', 'agua'], {}),
    ('Lion', ['Hyaena'], 'Savanna Plains', 'Leões e hienas disputam a savana.', ['areia', 'grama'], {}),
    ('Cobra', [], 'Cobra Dunes', 'Dunas quentes escondem cobras venenosas.', ['areia'], {}),
    ('Centipede', ['Larva'], 'Centipede Tunnels', 'Túneis estreitos cheios de centopeias e larvas.', ['terra'], {}),
    ('Skeleton', ['Skeleton Warrior'], 'Skeleton Crypt', 'Cripta antiga com esqueletos que não descansam.', ['pedra'], {}),
    ('Rotworm', ['Carrion Worm'], 'Rotworm Tunnels', 'A clássica caverna de rotworms: ótimo treino de level.', ['terra'], {}),
    ('Tiger', [], 'Tiger Jungle', 'Selva densa onde tigres emboscam de dentro do mato.', ['grama'], {}),
    ('Crocodile', [], 'Crocodile Swamp', 'Pântano raso dominado por crocodilos famintos.', ['pantano'], {}),
    ('Elf', ['Elf Scout'], 'Elf Grove', 'Bosque élfico protegido por arqueiros certeiros.', ['grama'], {}),
    ('Dwarf', ['Dwarf Soldier', 'Dwarf Guard'], 'Dwarf Mines', 'Minas anãs cavadas fundo na pedra, com soldados e guardas.', ['terra', 'pedra'], {}),
    ('Minotaur', ['Minotaur Archer', 'Minotaur Mage'], 'Minotaur Maze', 'Labirinto de minotauros guerreiros, arqueiros e magos.', ['terra'], {}),
    ('Orc Warrior', ['Orc Shaman'], 'Orc Stronghold', 'Fortaleza orc com guerreiros e xamãs lançando magias.', ['terra', 'grama'], {}),
    ('Amazon', ['Valkyrie'], 'Amazon Fort', 'Amazonas e valquírias defendem o forte com lanças.', ['grama', 'construcao'], {}),
    ('Nomad', ['Nomad Female'], 'Nomad Oasis', 'Nômades do deserto protegem um oásis escondido.', ['areia'], {}),
    ('Bandit', ['Poacher'], 'Bandit Hideout', 'Esconderijo de bandidos e caçadores ilegais.', ['grama', 'construcao'], {}),
    ('Barbarian Skullhunter', ['Barbarian Headsplitter', 'Barbarian Brutetamer'], 'Barbarian Camp', 'Bárbaros com domadores de feras acampados na neve.', ['neve'], {}),
    ('Ghoul', ['Crypt Shambler'], 'Ghoul Graves', 'Cemitério antigo onde os mortos se arrastam.', ['pedra'], {}),
    ('Gazer', ['Bonelord'], 'Gazer Spires', 'Olhos flutuantes vigiam torres de pedra fria.', ['pedra'], {}),
    ('Gladiator', ['Stalker'], 'Gladiator Pit', 'Fosso de combate com gladiadores e emboscadores.', ['construcao', 'pedra'], {}),
    ('Tortoise', ['Thornback Tortoise'], 'Tortoise Coast', 'Tartarugas de casco duro passeiam pela costa.', ['areia'], {}),
    ('Quara Mantassin Scout', ['Quara Hydromancer Scout'], 'Quara Reef', 'Recife raso habitado por batedores quaras.', ['agua'], {}),
    ('Assassin', ['Dark Apprentice'], 'Assassin Den', 'Covil de assassinos e aprendizes das trevas.', ['construcao', 'pedra'], {}),
    # ---- level ~15 a ~60 (experiência 100 a 1.000)
    ('Kongra', ['Sibang', 'Merlkin'], 'Kongra Jungle', 'Selva barulhenta tomada por macacos fortes.', ['grama'], {}),
    ('Scarab', ['Sandcrawler'], 'Scarab Tombs', 'Escaravelhos gigantes devoram tudo nas tumbas do deserto.', ['areia'], {}),
    ('Ghost', ['Tarnished Spirit'], 'Haunted Manor', 'Mansão assombrada onde espíritos vagam sem rumo.', ['construcao', 'pedra'], {}),
    ('Deepling Worker', ['Deepling Scout'], 'Deepling Depths', 'Deeplings trabalhando nas profundezas do mar.', ['agua'], {}),
    ('Fire Devil', ['Gozzler'], 'Fire Devil Forge', 'Forja infernal com diabinhos de fogo e gozzlers.', ['lava'], {}),
    ('Cyclops', ['Cyclops Drone'], 'Cyclops Fort', 'Forte de ciclopes brutamontes e seus zangões.', ['terra', 'grama'], {}),
    ('Frost Giant', ['Frost Giantess'], 'Frost Giant Hall', 'Salão gelado de gigantes do gelo.', ['neve'], {}),
    ('Mummy', ['Tomb Servant'], 'Mummy Crypt', 'Tumba antiga cheia de múmias e servos embalsamados.', ['areia', 'pedra'], {}),
    ('Stone Golem', ['Iron Servant'], 'Golem Workshop', 'Oficina de golens de pedra e servos de ferro.', ['pedra', 'terra'], {}),
    ('Slime', ['Mercury Blob', 'Acid Blob'], 'Slime Pits', 'Poças gosmentas onde blobs ácidos se multiplicam.', ['pantano'], {}),
    ('Dragon Hatchling', [], 'Dragon Nursery', 'Berçário de dragões ainda pequenos, mas já cuspindo fogo.', ['terra', 'lava'], {}),
    ('Monk', ['Dark Monk'], 'Monastery Halls', 'Monges devotos e monges sombrios dividem o mosteiro.', ['construcao'], {}),
    ('Blue Djinn', ['Green Djinn'], 'Djinn Fortress', 'Fortaleza dos djinns do deserto, rivais há séculos.', ['areia', 'pedra'], {}),
    ('Fire Elemental', [], 'Fire Rift', 'Fenda ardente onde elementais de fogo nascem das chamas.', ['lava'], {}),
    ('Demon Skeleton', [], 'Demon Skeleton Pit', 'Fosso escuro com esqueletos de demônios.', ['pedra', 'terra'], {}),
    ('Zombie', ['Ghoul'], 'Zombie Graves', 'Sepulturas abertas e mortos-vivos podres.', ['pedra', 'pantano'], {}),
    ('Vampire', [], 'Vampire Crypt', 'Cripta elegante de vampiros sedentos.', ['pedra', 'construcao'], {}),
    ('Efreet', [], 'Efreet Palace', 'Palácio flamejante dos efreets, aliados do fogo.', ['areia', 'lava'], {}),
    ('Yeti', ['Ice Witch'], 'Yeti Peak', 'Pico congelado onde yetis e bruxas do gelo rondam.', ['neve'], {}),
    ('Wyvern', ['Dragon Hatchling'], 'Wyvern Cliffs', 'Penhascos varridos pelo vento e dominados por wyverns.', ['terra', 'grama'], {}),
    ('Earth Elemental', ['Massive Earth Elemental'], 'Earth Rift', 'Fenda de pedra viva com elementais da terra.', ['terra'], {}),
    ('Necromancer', ['Bonebeast'], 'Necromancer Lair', 'Covil de necromantes e suas bestas de ossos.', ['pedra'], {}),
    ('Quara Mantassin', ['Quara Mantassin Scout'], 'Quara Deep', 'Mantassins quaras guardam o fundo do mar.', ['agua'], {}),
    ('Dragon', ['Dragon Hatchling', 'Dragon Lord Hatchling'], 'Dragon Lair', 'O covil dos dragões: fogo, ouro e muito perigo.', ['terra', 'lava'], {}),
    ('Insectoid Worker', ['Insectoid Scout'], 'Insectoid Hive', 'Colmeia insectoide cheia de operários e batedores.', ['terra'], {}),
    ('Pixie', ['Swan Maiden'], 'Pixie Glade', 'Clareira encantada onde as fadas atacam com magia.', ['grama'], {}),
    ('Bog Raider', [], 'Bog Raider Marsh', 'Pântano lodoso de onde saem os bog raiders.', ['pantano'], {}),
    ('Ogre Brute', ['Ogre Shaman', 'Ogre Savage'], 'Ogre Camp', 'Acampamento ogro com brutamontes e xamãs.', ['grama', 'terra'], {}),
    ('Giant Spider', ['Tarantula'], 'Giant Spider Lair', 'Ninho de aranhas gigantes de veneno mortal.', ['terra'], {}),
    ('Lich', ['Putrid Mummy'], 'Lich Crypt', 'Cripta de liches e múmias putrefatas.', ['pedra'], {}),
    # ---- level ~65 a 1000 (experiência 1.000 a 22.000)
    ('Gryphon', [], 'Gryphon Peaks', 'Picos rochosos onde grifos defendem seus ninhos.', ['terra', 'grama'], {}),
    ('Young Sea Serpent', [], 'Serpent Coast', 'Costa traiçoeira nadando em jovens serpentes marinhas.', ['agua', 'areia'], {}),
    ('Yielothax', ['Instable Breach Brood'], 'Yielothax Nest', 'Ninho dimensional de yielothax e crias instáveis.', ['lava', 'pedra'], {}),
    ('Minotaur Cult Zealot', ['Minotaur Cult Follower', 'Minotaur Cult Prophet'], 'Cult Sanctum', 'Santuário de minotauros fanáticos e profetas.', ['terra', 'pedra'], {}),
    ('Werebadger', ['Werefox'], 'Werebeast Hollow', 'Vale sombrio de criaturas que se transformam sob a lua.', ['grama', 'terra'], {}),
    ('Stone Rhino', [], 'Rhino Plains', 'Planície árida pisoteada por rinocerontes de pedra.', ['areia', 'terra'], {}),
    ('Hydra', [], 'Hydra Lair', 'Pântano profundo onde hidras de várias cabeças espreitam.', ['pantano', 'terra'], {}),
    ('Dragon Lord', ['Dragon'], 'Dragon Lord Citadel', 'Cidadela dos poderosos Dragon Lords.', ['lava', 'terra'], {}),
    ('Behemoth', [], 'Behemoth Caves', 'Cavernas imensas onde gigantes behemoths esmagam rochas.', ['terra'], {}),
    ('Spidris', ['Spidris Elite'], 'Spidris Nest', 'Ninho de spidris, aranhas colossais e venenosas.', ['terra', 'pantano'], {}),
    ('Stone Devourer', [], 'Devourer Quarry', 'Pedreira devorada por golens vivos de rocha.', ['pedra', 'terra'], {}),
    ('Fury', [], 'Fury Inferno', 'Inferno de fúrias, demônios de fogo e raiva.', ['lava'], {}),
    ('Magma Crawler', [], 'Magma Tunnels', 'Túneis de lava rastejante com crawlers incandescentes.', ['lava'], {}),
    ('Lost Soul', ['Flimsy Lost Soul'], 'Lost Souls Grave', 'Almas perdidas vagam sem descanso por este cemitério.', ['pedra'], {}),
    ('Dawnfire Asura', ['Midnight Asura', 'Frost Flower Asura'], 'Asura Palace', 'Palácio das asuras, belas e mortais.', ['lava', 'pedra'], {}),
    ('Phantasm', [], 'Phantasm Void', 'Vazio sombrio onde pesadelos ganham forma.', ['pedra', 'lava'], {}),
    ('Bulltaur Alchemist', ['Bulltaur Brute'], 'Bulltaur Forge', 'Forja de bulltaurs alquimistas e brutamontes.', ['pedra', 'terra'], {}),
    ('Skeleton Elite Warrior', [], 'Elite Skeleton Barracks', 'Quartel de esqueletos guerreiros de elite.', ['pedra'], {}),
    ('Dragolisk', [], 'Dragolisk Lair', 'Covil de dragolisks, mistura de dragão e basilisco.', ['terra', 'lava'], {}),
    ('Manticore', [], 'Manticore Ruins', 'Ruínas do deserto com manticoras de cauda venenosa.', ['areia'], {}),
    ('Venerable Girtablilu', ['Girtablilu Warrior'], 'Girtablilu Sanctuary', 'Santuário escondido dos escorpiões humanoides.', ['areia', 'pedra'], {}),
    ('Naga Warrior', ['Naga Archer'], 'Naga Temple', 'Templo submerso de nagas guerreiras e arqueiras.', ['pantano', 'agua', 'pedra'], {}),
    ('Demon', [], 'Hellgore', 'O famoso covil de demônios, quente como o inferno.', ['lava'], {'mapa': 'hellgore.otbm'}),
    ('Deathling Scout', ['Deathling Spellsinger'], 'Deathling Reef', 'Recife maldito de deathlings afogados.', ['agua'], {}),
    ('Undead Dragon', [], 'Undead Dragon Tomb', 'Tumba onde dragões mortos-vivos despertam.', ['pedra'], {}),
    ('Lava Golem', [], 'Lava Golem Forge', 'Forja de golens de lava derretida.', ['lava'], {}),
    ('Feral Sphinx', ['Black Sphinx Acolyte'], 'Sphinx Sanctum', 'Esfinges selvagens guardam os segredos do deserto.', ['areia', 'pedra'], {}),
    ('Guardian of Tales', ['Energuardian of Tales'], 'Library of Tales', 'Biblioteca arcana protegida por guardiões vivos.', ['pedra', 'construcao'], {}),
    ('Hellflayer', [], 'Hellflayer Pit', 'Fosso dos hellflayers, demônios que arrancam almas.', ['lava'], {}),
    ('Sabretooth', [], 'Sabretooth Cliffs', 'Penhascos gelados rondados por tigres de dentes de sabre.', ['neve', 'terra'], {}),
    ('Gorerilla', [], 'Gorerilla Jungle', 'Selva sangrenta dominada por gorilas colossais.', ['grama'], {}),
    ('Brachiodemon', ['Infernal Phantom'], 'Brachiodemon Hall', 'Salão infernal de braquiodemônios e fantasmas.', ['lava', 'pedra'], {}),
    ('Infernal Demon', [], 'Infernal Throne', 'Trono do inferno, onde demônios supremos governam.', ['lava'], {}),
    ('Rotten Golem', ['Branchy Crawler'], 'Rotten Grove', 'Bosque apodrecido de golens e rastejadores de galhos.', ['pantano', 'terra'], {}),
    ('Bony Sea Devil', [], 'Sea Devil Abyss', 'Abismo submarino de diabos marinhos ossudos.', ['agua', 'pedra'], {}),
    ('Darklight Construct', ['Darklight Striker'], 'Darklight Core', 'O coração da luz sombria, a caçada definitiva.', ['lava', 'pedra'], {}),
]

if __name__ == '__main__':
    import json, os, collections
    D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dados')
    cat = {x['nome']: x for x in json.load(open(os.path.join(D, 'catalogo_monstros.json'), encoding='utf-8'))}
    print(len(CACADAS), 'caçadas')
    nomes = [c[0] for c in CACADAS]
    print('principais repetidos:', [n for n, k in collections.Counter(nomes).items() if k > 1])
    print('nomes de caçada repetidos:', [n for n, k in collections.Counter(c[2] for c in CACADAS).items() if k > 1])
    for c in CACADAS:
        for n in [c[0]] + c[1]:
            if n not in cat: print('NÃO ACHADO:', n, 'em', c[2])
        if cat.get(c[0]) and cat[c[0]]['exp'] <= 0: print('sem exp', c[0])
    exps = [cat[c[0]]['exp'] for c in CACADAS if c[0] in cat]
    print('exp ordenada?', exps == sorted(exps))
    print([(c[0], cat[c[0]]['exp']) for i, c in enumerate(CACADAS) if i and cat[CACADAS[i - 1][0]]['exp'] > cat[c[0]]['exp']])
