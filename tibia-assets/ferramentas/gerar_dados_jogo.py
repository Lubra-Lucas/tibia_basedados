#!/usr/bin/env python3
"""
Gera tibia-assets/dados_jogo.js para o Tibia Idle a partir dos dados abertos do Canary
(github.com/opentibiabr/canary): monstros, loot, preços de NPC, peso dos itens e os spawns reais
do mapa. As imagens continuam vindo do TibiaWiki BR (o jogo carrega pelo nome).

Uso: python gerar_dados_jogo.py   (baixa o que faltar para ../dados e escreve ../dados_jogo.js)
"""
import concurrent.futures as cf, json, math, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, '..', 'dados')
RAW = 'https://raw.githubusercontent.com/opentibiabr/canary/main/'
REG = 36            # meia largura da região de cada hunt (72x72 tiles), igual ao jogo
MAX_ESTRELAS = 2

# hunts de nível alto que já existiam no jogo (locais reais)
ALTAS = {
    'dragons': ('Covil dos Dragões', 'Dragon'),
    'spiders': ('Ninho de Giant Spiders', 'Giant Spider'),
    'dls': ('Covil dos Dragon Lords', 'Dragon Lord'),
    'hydras': ('Caverna das Hydras', 'Hydra'),
    'behes': ('Caverna dos Behemoths', 'Behemoth'),
    'demons': ('Covil dos Demônios', 'Demon'),
}
CIDADES = {'Thais': (32369, 32241), 'Carlin': (32360, 31782), 'Venore': (32957, 32076), "Ab'Dendriel": (32732, 31634),
           'Kazordoon': (32649, 31925), 'Edron': (33217, 31814), 'Darashia': (33213, 32454), 'Ankrahmun': (33194, 32853),
           'Port Hope': (32594, 32745), 'Liberty Bay': (32317, 32826), 'Svargrond': (32212, 31132), 'Yalahar': (32787, 31276),
           'Rookgaard': (32097, 32219), 'Farmine': (33023, 31521), 'Gray Beach': (33447, 31323), 'Rathleton': (33594, 31899),
           'Roshamuul': (33513, 32363), 'Issavi': (33921, 31477), 'Krailos': (33657, 31665), 'Dawnport': (32064, 31894)}
ELEM = {'PHYSICAL': 'phys', 'FIRE': 'fire', 'ENERGY': 'energy', 'EARTH': 'poison', 'ICE': 'ice', 'HOLY': 'holy', 'DEATH': 'death',
        'LIFEDRAIN': 'death', 'MANADRAIN': 'energy', 'DROWN': 'ice'}
PEQUENAS = {'of', 'the', 'a', 'an', 'and', 'in', 'on', 'with', 'for', 'to', 'from'}


def baixar(caminho, destino=None):
    if destino and os.path.exists(destino):
        return open(destino, encoding='utf-8').read()
    for _ in range(3):
        try:
            t = urllib.request.urlopen(RAW + urllib.parse.quote(caminho), timeout=60).read().decode('utf-8', 'replace')
            if destino: open(destino, 'w', encoding='utf-8').write(t)
            return t
        except Exception as e:
            err = e
    print('falhou', caminho, err); return None

def titulo(n):
    p = n.split(' ')
    return ' '.join(w if (i and w.lower() in PEQUENAS) else (w[:1].upper() + w[1:]) for i, w in enumerate(p))

def slug(n):
    return re.sub(r'[^a-z0-9]+', '_', n.lower()).strip('_')

def num(rx, s, d=0):
    m = re.search(rx, s); return int(m.group(1)) if m else d

def bloco(s, nome):
    """Conteúdo de 'monster.<nome> = { ... }' respeitando chaves aninhadas."""
    i = s.find(f'monster.{nome} =')
    if i < 0: return ''
    i = s.find('{', i); prof = 0
    for j in range(i, len(s)):
        if s[j] == '{': prof += 1
        elif s[j] == '}':
            prof -= 1
            if prof == 0: return s[i + 1:j]
    return ''

def entradas(b):
    out, prof, ini = [], 0, None
    for j, c in enumerate(b):
        if c == '{':
            if prof == 0: ini = j
            prof += 1
        elif c == '}':
            prof -= 1
            if prof == 0: out.append(b[ini + 1:j])
    return out


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    mons = {m['nome']: m for m in json.load(open(os.path.join(DADOS, 'monstros_canary.json'), encoding='utf-8'))}
    baixos = {n for n, m in mons.items() if m['estrelas'] is not None and m['estrelas'] <= MAX_ESTRELAS}

    # ---------- spawns reais
    xml = baixar('data-otservbr-global/world/otservbr-monster.xml', os.path.join(DADOS, '_spawns.xml'))
    spawns = []
    for g in ET.fromstring(xml):
        cx, cy, cz = int(g.get('centerx')), int(g.get('centery')), int(g.get('centerz'))
        for m in g:
            n = m.get('name')
            if n in mons:
                spawns.append((n, cx + int(m.get('x', 0)), cy + int(m.get('y', 0)), cz, int(m.get('spawntime', 60))))
    print('spawns', len(spawns))
    por_z = defaultdict(list)
    for s in spawns: por_z[s[3]].append(s)

    def na_regiao(cx, cy, z):
        return [s for s in por_z[z] if abs(s[1] - cx) < REG and abs(s[2] - cy) < REG]

    # ---------- escolha das hunts (cobre todos os monstros baixos que dão exp)
    alvo = {n for n in baixos if mons[n]['exp'] > 0}
    balde = defaultdict(list)
    for s in spawns:
        if s[0] in baixos: balde[(s[1] // 16, s[2] // 16, s[3])].append(s)
    cand = {}
    for (bx, by, z) in list(balde):
        if not any(s[0] in alvo for s in balde[(bx, by, z)]): continue
        cx, cy = bx * 16 + 8, by * 16 + 8
        ss = [s for dx in range(-3, 4) for dy in range(-3, 4) for s in balde.get((bx + dx, by + dy, z), ())
              if abs(s[1] - cx) < REG and abs(s[2] - cy) < REG]
        cand[(cx, cy, z)] = ({s[0] for s in ss if s[0] in alvo}, len(ss))
    cobertos, hunts = set(), []
    while True:
        melhor, mv = None, 0
        for k, (nomes, total) in cand.items():
            novos = nomes - cobertos
            if not novos: continue
            v = len(novos) * 30 + min(total, 60)
            if v > mv: mv, melhor = v, (k, novos)
        if not melhor: break
        (cx, cy, z), novos = melhor
        cobertos |= novos
        hunts.append({'x': cx, 'y': cy, 'z': z})
    sem_spawn = sorted(alvo - cobertos)
    print('hunts baixas', len(hunts), '| monstros cobertos', len(cobertos), '| sem spawn no mapa', len(sem_spawn))

    # hunts altas: o lugar real com mais spawns de cada monstro
    todos = defaultdict(list)
    for s in spawns: todos[(s[1] // 16, s[2] // 16, s[3])].append(s)
    for k, (nome, alvo_n) in ALTAS.items():
        melhor, mv = None, 0
        for (bx, by, z), lst in todos.items():
            if not any(s[0] == alvo_n for s in lst): continue
            cx, cy = bx * 16 + 8, by * 16 + 8
            n = sum(1 for dx in range(-3, 4) for dy in range(-3, 4) for s in todos.get((bx + dx, by + dy, z), ())
                    if s[0] == alvo_n and abs(s[1] - cx) < REG and abs(s[2] - cy) < REG)
            if n > mv: mv, melhor = n, (cx, cy, z)
        if melhor:
            hunts.append({'id': k, 'nome': nome, 'x': melhor[0], 'y': melhor[1], 'z': melhor[2], 'alta': True})
            print(f'  {nome}: {mv} spawns de {alvo_n} em {melhor}')

    # ---------- monta cada hunt com os spawns reais
    usados = set()
    for i, h in enumerate(hunts):
        ss = na_regiao(h['x'], h['y'], h['z'])
        if not h.get('alta'): ss = [s for s in ss if s[0] in baixos]
        h['spawns'] = [[s[1] - (h['x'] - REG), s[2] - (h['y'] - REG), s[0], s[4]] for s in ss]
        cont = Counter(s[0] for s in ss)
        h['mobs'] = dict(cont)
        usados |= set(cont)
    print('monstros usados nas hunts', len(usados))

    # ---------- detalhes de cada monstro (ataques, defesa, loot)
    def ler(n):
        return n, baixar('data-otservbr-global/monster/' + mons[n]['arquivo'])
    textos = {}
    with cf.ThreadPoolExecutor(24) as ex:
        for n, t in ex.map(ler, sorted(usados)): textos[n] = t

    # ---------- itens: nome/peso (items.xml) e preço de venda (NPCs)
    ixml = baixar('data/items/items.xml', os.path.join(DADOS, '_items.xml'))
    id_nome, nome_peso = {}, {}
    for it in ET.fromstring(ixml).iter('item'):
        nm = it.get('name')
        if not nm: continue
        ids = [int(it.get('id'))] if it.get('id') else list(range(int(it.get('fromid', 0)), int(it.get('toid', -1)) + 1))
        w = next((int(a.get('value')) for a in it.iter('attribute') if a.get('key') == 'weight'), 0)
        for i in ids: id_nome[i] = nm
        nome_peso.setdefault(nm.lower(), w)
    precos_path = os.path.join(DADOS, '_precos_npc.json')
    if os.path.exists(precos_path):
        precos = json.load(open(precos_path, encoding='utf-8'))
    else:
        npcs = [p for p in open(os.path.join(DADOS, '_canary_paths.txt')).read().split('\n') if p.startswith('data-otservbr-global/npc/') and p.endswith('.lua')]
        precos = {}
        with cf.ThreadPoolExecutor(24) as ex:
            for t in ex.map(baixar, npcs):
                if not t: continue
                for m in re.finditer(r'itemName\s*=\s*"([^"]+)"[^}]*?\bsell\s*=\s*(\d+)', t):
                    k = m.group(1).lower(); precos[k] = max(precos.get(k, 0), int(m.group(2)))
        json.dump(precos, open(precos_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print('preços de NPC', len(precos))

    itens, saida_mobs = {}, {}
    for n in sorted(usados):
        s, m = textos[n], mons[n]
        if not s: continue
        ataques = entradas(bloco(s, 'attacks'))
        melee, magias = 0, []
        for a in ataques:
            nm = re.search(r'name\s*=\s*"([^"]+)"', a)
            mx = num(r'maxDamage\s*=\s*-?(\d+)', a)
            mn = num(r'minDamage\s*=\s*-?(\d+)', a)
            if not nm or not mx: continue
            if nm.group(1) == 'melee': melee = max(melee, mx); continue
            tp = re.search(r'type\s*=\s*COMBAT_([A-Z]+)DAMAGE', a)
            sh = re.search(r'shootEffect\s*=\s*CONST_ANI_([A-Z0-9_]+)', a)
            ef = re.search(r'effect\s*=\s*CONST_ME_([A-Z0-9_]+)', a)
            magias.append({'c': num(r'chance\s*=\s*(\d+)', a, 10), 'min': mn, 'max': mx, 'el': ELEM.get(tp.group(1) if tp else 'PHYSICAL', 'phys'),
                           'r': num(r'range\s*=\s*(\d+)', a, 1) or max(num(r'length\s*=\s*(\d+)', a), num(r'radius\s*=\s*(\d+)', a), 1),
                           'n': titulo(nm.group(1).replace('_', ' ')) if nm.group(1) != 'combat' else (tp.group(1).title() + ' Attack' if tp else 'Attack'),
                           'tiro': sh.group(1).lower() if sh else None, 'ef': ef.group(1).lower() if ef else None})
        defe = bloco(s, 'defenses')
        loot, gold = [], 0
        for e in entradas(bloco(s, 'loot')):
            ch = num(r'chance\s*=\s*(\d+)', e) / 100000
            if 'name' in e:
                nm = re.search(r'name\s*=\s*"([^"]+)"', e).group(1)
            else:
                nm = id_nome.get(num(r'id\s*=\s*(\d+)', e), '')
            if not nm: continue
            mc = num(r'maxCount\s*=\s*(\d+)', e, 1)
            if nm.lower() == 'gold coin': gold = mc; continue
            if nm.lower() in ('platinum coin', 'crystal coin'): continue
            k = slug(nm)
            if k not in itens:
                itens[k] = {'n': titulo(nm), 'w': round(nome_peso.get(nm.lower(), 100) / 100, 2), 'v': precos.get(nm.lower(), 0)}
            loot.append([k, round(ch, 5), mc] if mc > 1 else [k, round(ch, 5)])
        bt = bloco(s, 'Bestiary')
        saida_mobs[slug(n)] = {
            'n': n, 'hp': m['hp'], 'exp': m['exp'], 'hit': melee, 'gold': [0, gold], 'spd': num(r'monster\.speed\s*=\s*(\d+)', s, 80),
            'arm': num(r'armor\s*=\s*(\d+)', defe), 'def': num(r'defense\s*=\s*(\d+)', defe),
            'est': m['estrelas'], 'classe': m['classe'], 'magias': magias, 'loot': loot,
            'best': [num(r'FirstUnlock\s*=\s*(\d+)', bt, 10), num(r'SecondUnlock\s*=\s*(\d+)', bt, 100), num(r'toKill\s*=\s*(\d+)', bt, 500)],
            'charm': num(r'CharmsPoints\s*=\s*(\d+)', bt, 5),
            'dead': None}

    # ---------- nome, cidade mais próxima e level recomendado de cada hunt
    def andar(z): return 'superfície' if z == 7 else (f'subsolo {z - 7}' if z > 7 else f'andar +{7 - z}')
    saida_hunts = {}
    for i, h in enumerate(hunts):
        cid = min(CIDADES, key=lambda c: (CIDADES[c][0] - h['x']) ** 2 + (CIDADES[c][1] - h['y']) ** 2)
        ordem = [n for n, _ in Counter(h['mobs']).most_common() if mons[n]['exp'] > 0] or list(h['mobs'])
        exps = sorted(mons[n]['exp'] for n in h['mobs'] for _ in range(h['mobs'][n]) if mons[n]['exp'] > 0) or [1]
        p75 = exps[int(len(exps) * .75)]
        lv = max(1, min(200, round(p75 ** 0.7 / 1.5)))
        nome = (h['nome'] if h.get('nome') else ' e '.join(ordem[:2])) + f' — {cid}'
        rep = sum(1 for v in saida_hunts.values() if v['n'].split(' (')[0] == nome)
        if rep: nome += f' ({rep + 1})'
        hid = h.get('id') or slug(f'{ordem[0]}_{cid}_{h["z"]}_{i}')
        saida_hunts[hid] = {'n': nome, 'cidade': cid, 'andar': andar(h['z']), 'lv': lv, 'x': h['x'], 'y': h['y'], 'z': h['z'],
                            'mobs': {slug(n): c for n, c in h['mobs'].items()}, 'spawns': [[x, y, slug(n), t] for x, y, n, t in h['spawns']]}
    saida_hunts = dict(sorted(saida_hunts.items(), key=lambda kv: (kv[1]['lv'], kv[1]['n'])))

    out = {'fonte': 'Canary (opentibiabr/canary) + mapa tibia-map-data; imagens do TibiaWiki BR',
           'mobs': saida_mobs, 'itens': itens, 'hunts': saida_hunts, 'sem_spawn': sem_spawn}
    destino = os.path.join(AQUI, '..', 'dados_jogo.js')
    with open(destino, 'w', encoding='utf-8') as f:
        f.write('/* gerado por ferramentas/gerar_dados_jogo.py */\nwindow.TIBIA_DATA=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'{len(saida_mobs)} monstros, {len(itens)} itens de loot, {len(saida_hunts)} hunts → {os.path.abspath(destino)} ({os.path.getsize(destino) // 1024} KB)')
    print('sem spawn no mapa:', ', '.join(sem_spawn))


if __name__ == '__main__':
    main()
