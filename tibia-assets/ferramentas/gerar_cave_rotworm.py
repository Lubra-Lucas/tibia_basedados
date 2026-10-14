#!/usr/bin/env python3
"""Gera a "Cave de Rotworm" (mapa próprio do jogo) com os gráficos originais do Tibia 7.4.

1) desenha a planta: dois anéis de corredor (formato de "8") com raio irregular (semente fixa);
2) classifica os tiles: chão / parede interna (encosta no chão) / parede externa (encosta na interna) / vazio (preto);
3) escolhe a peça de parede de cada tile por ASSINATURA VISUAL: cada peça (32x32) é dividida em 3x3 zonas e cada zona é
   marcada como 'vazio' (linha preta), 'chão' (faixa de terra clara) ou 'rocha'; as 8 vizinhas do tile dizem o que
   a peça precisa mostrar em cada zona. Vence a peça de melhor pontuação (empate: sorteio fixo por posição);
4) decoração (variação de chão e estalagmites que não bloqueiam a passagem), spawns e posição inicial;
5) exporta os PNGs dos tiles, a folha do rotworm, tibia-assets/mapas.js e uma prévia do mapa inteiro.

Uso:  python gerar_cave_rotworm.py [--sem-cinza]   (--sem-cinza descarta as peças com franja cinza)
"""
import sys, os, json, math, random
import numpy as np
from collections import deque
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from ler_spr import Spr
from ler_dat import Dat, montar

SPR = r'C:\Users\user\AppData\Local\Temp\Tibia (1).spr'
DAT = r'C:\Users\user\AppData\Local\Temp\Tibia.dat'
RAIZ = os.path.abspath(os.path.join(AQUI, '..'))          # tibia-assets
LOOK_ROTWORM = 26

# ---------------- peças ----------------
CHAO_BASE, CHAO_VAR = 351, [352, 353, 354, 355]
PAREDES = [356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 372, 374, 376, 377, 378, 381]
CINZAS = {372, 374, 376, 377, 378, 381}                    # versões com franja cinza
ESTALAG = [386, 387, 388, 389, 390, 391]
FLAT = 362                                                 # rocha lisa (reserva)

# ---------------- planta ----------------
LARG, ALT = 36, 54
CX, CY1, CY2 = 18, 17, 36                                  # centros dos dois anéis
R_EXT, R_INT = 11.0, 5.5                                   # raio externo e da ilha (corredor ~7 tiles)


def raio(theta, base, amp, fases):
    return base + sum(a * math.sin(k * theta + f) for (k, a), f in zip(amp, fases))


def planta(sem):
    rng = random.Random(sem)
    amp_e = [(2, 1.3), (3, 0.9), (5, 0.6)]
    amp_i = [(2, 0.7), (3, 0.6), (4, 0.4)]
    aneis = []
    for cy in (CY1, CY2):
        aneis.append((cy, [rng.uniform(0, 6.28) for _ in amp_e], [rng.uniform(0, 6.28) for _ in amp_i]))
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    chao = np.zeros((ALT, LARG), bool)
    for y in range(ALT):
        for x in range(LARG):
            ruido = 0.7 * math.sin(0.9 * x + ph[0] + 0.5 * y) + 0.6 * math.sin(0.7 * y + ph[1] - 0.4 * x) + 0.4 * math.sin(1.7 * x + 1.3 * y + ph[2])
            for cy, fe, fi in aneis:
                dx, dy = x - CX, y - cy
                d = math.hypot(dx, dy); th = math.atan2(dy, dx)
                if d <= raio(th, R_EXT, amp_e, fe) + 0.9 * ruido and d > raio(th, R_INT, amp_i, fi) + 0.6 * ruido:
                    chao[y, x] = True
    # limpeza: preenche reentrâncias de 1 tile e remove pontas finas
    def viz4(m, x, y):
        return sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < LARG and 0 <= y + dy < ALT and m[y + dy, x + dx])
    for _ in range(3):
        n = chao.copy()
        for y in range(1, ALT - 1):
            for x in range(1, LARG - 1):
                v = viz4(chao, x, y)
                if not chao[y, x] and v >= 3: n[y, x] = True
                elif chao[y, x] and v <= 1: n[y, x] = False
        chao = n
    # só o maior componente conectado
    lab = np.zeros(chao.shape, int); best, bn, c = 0, 0, 0
    for y in range(ALT):
        for x in range(LARG):
            if chao[y, x] and not lab[y, x]:
                c += 1; q = deque([(x, y)]); lab[y, x] = c; n = 0
                while q:
                    a, b = q.popleft(); n += 1
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            u, v = a + dx, b + dy
                            if 0 <= u < LARG and 0 <= v < ALT and chao[v, u] and not lab[v, u]:
                                lab[v, u] = c; q.append((u, v))
                if n > bn: best, bn = c, n
    return lab == best


def classes(chao):
    """'F' chão, '1' parede interna, '2' parede externa, 'V' vazio."""
    cls = np.full(chao.shape, 'V', dtype='<U1')
    cls[chao] = 'F'
    def tem(c, x, y):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                u, v = x + dx, y + dy
                if (dx or dy) and 0 <= u < LARG and 0 <= v < ALT and cls[v, u] == c: return True
        return False
    for y in range(ALT):
        for x in range(LARG):
            if cls[y, x] == 'V' and tem('F', x, y): cls[y, x] = '1'
    # parede externa: só onde ela leva a linha preta (lados N/O de uma parede interna); nos lados S/L a peça não tem linha e 1 tile basta
    for y in range(ALT):
        for x in range(LARG):
            if cls[y, x] == 'V' and any(0 <= x + dx < LARG and 0 <= y + dy < ALT and cls[y + dy, x + dx] == '1' for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 1), (1, -1))):
                cls[y, x] = '2'
    return cls


# ---------------- assinatura das peças ----------------
ZON = [(0, 11), (11, 21), (21, 32)]


def assinatura(img):
    """matriz 3x3 de 'V' (linha preta), 'F' (terra clara) ou 'R' (rocha)."""
    rgb = np.array(img.convert('RGBA')).astype(int)[:, :, :3]
    preto = (rgb.max(2) <= 22) & ((rgb.max(2) - rgb.min(2)) <= 8)       # só o preto da linha (o vermelho escuro das cristas tem R>G)
    clara = (rgb[:, :, 2] >= 28) & (rgb[:, :, 0] >= 100) & (rgb[:, :, 1] >= 45)   # terra do chão tem azul ~39; a rocha ~11
    s = []
    for zi, (y0, y1) in enumerate(ZON):
        linha = []
        for zj, (x0, x1) in enumerate(ZON):
            v = preto[y0:y1, x0:x1].mean(); f = clara[y0:y1, x0:x1].mean()
            canto = zi != 1 and zj != 1
            lim = 0.06 if canto else 0.2
            linha.append('V' if v >= 0.04 else 'F' if f >= lim else 'R')
        s.append(linha)
    return s


def pontos(rotulo, viz, lado_sombra):
    """pontuação de uma zona da peça (rotulo) contra a vizinha do mapa (viz). lado_sombra: lado sem linha preta (S/E)."""
    if viz == 'F':
        return {'F': 3, 'R': -1.5, 'V': -6}[rotulo]
    if viz == 'V':
        return {'V': 3, 'R': 0 if lado_sombra else -1, 'F': -6}[rotulo]
    return {'R': 0.5, 'V': -4, 'F': -4}[rotulo]


def escolher(cls, x, y, sigs, sem_cinza):
    viz = {}
    for zi in range(3):
        for zj in range(3):
            if zi == 1 and zj == 1: continue
            u, v = x + zj - 1, y + zi - 1
            c = cls[v, u] if 0 <= u < LARG and 0 <= v < ALT else 'V'
            viz[(zi, zj)] = 'F' if c == 'F' else 'V' if c == 'V' else 'W'
    pts = {}
    for pid, s in sigs.items():
        if sem_cinza and pid in CINZAS: continue
        t = 0
        for (zi, zj), vz in viz.items():
            t += pontos(s[zi][zj], vz, zi == 2 or zj == 2)
        t -= 0.05 * sum(1 for r in s for q in r if q != 'R')      # desempate: peça mais simples
        pts[pid] = t
    m = max(pts.values())
    melhores = sorted(p for p, t in pts.items() if t >= m - 0.075)
    h = (x * 73856093) ^ (y * 19349663)
    return melhores[h % len(melhores)], viz


def main():
    sem_cinza = '--sem-cinza' in sys.argv
    SEMENTE = int(sys.argv[sys.argv.index('--semente') + 1]) if '--semente' in sys.argv else 12
    spr, dat = Spr(SPR), Dat(DAT)
    chao = planta(SEMENTE)
    cls = classes(chao)
    img = {i: montar(spr, dat.itens[i]) for i in [CHAO_BASE] + CHAO_VAR + PAREDES}
    sigs = {i: assinatura(img[i]) for i in PAREDES}

    tiles = {}      # (x,y) -> [ids]
    usados_parede = {}
    for y in range(ALT):
        for x in range(LARG):
            c = cls[y, x]
            if c == 'V': continue
            if c == 'F':
                continue
            pid, _ = escolher(cls, x, y, sigs, sem_cinza)
            tiles[(x, y)] = [pid]; usados_parede[pid] = usados_parede.get(pid, 0) + 1

    rng = random.Random(SEMENTE)
    walk = np.zeros((ALT, LARG), np.uint8)
    for y in range(ALT):
        for x in range(LARG):
            if cls[y, x] == 'F':
                r = rng.random()
                f = CHAO_BASE if r > 0.10 else rng.choices(CHAO_VAR, [3, 3, 1, 1])[0]
                tiles[(x, y)] = [f]; walk[y, x] = 1

    # ---- estalagmites encostadas na parede, sem bloquear a passagem ----
    meio = (CY1 + CY2) / 2
    def conectado(w):
        pts = [(x, y) for y in range(ALT) for x in range(LARG) if w[y, x]]
        if not pts: return True
        seen = {pts[0]}; q = deque([pts[0]])
        while q:
            a, b = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    u, v = a + dx, b + dy
                    if 0 <= u < LARG and 0 <= v < ALT and w[v, u] and (u, v) not in seen:
                        seen.add((u, v)); q.append((u, v))
        return len(seen) == len(pts)
    cand = [(x, y) for y in range(ALT) for x in range(LARG) if cls[y, x] == 'F'
            and any(0 <= x + dx < LARG and 0 <= y + dy < ALT and cls[y + dy, x + dx] == '1' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            and abs(y - meio) > 5]
    rng.shuffle(cand)
    estal = []
    quais = [386, 387, 390, 391, 386, 387, 390, 391, 388, 389]
    for (x, y) in cand:
        if len(estal) >= 14: break
        if any(max(abs(x - a), abs(y - b)) < 4 for a, b, _ in estal): continue
        # não cola em outra estalagmite e mantém o chão conectado (inclusive sem estreitar demais)
        livres = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and walk[y + dy, x + dx])
        if livres < 5: continue
        walk[y, x] = 0
        if not conectado(walk): walk[y, x] = 1; continue
        est = quais[len(estal) % len(quais)]
        estal.append((x, y, est)); tiles[(x, y)].append(est)

    # ---- início e spawns ----
    inicio = (CX, int(round(meio)))
    if not walk[inicio[1], inicio[0]]:
        inicio = min(((x, y) for y in range(ALT) for x in range(LARG) if walk[y, x]), key=lambda p: (p[0] - CX) ** 2 + (p[1] - meio) ** 2)
    livres = [(x, y) for y in range(ALT) for x in range(LARG) if walk[y, x]]
    spawns = []
    for _ in range(4000):
        if len(spawns) >= 18: break
        x, y = rng.choice(livres)
        if max(abs(x - inicio[0]), abs(y - inicio[1])) < 5: continue
        if any(max(abs(x - a), abs(y - b)) < 4 for a, b in spawns): continue
        spawns.append((x, y))
    spawns.sort(key=lambda p: (p[1], p[0]))

    # ---- sprites dos tiles ----
    ids = sorted({i for v in tiles.values() for i in v})
    dtiles = os.path.join(RAIZ, 'sprites', 'tiles74'); os.makedirs(dtiles, exist_ok=True)
    meta_tiles = {}
    for i in ids:
        t = dat.itens[i]; n = t['fases']
        fr = [montar(spr, t, fase=f) for f in range(n)]
        w, h = fr[0].size
        folha = Image.new('RGBA', (w * n, h))
        for k, f in enumerate(fr): folha.paste(f, (k * w, 0))
        folha.save(os.path.join(dtiles, f'{i}.png'))
        meta_tiles[i] = {'src': f'tibia-assets/sprites/tiles74/{i}.png', 'w': w, 'h': h, 'n': n}
    # ---- rotworm ----
    t = dat.criaturas[LOOK_ROTWORM]
    fr = [[montar(spr, t, px=d, py=0, fase=f, layers=range(t['layers'])) for f in range(t['fases'])] for d in range(4)]
    w, h = fr[0][0].size
    folha = Image.new('RGBA', (w * t['fases'], h * 4))
    for d in range(4):
        for f in range(t['fases']): folha.paste(fr[d][f], (f * w, d * h))
    dcri = os.path.join(RAIZ, 'sprites', 'criaturas74'); os.makedirs(dcri, exist_ok=True)
    folha.save(os.path.join(dcri, 'rotworm.png'))
    meta_cri = {'rotworm': {'src': 'tibia-assets/sprites/criaturas74/rotworm.png', 'w': w, 'h': h, 'fases': t['fases'], 'dirs': 4}}

    # ---- mapas.js ----
    mapa = {'nome': 'Cave de Rotworm', 'w': LARG, 'h': ALT,
            'tiles': [[x, y, v] for (x, y), v in sorted(tiles.items(), key=lambda kv: (kv[0][1], kv[0][0]))],
            'walk': [int(v) for v in walk.flatten()],
            'spawns': [[x, y, 'rotworm', 60] for x, y in spawns], 'inicio': list(inicio), 'escuro': True}
    with open(os.path.join(RAIZ, 'mapas.js'), 'w', encoding='utf8') as f:
        f.write('/* gerado por ferramentas/gerar_cave_rotworm.py (gráficos do Tibia 7.4) */\n')
        f.write('window.MAPAS=' + json.dumps({'cave_rotworm': mapa}, separators=(',', ':')) + ';\n')
        f.write('window.MAPAS_SPRITES=' + json.dumps({'tiles': meta_tiles, 'criaturas': meta_cri}, separators=(',', ':')) + ';\n')

    # ---- prévia ----
    prev = Image.new('RGB', (LARG * 32, ALT * 32), (0, 0, 0))
    cache = {i: montar(spr, dat.itens[i]) for i in ids}
    for (x, y), v in tiles.items():
        for i in v:
            im = cache[i]; prev.paste(im, (x * 32 + 32 - im.width, y * 32 + 32 - im.height), im)
    dprev = os.path.join(RAIZ, 'spr_previa'); os.makedirs(dprev, exist_ok=True)
    prev.save(os.path.join(dprev, 'cave_rotworm_mapa.png'))
    # versão com spawns e início marcados
    from PIL import ImageDraw
    p2 = prev.copy(); dr = ImageDraw.Draw(p2)
    for x, y in spawns: dr.ellipse([x * 32 + 8, y * 32 + 8, x * 32 + 24, y * 32 + 24], outline=(255, 255, 0), width=2)
    dr.rectangle([inicio[0] * 32 + 6, inicio[1] * 32 + 6, inicio[0] * 32 + 26, inicio[1] * 32 + 26], outline=(0, 255, 0), width=3)
    p2.save(os.path.join(dprev, 'cave_rotworm_spawns.png'))

    print(f'mapa {LARG}x{ALT}; chão {int(chao.sum())} tiles; paredes {len(usados_parede) and sum(usados_parede.values())}; estalagmites {len(estal)}; spawns {len(spawns)}; início {inicio}')
    print('peças de parede usadas:', dict(sorted(usados_parede.items())))
    print('conectado:', conectado(walk))


if __name__ == '__main__':
    main()
