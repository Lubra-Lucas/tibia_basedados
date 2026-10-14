#!/usr/bin/env python3
"""Gera as 100 caçadas do jogo: escolhe o recorte de mapa de cada uma, exporta os mapas, lê os monstros do Canary
(vida, exp, ataques, loot), monta os itens (peso, preço de NPC, ícone do cliente 15.01) e escreve cacadas100.js.

Etapas (python gerar_cacadas100.py ETAPA ...; sem argumento roda todas na ordem):
  plano      escolhe uma região de regioes_cacada.json para cada caçada e calcula o level      → dados/cacadas100_plano.json
  mapas      exporta os 100 recortes (atlas PNG + .js)                                          → mapas15/cacadas/hNNN.js
  dados      baixa os .lua (cache em dados/canary_magias/monstros/), monta monstros e itens     → cacadas100.js, dados/cacadas100_mobs.json
  icones     ícones 15.01 dos itens do loot e dos itens do jogo                                  → sprites15/itens/<id>.png
  relatorio  dados/cacadas100_relatorio.txt
Depois rodar gerar_sprites15.py (lê dados/cacadas100_mobs.json) para as folhas de sprite e cadáveres dos monstros novos.
"""
import collections, glob, json, math, os, random, re, sys, urllib.parse, urllib.request
import concurrent.futures as cf
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
DADOS = os.path.join(RAIZ, 'dados')
MAPAS = os.path.normpath(os.path.join(RAIZ, '..', 'MAPAS'))
PLANO = os.path.join(DADOS, 'cacadas100_plano.json')
RAW = 'https://raw.githubusercontent.com/opentibiabr/canary/main/data-otservbr-global/monster/'
sys.path.insert(0, AQUI)
from cacadas100_def import CACADAS

# mapas que não servem para caçar (salas de treino, lojas, teleportes, arenas de evento, cidades)
EXCLUIR = {'Stone_Trainers.otbm', 'shop.otbm', 'wzshop.otbm', 'training_.otbm', 'TeleportsRoom_V12.otbm', 'moba.otbm', 'battlefield.otbm',
           'Houses.otbm', 'SmallCity.otbm', 'city_proj.otbm', 'castle24h.otbm', 'Castles.otbm', 'castle.otbm'}
# palavras do nome que pedem subsolo ou superfície
SUBSOLO = ('cellars', 'nest', 'burrows', 'tunnels', 'crypt', 'mines', 'maze', 'tombs', 'tomb', 'pit', 'lair', 'caves', 'hive', 'abyss', 'core', 'inferno',
           'rift', 'forge', 'depths', 'sanctum', 'barracks', 'void', 'workshop', 'quarry', 'graves', 'throne', 'hall', 'library', 'palace', 'den', 'temple')
SUPERFICIE = ('woods', 'hills', 'plains', 'jungle', 'camp', 'coast', 'shore', 'dunes', 'trail', 'peak', 'cliffs', 'grove', 'marsh', 'oasis', 'glade',
              'reef', 'fort', 'fortress', 'ruins', 'pixie', 'savanna', 'swamp', 'isles', 'garden')
PULL = {'cauteloso': {'n': 6, 'k': 1}, 'ousado': {'n': 10, 'k': 2}, 'agressivo': {'n': 16, 'k': 3}}
# anchors (exp do monstro principal, level recomendado): interpolação logarítmica por partes
ANCORAS = [(5, 1), (10, 3), (20, 6), (30, 10), (50, 18), (100, 32), (150, 45), (300, 75), (500, 100), (700, 125), (1000, 160), (2000, 250),
           (4000, 380), (6000, 500), (10000, 700), (22050, 1000)]


def slug(n):
    return re.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')


def titulo(n):
    pequenas = {'of', 'the', 'a', 'an', 'and', 'in', 'on', 'with', 'for', 'to', 'from'}
    return ' '.join(w if (i and w.lower() in pequenas) else (w[:1].upper() + w[1:]) for i, w in enumerate(n.split(' ')))


def carregar_catalogo():
    cat = {x['nome']: x for x in json.load(open(os.path.join(DADOS, 'catalogo_monstros.json'), encoding='utf-8'))}
    can = {x['nome']: x for x in json.load(open(os.path.join(DADOS, 'monstros_canary.json'), encoding='utf-8'))}
    return cat, can


def level_de(exp):
    if exp <= ANCORAS[0][0]: return ANCORAS[0][1]
    for (e0, l0), (e1, l1) in zip(ANCORAS, ANCORAS[1:]):
        if exp <= e1: return l0 + (l1 - l0) * math.log(exp / e0) / math.log(e1 / e0)
    return ANCORAS[-1][1]


# ---------------------------------------------------------------- etapa 1: plano (região + level)
def etapa_plano():
    cat, _ = carregar_catalogo()
    regs = json.load(open(os.path.join(DADOS, 'regioes_cacada.json'), encoding='utf-8'))
    rng = random.Random(1501)
    uso_mapa = collections.Counter(); escolhidas = []; plano = []
    # level: curva pela exp do principal, sempre crescente
    levels = []
    for c in CACADAS:
        lv = round(level_de(cat[c[0]]['exp']))
        levels.append(max(lv, levels[-1] + 1 if levels else 1))
    levels[-1] = 1000
    for i in range(len(levels) - 2, -1, -1): levels[i] = min(levels[i], levels[i + 1] - 1)   # garante crescente também no fim
    ordem = sorted(range(len(CACADAS)), key=lambda i: 0 if CACADAS[i][5].get('mapa') else 1)   # recortes forçados primeiro
    plano_por = {}
    for i in ordem:
        prin, comp, nome, desc, biomas, op = CACADAS[i]
        pal = nome.lower()
        quer_sub = any(p in pal for p in SUBSOLO) and not any(p in pal for p in SUPERFICIE)
        quer_sup = any(p in pal for p in SUPERFICIE) and not quer_sub
        melhor, ms = None, 1e9
        for r in regs:
            if r['mapa'] in EXCLUIR: continue
            if op.get('mapa') and r['mapa'] != op['mapa']: continue
            if op.get('regiao') is not None and r['id'] != op['regiao']: continue
            if not op.get('mapa') and (r['tiles'] < 300 or r['tiles'] > 1500 or r['dens'] < .28): continue
            w, h = r['x1'] - r['x0'], r['y1'] - r['y0']
            if not op.get('mapa') and (min(w, h) < 16 or max(w, h) / min(w, h) > 3.2): continue
            if any(e['mapa'] == r['mapa'] and e['z'] == r['z'] and not (r['x1'] <= e['x0'] or r['x0'] >= e['x1'] or r['y1'] <= e['y0'] or r['y0'] >= e['y1']) for e in escolhidas): continue
            if r['bioma'] in biomas: s = 1.6 * biomas.index(r['bioma'])
            elif op.get('mapa'): s = 0
            else:
                # bioma secundário (2º mais comum) conta como meia concordância
                sec = [b for b in r['cats'] if b in biomas]
                if not sec or r['cats'][sec[0]] < r['tiles'] * .25: continue
                s = 4 + 1.6 * biomas.index(sec[0])
            if quer_sub and not r['sub']: s += 1.4
            if quer_sup and r['sub']: s += 1.4
            s += abs(math.log(r['tiles'] / 700)) * 1.1 + (0.7 if r.get('janela') else 0) + 0.9 * uso_mapa[r['mapa']] + rng.random() * 0.8
            if s < ms: melhor, ms = r, s
        if not melhor: raise SystemExit(f'sem região para {nome} ({biomas})')
        escolhidas.append(melhor); uso_mapa[melhor['mapa']] += 1
        plano_por[i] = ({'num': i + 1, 'id': slug(nome), 'chave': f'h{i + 1:03d}', 'nome': nome, 'desc': desc, 'principal': prin, 'comp': comp, 'lv': levels[i],
                      'regiao': melhor['id'], 'mapa': melhor['mapa'], 'z': melhor['z'], 'caixa': [melhor['x0'], melhor['y0'], melhor['x1'], melhor['y1']],
                      'bioma': 'lava' if prin == 'Demon' else melhor['bioma'], 'sub': melhor['sub'], 'tiles_regiao': melhor['tiles'], 'chao': melhor['chao']})
    plano = [plano_por[i] for i in range(len(CACADAS))]
    json.dump(plano, open(PLANO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('plano salvo:', len(plano), 'caçadas;', len(uso_mapa), 'mapas;', uso_mapa.most_common(8))
    print('biomas:', collections.Counter(p['bioma'] for p in plano), 'subsolo:', sum(p['sub'] for p in plano))
    for p in plano: print(f"{p['num']:3d} {p['nome']:26s} lv{p['lv']:4d} {p['mapa']:26s} z{p['z']:2d} {p['bioma']:10s} {p['tiles_regiao']}")


# ---------------------------------------------------------------- etapa 2: mapas
def etapa_mapas(somente=None):
    from exportar_mapa15 import Exportador
    from ler_otbm import ler
    plano = json.load(open(PLANO, encoding='utf-8'))
    por_mapa = collections.defaultdict(list)
    for p in plano:
        if somente and p['num'] not in somente: continue
        por_mapa[p['mapa']].append(p)
    E = Exportador()
    pasta_mapas = [os.path.join(MAPAS, 'mapas1'), os.path.join(MAPAS, 'Classicos')]
    for mapa, ps in sorted(por_mapa.items()):
        arq = next(os.path.join(d, mapa) for d in pasta_mapas if os.path.exists(os.path.join(d, mapa)))
        tiles = ler(arq)['tiles']
        for p in ps:
            x0, y0, x1, y1 = p['caixa']; m = 3
            lid = [slug(p['principal'])] * 2 + [slug(c) for c in p['comp']]
            st = E.exportar(arq, p['chave'], p['nome'], p['z'], (x0 - m, y0 - m, x1 + m, y1 + m), tiles=tiles,
                            plano={'lideres': lid, 'pts': 16, 'tempo': 40}, pasta='cacadas', prefixo=p['chave'])
            p['export'] = st
        del tiles
        json.dump(plano, open(PLANO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)   # salva a cada mapa (retomável)


CABECALHO = """/* gerado por ferramentas/gerar_cacadas100.py: as 100 caçadas do jogo (monstros e loot do Canary, mapas reais recortados).
 *
 * window.CACADAS100 = { hunts, mobs, itens, icones }
 *  hunts[id]  = { num (1-100), n (nome em inglês), desc, lv (level recomendado), mobs {monstro: peso}, principal, bioma, sub (subsolo),
 *                 mapa (caminho do .js do mapa, carregado sob demanda ao entrar), chave (hNNN), origem (mapa/andar/recorte),
 *                 pull { cauteloso|ousado|agressivo: { n: pontos de spawn usados, k: monstros por ponto, nome } } }
 *  mobs[id]   = { n, hp, exp, vel, arm, def, el {elemento: % de resistência}, hit, loot [[itemId, chance 0-1, maxCount]],
 *                 atq15/def15 (ataques e defesas do Canary, usados por ataque15), invoca [{id, chance}], maxInv, best [3 marcos do bestiário],
 *                 charm, est (estrelas), classe, invocado (só aparece como invocação de outro monstro) }   sprite em SPR15.criaturas[id]
 *  itens[id]  = { n, w (peso em oz), v (preço de NPC), type ('loot' | 'coin'), cid (id no cliente 15.01), icone, estimado (preço estimado) }
 *  icones     = { idDoItemDoJogo: caminho do ícone 15.01 }  (equipamentos e poções definidos no HTML)
 * No jogo (tibia-idle-2d.html): HUNTS[id], MOBS[id] e ITEMS[id] são montados a partir daqui (sprites em SPR15.criaturas[id], ícones em ITEMS[id].icone).
 *  S.pull[idCaçada]       = 'cauteloso' | 'ousado' | 'agressivo' (padrão cauteloso); pullDe(idCaçada) devolve { n, k, nome }
 *  S.lootCfg[idItemDoJogo] = { pegar, vender }; lootCfgDe(id) devolve o efetivo (padrão em lootPadrao), setLootCfg(id, 'pegar'|'vender', bool) grava.
 *      O id é o do ITEMS do jogo: LOOT_ID[idDoLoot] traduz (equipamentos e poções do jogo são reaproveitados pelo nome); moedas viram gold direto.
 *  S.recordes[idCaçada]   = { exp (exp/h), lucro (gp/h), pull, lv, t }: melhor medida nos primeiros 5 min de uma entrada na caçada (medirRecorde).
 *  MOB_CACADA = conjunto dos monstros que aparecem em alguma caçada (bestiário, prey). travel(id) espera ensureRegion(id), que injeta o <script> do mapa.
 * O mapa de cada caçada (window.MAPAS.hNNN + MAPAS_SPRITES) é injetado por <script> dinâmico em ensureRegion; MAPAS[chave].spawns[] = [x, y, monstro, tempo(s)] já
 * ordenados do "mais afastado": Cauteloso usa os 6 primeiros, Ousado 10, Agressivo 16 (k monstros por ponto: 1/2/3). */
"""


def escrever_js(out):
    with open(os.path.join(RAIZ, 'cacadas100.js'), 'w', encoding='utf-8') as fp:
        fp.write(CABECALHO + 'window.CACADAS100=' + json.dumps(out, separators=(',', ':'), ensure_ascii=False) + ';\n')


def ler_js():
    t = open(os.path.join(RAIZ, 'cacadas100.js'), encoding='utf-8').read()
    return json.loads(t[t.index('window.CACADAS100=') + 18:t.rindex(';')])


# ---------------------------------------------------------------- etapa 3: monstros e itens
def bloco(s, nome):
    i = s.find(f'monster.{nome} = {{')
    if i < 0: return ''
    j, prof = s.index('{', i), 0
    for k in range(j, len(s)):
        prof += {'{': 1, '}': -1}.get(s[k], 0)
        if prof == 0: return s[j:k + 1]
    return ''


def nomes_itens():
    """nome (minúsculo) → id do cliente, id → nome e peso em oz, a partir do items.xml do Canary."""
    por_nome, por_id, peso = {}, {}, {}
    for it in ET.parse(os.path.join(DADOS, '_items.xml')).getroot().iter('item'):
        nm = (it.get('name') or '').lower()
        ids = [int(it.get('id'))] if it.get('id') else list(range(int(it.get('fromid')), int(it.get('toid')) + 1))
        w = 0
        for a in it.iter('attribute'):
            if a.get('key') == 'weight': w = int(a.get('value')) / 100
        for i in ids:
            por_id[i] = nm; peso[i] = w
            if nm and (nm not in por_nome or (w and not peso.get(por_nome[nm]))): por_nome[nm] = i
    return por_nome, por_id, peso


def ler_loot(s):
    b = bloco(s, 'loot'); out = []
    for e in re.findall(r'\{[^{}]*\}', b[1:-1] if b else ''):
        nm = re.search(r'name\s*=\s*"([^"]+)"', e); idd = re.search(r'\bid\s*=\s*(\d+)', e)
        ch = re.search(r'chance\s*=\s*(\d+)', e); mx = re.search(r'maxCount\s*=\s*(\d+)', e)
        if not ch or not (nm or idd): continue
        out.append({'nome': nm.group(1).lower() if nm else None, 'id': int(idd.group(1)) if idd else None, 'chance': int(ch.group(1)) / 100000, 'max': int(mx.group(1)) if mx else 1})
    return out


def baixar_lua(chave, arquivo):
    d = os.path.join(DADOS, 'canary_magias', 'monstros', chave + '.lua')
    if not os.path.exists(d):
        for t in range(3):
            try:
                open(d, 'wb').write(urllib.request.urlopen(RAW + urllib.parse.quote(arquivo), timeout=60).read()); break
            except Exception as e:
                if t == 2: raise
    return d



# ---- ataques e defesas: leitor próprio (aceita blocos aninhados, como "condition = { ... }") ----
KW_EL = [('soulfire', 'fire'), ('fire', 'fire'), ('lava', 'fire'), ('ice', 'ice'), ('frost', 'ice'), ('poison', 'earth'), ('death', 'death'), ('curse', 'death'),
         ('holy', 'holy'), ('energy', 'energy'), ('electr', 'energy'), ('earth', 'earth')]


def entradas_lua(b, me, ani):
    """Entradas de primeiro nível de um bloco `{ {...}, {...} }` do Canary como dicts (blocos internos são descartados)."""
    out, prof, ini = [], 0, None
    for k, ch in enumerate(b):
        if ch == '{':
            prof += 1
            if prof == 2: ini = k
        elif ch == '}':
            if prof == 2 and ini is not None: out.append(b[ini + 1:k]); ini = None
            prof -= 1
    res = []
    for e in out:
        while True:
            e2 = re.sub(r'\{[^{}]*\}', '', e)
            if e2 == e: break
            e = e2
        d = {}
        for k, v in re.findall(r'(\w+)\s*=\s*("[^"]*"|[-\w.]+)', e):
            v = v.strip('"')
            if v.startswith('CONST_ME_'): v = me.get(v)
            elif v.startswith('CONST_ANI_'): v = ani.get(v)
            elif v.startswith('COMBAT_'): v = v[7:].replace('DAMAGE', '').lower(); v = {'physical': 'phys'}.get(v, v)
            elif v in ('true', 'false'): v = v == 'true'
            else:
                try: v = float(v) if '.' in v else int(v)
                except ValueError: pass
            d[k] = v
        if 'name' in d: res.append(d)
    return res


def ataque_jogo(a):
    """Converte um ataque do Canary para o que o ataque15 do jogo entende (melee, combat, firefield, speed); magias nomeadas com dano viram combat."""
    n = a['name']
    if n == 'melee' or n == 'speed': return a
    if n in ('firefield', 'poisonfield', 'energyfield'): return a
    if n == 'combat':
        if a.get('type') in ('healing', None): return None
        if not a.get('length') and not a.get('range'):
            a['range'] = a.get('radius') or 1              # área em volta do monstro / ataque de contato
        return a
    if 'minDamage' in a and 'maxDamage' in a:               # magia nomeada ("fire wave", "death chain", "largefirering"...)
        tipo = next((e for k, e in KW_EL if k in n), 'phys')
        b = {'name': 'combat', 'chance': a.get('chance', 10), 'interval': a.get('interval', 2000), 'type': tipo, 'minDamage': a['minDamage'], 'maxDamage': a['maxDamage']}
        if 'ring' in n: b['radius'] = 6 if 'large' in n else 4; b['range'] = b['radius']; b['target'] = False
        elif 'wave' in n or 'avalanche' in n: b['length'] = 6; b['target'] = False
        else: b['range'] = a.get('range') or 7; b['target'] = True
        return b
    return None                                             # redutores de skill, drunk, root, invisibilidade...


def defesa_jogo(a):
    if a['name'] == 'speed' and a.get('speed', 0) > 0: return a
    if a['name'] == 'combat' and a.get('type') == 'healing': return a
    return None


COINS = {'gold coin': ('gold_coin', 1), 'platinum coin': ('platinum_coin', 100), 'crystal coin': ('crystal_coin', 10000)}


def etapa_dados():
    from gerar_combate15 import ler_monstro, constantes
    cat, can = carregar_catalogo()
    plano = json.load(open(PLANO, encoding='utf-8'))
    me, ani = constantes()
    precos = {k.lower(): v for k, v in json.load(open(os.path.join(DADOS, '_precos_npc.json'), encoding='utf-8')).items()}
    por_nome, por_id, peso = nomes_itens()
    os.makedirs(os.path.join(DADOS, 'canary_magias', 'monstros'), exist_ok=True)
    # monstros: principais, companheiros e (até 2 níveis) o que eles invocam
    fila = []; vistos = {}
    for p in plano:
        for n in [p['principal']] + p['comp']: fila.append((n, False))
    todos = {}; canon = {k.lower(): k for k in can}
    prof = 0
    while fila and prof < 3:
        prox = []
        for n, inv in fila:
            n = canon.get(n.lower())
            if not n: print('sem dado no Canary:', n); continue
            if n in todos: continue
            todos[n] = {'inv': inv}
        # baixa e lê
        with cf.ThreadPoolExecutor(12) as ex: list(ex.map(lambda n: baixar_lua(slug(n), can[n]['arquivo']), [n for n in todos if 'lua' not in todos[n]]))
        for n in list(todos):
            if 'lua' in todos[n]: continue
            todos[n]['lua'] = ler_monstro(os.path.join('monstros', slug(n) + '.lua'), me, ani)
            for s in todos[n]['lua']['invoca']:
                prox.append((s['nome'], True))
        fila = prox; prof += 1
    # lê o texto de cada lua para loot e bestiário
    mobs, itens_usados = {}, {}
    comuns = {}
    for n, d in todos.items():
        txt = open(os.path.join(DADOS, 'canary_magias', 'monstros', slug(n) + '.lua'), encoding='utf-8').read()
        L = d['lua']; c = can[n]; k = slug(n)
        num = lambda rx, d: int((re.search(rx, txt) or [0, d])[1])
        best = [num(r'FirstUnlock = (\d+)', 25), num(r'SecondUnlock = (\d+)', 250), num(r'toKill = (\d+)', 500)]
        loot = []
        for e in ler_loot(txt):
            nm = e['nome'] or por_id.get(e['id'], '')
            if not nm: continue
            iid = por_nome.get(nm, e['id'])
            loot.append({'nome': nm, 'cid': iid, 'chance': e['chance'], 'max': e['max']})
        ataques = [x for x in (ataque_jogo(a) for a in entradas_lua(bloco(txt, 'attacks'), me, ani)) if x]
        defesas = [x for x in (defesa_jogo(a) for a in entradas_lua(bloco(txt, 'defenses'), me, ani)) if x]
        melee = next((a for a in ataques if a.get('name') == 'melee'), None)
        mobs[k] = {'n': c['nome'], 'hp': L['hp'], 'exp': L['exp'], 'vel': L['vel'], 'arm': L['arm'], 'def': L['def'], 'el': L['elementos'],
                   'hit': abs(melee.get('maxDamage', 0)) if melee else 0, 'atq15': ataques, 'def15': defesas,
                   'invoca': [{'id': slug(canon[s['nome'].lower()]), 'chance': s['chance']} for s in L['invoca'] if s['nome'].lower() in canon], 'maxInv': L['max_invoca'],
                   'best': best, 'charm': num(r'CharmsPoints = (\d+)', 5), 'est': c['estrelas'], 'classe': c['classe'],
                   'invocado': d['inv'], '_loot': loot, '_look': c}
    # itens: tudo que aparece nos loots
    itens = {}
    for k, m in mobs.items():
        for e in m['_loot']:
            nm = e['nome']
            if nm in COINS:
                iid, v = COINS[nm]; itens.setdefault(iid, {'n': titulo(nm), 'w': 0, 'v': v, 'type': 'coin', 'cid': e['cid']}); e['item'] = iid; continue
            iid = slug(nm); e['item'] = iid
            it = itens.setdefault(iid, {'n': titulo(nm), 'w': peso.get(e['cid'], 0) or 0.5, 'v': precos.get(nm), 'type': 'loot', 'cid': e['cid'], 'comum': 0, 'exp': 0})
            it['comum'] = max(it['comum'], e['chance']); it['exp'] = m['exp'] if not it['exp'] else min(it['exp'], m['exp'])
    for iid, it in itens.items():
        if it['type'] == 'coin': continue
        if it['v'] is None:    # preço estimado por raridade e experiência do monstro que dropa
            base = max(2, .35 * it.pop('exp', 0)); fator = min(30, max(.25, (0.05 / max(it.pop('comum', 1), 1e-4)) ** .55))
            v = base * fator; dig = 10 ** max(0, int(math.log10(v)) - 1); it['v'] = max(1, int(round(v / dig) * dig)); it['estimado'] = True
        it.pop('exp', None); it.pop('comum', None)
    # monta mobs finais
    for k, m in mobs.items():
        m['loot'] = [[e['item'], round(e['chance'], 5), e['max']] for e in m.pop('_loot')]
        m.pop('_look')
    # caçadas
    hunts = {}
    for p in plano:
        prin = slug(p['principal']); comp = [slug(c) for c in p['comp']]
        pesos = {prin: 10}
        for c in comp: pesos[c] = max(2, round(10 / (len(comp) + 1)))
        ex = p.get('export') or {}
        hunts[p['id']] = {'num': p['num'], 'n': p['nome'], 'desc': p['desc'], 'lv': p['lv'], 'mobs': pesos, 'principal': prin, 'bioma': p['bioma'],
                          'mapa': f"tibia-assets/mapas15/cacadas/{p['chave']}.js", 'chave': p['chave'], 'pull': {k: dict(v, nome=k.capitalize()) for k, v in PULL.items()},
                          'sub': p['sub'], 'origem': f"{p['mapa']} z{p['z']} [{p['caixa'][0]},{p['caixa'][1]}-{p['caixa'][2]},{p['caixa'][3]}]"}
    # itens que o jogo precisa mesmo sem cair de nenhum monstro: materiais de imbuement
    html = open(os.path.join(RAIZ, '..', 'tibia-idle-2d.html'), encoding='utf-8').read()
    por_slug = {slug(n): i for n, i in por_nome.items()}
    for blk in re.findall(r'mats:\{([^}]*)\}', html):
        for k in re.findall(r'(\w+):', blk):
            if k in itens: continue
            cid = por_slug.get(k)
            if cid: itens[k] = {'n': titulo(por_id[cid]), 'w': peso.get(cid, .5) or .5, 'v': precos.get(por_id[cid], 0), 'type': 'loot', 'cid': cid, 'naoDropa': True}
    escrever_js({'hunts': hunts, 'mobs': mobs, 'itens': itens})
    json.dump({k: {'nome': m['n']} for k, m in mobs.items()}, open(os.path.join(DADOS, 'cacadas100_mobs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    est = sum(1 for i in itens.values() if i.get('estimado'))
    print(f'{len(hunts)} caçadas, {len(mobs)} monstros ({sum(1 for m in mobs.values() if m["invocado"])} só invocados), {len(itens)} itens ({est} com preço estimado)')


# ---------------------------------------------------------------- etapa 4: ícones
def etapa_icones():
    from gerar_sprites15 import Gerador
    G = Gerador(); pasta = os.path.join(RAIZ, 'sprites15', 'itens'); os.makedirs(pasta, exist_ok=True)
    out = ler_js(); por_nome, por_id, _ = nomes_itens(); feitos = {}

    def icone(cid):
        if cid is None: return None
        if cid not in feitos:
            arq = os.path.join(pasta, f'{cid}.png')
            feitos[cid] = f'tibia-assets/sprites15/itens/{cid}.png' if (os.path.exists(arq) or G.folha_item(cid, arq)) else None
        return feitos[cid]
    sem = []
    for k, it in out['itens'].items():
        ic = icone(it.get('cid'))
        if ic: it['icone'] = ic
        else: it.pop('icone', None); sem.append(it['n'])
    # equipamentos e poções definidos no HTML do jogo: nome → id do cliente
    html = open(os.path.join(RAIZ, '..', 'tibia-idle-2d.html'), encoding='utf-8').read()
    ini, fim = html.index('const ITEMS={}'), html.index('const POTS=')
    icones, semj = {}, []
    for iid, nome in re.findall(r"\['(\w+)','([^']+)'", html[ini:fim]):
        cid = por_nome.get(nome.lower())
        ic = icone(cid) if cid else None
        if ic: icones[iid] = ic
        else: semj.append(nome)
    for iid, nome in {'stamina_pot': 'stamina extension'}.items():     # itens do jogo que não estão nas listas do HTML ou têm nome diferente
        ic = icone(por_nome.get(nome))
        if ic: icones[iid] = ic
    out['icones'] = icones
    escrever_js(out)
    print(f'ícones: {len(feitos)} arquivos; itens do loot sem ícone {len(sem)} {sem[:12]}; itens do jogo com ícone {len(icones)}, sem {semj}')


# ---------------------------------------------------------------- etapa 5: relatório
def etapa_relatorio():
    plano = json.load(open(PLANO, encoding='utf-8')); out = ler_js()
    L = ['RELATÓRIO DAS 100 CAÇADAS (gerado por gerar_cacadas100.py)', '',
         'nº | nome | monstros | level | mapa de origem / andar / recorte | bioma | tiles andáveis | spawns por modo (pontos x monstros por ponto = total)', '-' * 150]
    tot_and = 0
    for p in plano:
        ex = p.get('export') or {}; h = out['hunts'][p['id']]
        mobs = ', '.join(out['mobs'][k]['n'] for k in h['mobs'])
        sp = ex.get('spawns', 0)
        modos = '  '.join(f"{m[:3]} {min(v['n'], sp)}x{v['k']}={min(v['n'], sp) * v['k']}" for m, v in h['pull'].items())
        tot_and += ex.get('andaveis', 0)
        L.append(f"{p['num']:3d} | {p['nome']} | {mobs} | lv {p['lv']} | {p['mapa']} z{p['z']} [{p['caixa'][0]},{p['caixa'][1]}-{p['caixa'][2]},{p['caixa'][3]}] | {p['bioma']}{' (subsolo)' if p['sub'] else ''} | {ex.get('andaveis', '?')} andáveis ({ex.get('w', '?')}x{ex.get('h', '?')}) | spawns {sp}: {modos}")
    L += ['', f"Total: {len(plano)} caçadas, {len(out['mobs'])} monstros, {len(out['itens'])} itens, média de {tot_and // max(1, len(plano))} tiles andáveis por caçada."]
    open(os.path.join(DADOS, 'cacadas100_relatorio.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('relatório com', len(plano), 'linhas')


if __name__ == '__main__':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    et = sys.argv[1:] or ['plano', 'mapas', 'dados', 'icones', 'relatorio']
    for e in et:
        if e == 'plano': etapa_plano()
        elif e == 'mapas': etapa_mapas()
        elif e == 'dados': etapa_dados()
        elif e == 'icones': etapa_icones()
        elif e == 'relatorio': etapa_relatorio()
