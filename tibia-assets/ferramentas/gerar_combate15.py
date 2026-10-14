#!/usr/bin/env python3
"""Gera o combate no estilo do cliente: efeitos e projéteis do 15.01 + magias e ataques de monstros do Canary.

- Efeitos (CONST_ME_*) e projéteis (CONST_ANI_*) saem do .dat/.spr 15.01 em folhas (atlas).
  Efeito: quadros lado a lado com o tempo de cada quadro. Projétil: grade 3x3 com as 8 direções.
- Magias de ataque do sorcerer: lidas dos scripts do Canary (área, efeito, projétil, fórmula,
  cooldowns, condição de dano contínuo). As áreas vêm do register_spells.lua.
- Monstros (Demon e Fire Elemental): ataques, defesas, resistências e invocações do .lua do Canary.

Saída: combate15.js (window.COMB15) e sprites15/combate_N.png
"""
import glob, json, os, re, sys, urllib.request, urllib.parse
import concurrent.futures as cf
from PIL import Image
from ler_dat_moderno import DatModerno
from gerar_sprites15 import Gerador
from ler_magias_canary import ler as ler_canary

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
DADOS = os.path.join(RAIZ, 'dados')
LUA = os.path.join(DADOS, 'canary_magias')
CAMPOS = {'fire': 2118, 'energy': 2122, 'earth': 105}   # campos PvP do Canary (ITEM_FIREFIELD_PVP_FULL, ITEM_ENERGYFIELD_PVP, ITEM_POISONFIELD_PVP)
# preço de NPC aproximado de cada runa (por unidade)
PRECO_RUNA = {'sudden death': 135, 'great fireball': 57, 'avalanche': 57, 'thunderstorm': 52, 'stone shower': 37, 'ultimate healing': 175,
              'intense healing': 95, 'paralyze': 700, 'magic wall': 116, 'explosion': 31, 'heavy magic missile': 12, 'icicle': 30, 'fireball': 30,
              'soulfire': 46, 'energybomb': 203, 'firebomb': 147, 'poison bomb': 85, 'energy wall': 85, 'fire wall': 61, 'poison wall': 52,
              'energy field': 38, 'fire field': 28, 'poison field': 21, 'holy missile': 16, 'stalagmite': 12, 'desintegrate': 26,
              'destroy field': 15, 'wild growth': 160, 'chameleon': 210, 'convince creature': 80, 'animate dead': 375, 'antidote': 65,
              'light stone shower': 4, 'lightest missile': 4, 'lightest magic missile': 4, 'light magic missile': 4}


def constantes():
    c = json.load(open(os.path.join(DADOS, 'constantes_canary.json'), encoding='utf-8'))
    me = {n: i for n, i in (c['efeitos'].items() if isinstance(c['efeitos'], dict) else c['efeitos'])}
    ani = {n: i for n, i in (c['projeteis'].items() if isinstance(c['projeteis'], dict) else c['projeteis'])}
    return me, ani


def areas():
    txt = open(os.path.join(LUA, 'register_spells.lua'), encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^(AREA\w*)\s*=\s*\{(.*?)^\}', txt, re.S | re.M):
        linhas = [[int(v) for v in re.findall(r'-?\d+', l)] for l in re.findall(r'\{([^{}]*)\}', m.group(2))]
        if linhas: out[m.group(1)] = linhas
    return out


def num(rx, s, padrao=None, f=float):
    m = re.search(rx, s)
    return f(m.group(1)) if m else padrao


def ler_magia(arq, me, ani, AREAS):
    s = open(os.path.join(LUA, arq), encoding='utf-8').read()
    nome = re.search(r'spell:name\("([^"]+)"\)', s).group(1)
    palavras = re.search(r'spell:words\("([^"]+)"\)', s).group(1)
    tipo = num(r'COMBAT_PARAM_TYPE,\s*COMBAT_(\w+?)DAMAGE', s, None, str)
    el = {'ENERGY': 'energy', 'FIRE': 'fire', 'DEATH': 'death', 'EARTH': 'earth', 'ICE': 'ice', 'HOLY': 'holy', 'PHYSICAL': 'phys'}.get(tipo, 'phys')
    ef = re.search(r'COMBAT_PARAM_EFFECT,\s*(CONST_ME_\w+)', s)
    tiro = re.search(r'COMBAT_PARAM_DISTANCEEFFECT,\s*(CONST_ANI_\w+)', s)
    area = re.search(r'createCombat(?:Area)?\((?:\w+,\s*)?(AREA_\w+)', s)
    fmin = re.search(r'local min = \(level / 5\) \+ \(maglevel \* ([\d.]+)\)(?: \+ ([\d.]+))?', s)
    fmax = re.search(r'local max = \(level / 5\) \+ \(maglevel \* ([\d.]+)\)(?: \+ ([\d.]+))?', s)
    gcd = re.search(r'spell:groupCooldown\(([\d* ]+)(?:,\s*([\d* ]+))?\)', s)
    ticks = [[int(n), int(i), int(d)] for n, i, d in re.findall(r'addDamage\((\d+),\s*(\d+),\s*-(\d+)\)', s)]
    grupos = re.search(r'spell:group\(([^)]*)\)', s).group(1)
    av = lambda e: eval(e) if e else 0
    m = {'nome': nome, 'palavras': palavras, 'id': palavras.replace(' ', '_'), 'el': el,
         'lv': int(num(r'spell:level\((\d+)\)', s, 1)), 'mana': int(num(r'spell:mana\((\d+)\)', s, 0)),
         'cd': int(av(num(r'spell:cooldown\(([\d* ]+)\)', s, '2000', str))),
         'gcd': int(av(gcd.group(1))) if gcd else 2000, 'focus': int(av(gcd.group(2))) if gcd and gcd.group(2) and 'focus' in grupos else 0,
         'alcance': int(num(r'spell:range\((\d+)\)', s, 0)),
         'ef': me.get(ef.group(1)) if ef else None, 'tiro': ani.get(tiro.group(1)) if tiro else None,
         'aprender': 'needLearn(true)' in s}
    if fmin and fmax:
        m['f'] = [float(fmin.group(1)), float(fmin.group(2) or 0), float(fmax.group(1)), float(fmax.group(2) or 0)]
    if ticks: m['dot'] = ticks
    if area:
        m['area'] = AREAS[area.group(1)]; m['area_nome'] = area.group(1)
        m['t'] = 'onda' if 'needDirection(true)' in s else 'self'
    else:
        m['t'] = 'dot' if ticks and 'f' not in m else 'alvo'
        if not m['alcance']: m['alcance'] = 3
    return m


def ler_monstro(arq, me, ani):
    s = open(os.path.join(LUA, arq), encoding='utf-8').read()
    def bloco(nome):
        i = s.find(f'monster.{nome} = {{')
        if i < 0: return ''
        j, prof = s.index('{', i), 0
        for k in range(j, len(s)):
            prof += {'{': 1, '}': -1}.get(s[k], 0)
            if prof == 0: return s[j:k + 1]
        return ''
    def entradas(b):
        out = []
        for e in re.findall(r'\{\s*name\s*=\s*"[^"]+"[^{}]*\}', b):
            d = {}
            for k, v in re.findall(r'(\w+)\s*=\s*("[^"]*"|[-\w.]+)', e):
                v = v.strip('"')
                if v.startswith('CONST_ME_'): v = me.get(v)
                elif v.startswith('CONST_ANI_'): v = ani.get(v)
                elif v.startswith('COMBAT_'): v = v[7:].replace('DAMAGE', '').lower()
                elif v in ('true', 'false'): v = v == 'true'
                else:
                    try: v = float(v) if '.' in v else int(v)
                    except ValueError: pass
                d[k] = v
            out.append(d)
        return out
    el = {t.replace('DAMAGE', '').lower(): int(p) for t, p in re.findall(r'type = COMBAT_(\w+), percent = (-?\d+)', bloco('elements'))}
    el = {{'physical': 'phys'}.get(k, k): v for k, v in el.items()}
    inv = [{'nome': n, 'chance': int(c)} for n, c in re.findall(r'name = "([^"]+)", chance = (\d+)', bloco('summon'))]
    o = bloco('outfit'); fl = bloco('flags')
    return {'nome': num(r'createMonsterType\("([^"]+)"', s, None, str),
            'look': int(num(r'lookType = (\d+)', o, 0)), 'cores': [int(num(rf'look{c} = (\d+)', o, 0)) for c in ('Head', 'Body', 'Legs', 'Feet')],
            'addons': int(num(r'lookAddons = (\d+)', o, 0)),
            'invocavel': bool(re.search(r'summonable = true', fl)), 'custo': int(num(r'monster.manaCost = (\d+)', s, 0)),
            'hp': int(num(r'monster.health = (\d+)', s)), 'exp': int(num(r'monster.experience = (\d+)', s, 0)),
            'vel': int(num(r'monster.speed = (\d+)', s)), 'cadaver': int(num(r'monster.corpse = (\d+)', s, 0)),
            'arm': int(num(r'armor = (\d+)', bloco('defenses'), 0)), 'def': int(num(r'defense = (\d+)', bloco('defenses'), 0)),
            'ataques': entradas(bloco('attacks')), 'defesas': entradas(bloco('defenses')), 'elementos': el,
            'invoca': inv, 'max_invoca': int(num(r'maxSummons = (\d+)', bloco('summon'), 0))}


def invocaveis(me, ani):
    """Monstros do jogo que o Canary marca como 'summonable' (alvo do utevo res), com o custo de mana."""
    RAW = 'https://raw.githubusercontent.com/opentibiabr/canary/main/data-otservbr-global/monster/'
    js = open(os.path.join(RAIZ, 'dados_jogo.js'), encoding='utf-8').read()
    mobs = json.loads(js[js.index('{'):js.rindex('}') + 1])['mobs']
    canary = {m['nome'].lower(): m for m in json.load(open(os.path.join(DADOS, 'monstros_canary.json'), encoding='utf-8'))}
    pasta = os.path.join(LUA, 'monstros'); os.makedirs(pasta, exist_ok=True)
    pedidos = {k: canary[v['n'].lower()]['arquivo'] for k, v in mobs.items() if v['n'].lower() in canary}
    def baixa(item):
        k, arq = item; d = os.path.join(pasta, k + '.lua')
        if not os.path.exists(d):
            try: open(d, 'wb').write(urllib.request.urlopen(RAW + urllib.parse.quote(arq), timeout=60).read())
            except Exception: return None
        return k
    with cf.ThreadPoolExecutor(16) as ex: prontos = [k for k in ex.map(baixa, pedidos.items()) if k]
    out = {}
    for k in prontos:
        mo = ler_monstro(os.path.join('monstros', k + '.lua'), me, ani)
        if mo['invocavel'] and mo['custo']: out[k] = mo
    return out


class Atlas:
    def __init__(self, larg=2048):
        self.larg, self.folhas, self.atual, self.cx, self.cy, self.alt = larg, [], Image.new('RGBA', (larg, larg)), 0, 0, 0

    def por(self, im):
        if self.cx + im.width > self.larg: self.cx, self.cy, self.alt = 0, self.cy + self.alt, 0
        if self.cy + im.height > self.larg:
            self.folhas.append(self.atual); self.atual = Image.new('RGBA', (self.larg, self.larg)); self.cx = self.cy = self.alt = 0
        pos = (len(self.folhas), self.cx, self.cy)
        self.atual.paste(im, (self.cx, self.cy)); self.cx += im.width; self.alt = max(self.alt, im.height)
        return pos

    def salvar(self, prefixo):
        self.folhas.append(self.atual.crop((0, 0, self.larg, self.cy + self.alt)))
        srcs = []
        for i, f in enumerate(self.folhas):
            arq = f'{prefixo}_{i}.png'; f.save(os.path.join(RAIZ, 'sprites15', arq), optimize=True)
            srcs.append(f'tibia-assets/sprites15/{arq}')
        return srcs


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    me, ani = constantes(); AREAS = areas()
    G = Gerador(); dat = G.dat
    A = Atlas(); efeitos, tiros = {}, {}

    for i, t in dat.efeitos.items():
        g = t['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
        fr = [G.quadro(g, 0, 0, f, 0, W, H) for f in range(g['fases'])]
        if not any(q.getbbox() for q in fr): continue
        tira = Image.new('RGBA', (W * len(fr), H))
        for k, q in enumerate(fr): tira.paste(q, (k * W, 0))
        f, x, y = A.por(tira)
        efeitos[i] = {'f': f, 'x': x, 'y': y, 'w': W, 'h': H, 'n': len(fr), 'ms': g['anim']['ms'] if g['anim'] else [100]}
    for i, t in dat.projeteis.items():
        g = t['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
        grade = Image.new('RGBA', (W * 3, H * 3))
        for py in range(3):
            for px in range(3):
                q = Image.new('RGBA', (W, H))
                for yy in range(g['h']):
                    for xx in range(g['w']):
                        k = DatModerno.idx(g, xx, yy, 0, px % g['px'], py % g['py'], 0, 0)
                        sid = g['spr'][k] if k < len(g['spr']) else 0
                        if sid: q.alpha_composite(G.sprite(sid), (W - (xx + 1) * 32, H - (yy + 1) * 32))
                grade.paste(q, (px * W, py * H))
        if not grade.getbbox(): continue
        f, x, y = A.por(grade)
        tiros[i] = {'f': f, 'x': x, 'y': y, 'w': W, 'h': H}
    # campos (itens animados criados por runas e monstros)
    campos = {}
    for el, cid in CAMPOS.items():
        t = dat.itens.get(cid)
        if not t: continue
        g = t['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
        tira = Image.new('RGBA', (W * g['fases'], H))
        for k in range(g['fases']): tira.paste(G.quadro(g, 0, 0, k, 0, W, H), (k * W, 0))
        if not tira.getbbox(): continue
        f, x, y = A.por(tira)
        campos[el] = {'f': f, 'x': x, 'y': y, 'w': W, 'h': H, 'n': g['fases'], 'ms': g['anim']['ms'] if g['anim'] else [150], 'item': cid}

    srcs = A.salvar('combate')
    for d in list(efeitos.values()) + list(tiros.values()) + list(campos.values()): d['src'] = srcs[d.pop('f')]

    # ---- todas as magias e runas das 4 vocações (Canary)
    magias = []
    arqs = sorted(glob.glob(os.path.join(LUA, '*.lua')) + glob.glob(os.path.join(LUA, 'runas', '*.lua')))
    for a in arqs:
        if os.path.basename(a) in ('register_spells.lua', 'demon.lua', 'fire_elemental.lua', 'familiar.lua', 'magic_shield.lua'): continue
        m = ler_canary(a, me, ani, AREAS)
        if not m or not (m['voc'] or m.get('runa')): continue
        magias.append(m)
    magias.append(ler_canary(os.path.join(LUA, 'magic_shield.lua'), me, ani, AREAS))
    runas = {m['item']: m for m in magias if m.get('runa')}
    # ícones das runas (item do .dat, quadro parado)
    os.makedirs(os.path.join(RAIZ, 'sprites15', 'itens'), exist_ok=True)
    for cid, m in runas.items():
        im = G.folha_item(cid, os.path.join(RAIZ, 'sprites15', 'itens', f'{cid}.png'))
        if im: m['icone'] = f'tibia-assets/sprites15/itens/{cid}.png'
        m['preco'] = PRECO_RUNA.get(m['nome'].lower().replace(' rune', ''), 50)
        if m.get('cria'): m['campo'] = {'ITEM_FIREFIELD_PVP_FULL': 'fire', 'ITEM_ENERGYFIELD_PVP': 'energy', 'ITEM_POISONFIELD_PVP': 'earth'}.get(m['cria'])
    for m in magias:
        if m['t'] == 'conjurar':
            alvo = runas.get(m['conj'][1])
            if alvo: m['conj_runa'] = 'runa_' + str(m['conj'][1])
            else: m['t'] = 'util'                                    # flechas e itens que o jogo não usa
        if m['t'] == 'familiar': m['familiar'] = m['voc'][0] + '_familiar' if m['voc'] else None
    from collections import Counter
    print('magias/runas', len(magias), Counter(m['t'] for m in magias))

    # ---- monstros com ataques completos: Demon, Fire Elemental, familiares e invocáveis (utevo res)
    monstros = {'demon': ler_monstro('demon.lua', me, ani), 'fire_elemental': ler_monstro('fire_elemental.lua', me, ani)}
    criaturas = {}
    for a in sorted(glob.glob(os.path.join(LUA, 'familiares', '*.lua'))):
        k = os.path.basename(a)[:-4]
        if k.startswith('monk'): continue
        mo = ler_monstro(os.path.join('familiares', os.path.basename(a)), me, ani); mo['familiar'] = True
        monstros[k] = mo
        meta = G.folha_criatura(mo['look'], mo['cores'], mo['addons'], os.path.join(RAIZ, 'sprites15', 'criaturas', k + '.png'))
        if meta: meta['src'] = f'tibia-assets/sprites15/criaturas/{k}.png'; criaturas[k] = meta
    for k, mo in invocaveis(me, ani).items():
        monstros.setdefault(k, mo)
    for k, v in monstros.items(): print(k, v['hp'], v['exp'], 'ataques', len(v['ataques']), 'invocável' if v.get('invocavel') else '', v.get('custo', ''))

    nomes_me = {k[9:].lower(): v for k, v in me.items()}
    out = {'efeitos': efeitos, 'tiros': tiros, 'campo_fogo': campos.get('fire'), 'campos': campos, 'magias': magias, 'monstros': monstros,
           'criaturas': criaturas, 'me': nomes_me, 'ani': {k[10:].lower(): v for k, v in ani.items()}}
    with open(os.path.join(RAIZ, 'combate15.js'), 'w', encoding='utf-8') as fp:
        fp.write('/* gerado por ferramentas/gerar_combate15.py (efeitos do cliente 15.01 + magias e monstros do Canary) */\nwindow.COMB15=' + json.dumps(out, separators=(',', ':'), ensure_ascii=False) + ';\n')
    print('efeitos', len(efeitos), 'projéteis', len(tiros), 'folhas', srcs)


if __name__ == '__main__':
    main()
