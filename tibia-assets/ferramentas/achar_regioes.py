#!/usr/bin/env python3
"""Procura regiões caçáveis nos .otbm: áreas andáveis conectadas de ~250 a 1.600 tiles, por andar.

Para cada mapa e andar:
  - andável = tem chão (flag 'chao' do .dat) e nenhum item com 'bloqueia' ou 'bloqueia_caminho' (mesma regra do exportar_mapa15);
  - componentes conectados (8 vizinhos); os grandes demais são recortados em janelas de 40x40 e cada janela
    fica com a maior peça andável (mínimo 250 tiles e 25% de densidade);
  - o bioma sai do nome do chão dominante (items.xml do TFS 10.98): grama, terra, areia, neve, pantano,
    lava, pedra, agua, construcao. Andares abaixo do 7 são subsolo.
Saída: dados/regioes_cacada.json (lista de regiões com caixa absoluta, nº de tiles, densidade, bioma e histograma de chão).
Uso: python achar_regioes.py [max_mb=30] [arquivo.otbm ...]
"""
import collections, glob, json, os, sys, time
import xml.etree.ElementTree as ET
import numpy as np
from scipy import ndimage
sys.setrecursionlimit(20000)
from ler_otbm import ler
from renderizar_otbm import Pintor

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
MAPAS = os.path.normpath(os.path.join(RAIZ, '..', 'MAPAS'))
MIN_TILES, MAX_TILES, JANELA = 250, 1600, 40

# nome do chão (items.xml do TFS) → bioma
BIOMA = {
    'grama': ['grass', 'jungle grass', 'dried grass', 'forest floor', 'flowers', 'leaves', 'lush grass', 'ploughed soil', 'soil', 'branches', 'teal leaves', 'gravel floor'],
    'terra': ['earth', 'dirt', 'dirt floor', 'rock soil', 'rock', 'grotto', 'dry earth', 'rutted earth', 'earth ground', 'gravel', 'stony floor', 'stone pebbles', 'mountain', 'dry floor', 'loose stone pile', 'organic structure'],
    'areia': ['sand', 'grey sand', 'sandstone', 'sandstone floor', 'sandstone tile', 'strange sand', 'sandy tile', 'wasteland', 'sandy floor', 'dark sandy floor'],
    'neve': ['ice', 'snow', 'ice floor', 'ice stone floor', 'fragile ice', 'fur', 'ice hole'],
    'pantano': ['muddy floor', 'mud', 'swamp', 'tar', 'mossy floor', 'muddy water', 'dirty water', 'corrupted mud', 'slime fungus', 'mold floor', 'slime', 'mossy wall', 'mushroom sponge'],
    'lava': ['lava', 'basalt', 'basalt floor', 'small lava cracks', 'sulphur', 'purple soil', 'strange colours', 'rift floor', 'overgrown rift floor', 'blood', 'iron floor'],
    'pedra': ['stone floor', 'black marble floor', 'white marble floor', 'stone tile', 'cracked temple floor', 'wet temple floor', 'marble floor', 'cracked jade floor', 'stone pebble floor', 'rutted stone', 'rutted stone floor', 'brown marble floor', 'carved stone tile', 'crystal floor', 'crystal glass floor', 'white stone tile', 'stone pavement', 'stony pavement'],
    'agua': ['shallow water', 'ocean floor', 'sea floor', 'coral stone', 'brown sea floor', 'water', 'small brook', 'flowing water', 'sunken ship'],
    'construcao': ['wooden floor', 'tiled floor', 'cobblestone', 'pavement', 'plaster', 'parquet floor', 'brown pavement', 'terracotta', 'wooden planks', 'timber floor', 'carpet', 'grimy wooden plank', 'ornamented floor', 'cobbled pavement', 'road', 'bridge', 'rope bridge', 'drawbridge', 'raft', 'metal grate', 'chess board', 'flat roof', 'tiled roof', 'roof', 'wooden roof'],
}
CATS = list(BIOMA)
NOME2CAT = {n: CATS.index(b) for b, ns in BIOMA.items() for n in ns}


def nomes_chao():
    nomes = {}
    for it in ET.parse(os.path.join(RAIZ, 'dados', '_items_tfs1098.xml')).getroot().iter('item'):
        nm = it.get('name') or ''
        if it.get('id'): nomes[int(it.get('id'))] = nm
        else:
            for i in range(int(it.get('fromid')), int(it.get('toid')) + 1): nomes[i] = nm
    return nomes


class Analisador:
    def __init__(self):
        self.P = Pintor()
        self.nomes = nomes_chao()
        self.cache = {}

    def info(self, sid):
        """(é chão, bloqueia, nome do chão) de um item do servidor."""
        r = self.cache.get(sid)
        if r is None:
            _, t = self.P.coisa(sid)
            f = t['flags'] if t else {}
            r = self.cache[sid] = ('chao' in f, 'bloqueia' in f or 'bloqueia_caminho' in f, self.nomes.get(sid, '?'))
        return r

    def andar(self, tiles, z):
        pts = [k for k in tiles if k[2] == z]
        if not pts: return None
        xs = np.array([k[0] for k in pts]); ys = np.array([k[1] for k in pts])
        X0, Y0 = int(xs.min()), int(ys.min()); W, H = int(xs.max()) - X0 + 1, int(ys.max()) - Y0 + 1
        if W * H > 90_000_000: return None
        walk = np.zeros((H, W), bool); nome = {}
        chao = np.zeros((H, W), bool)
        for (x, y, _), its in ((k, tiles[k]) for k in pts):
            g = b = False; gn = None
            for s in its:
                ig, ib, nm = self.info(s)
                if ig and not g: g = True; gn = nm
                if ib: b = True
            if g:
                chao[y - Y0, x - X0] = True
                if not b: walk[y - Y0, x - X0] = True
                nome[(x - X0, y - Y0)] = gn
        return X0, Y0, walk, nome

    def regioes(self, arquivo, tiles):
        out = []
        for z in sorted({k[2] for k in tiles}):
            r = self.andar(tiles, z)
            if r is None: continue
            X0, Y0, walk, nome = r
            lab, n = ndimage.label(walk, structure=np.ones((3, 3)))
            if n == 0: continue
            tam = ndimage.sum(walk, lab, range(1, n + 1))
            objs = ndimage.find_objects(lab)
            for i in range(n):
                if tam[i] < MIN_TILES: continue
                sl = objs[i]; h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
                comp = lab[sl] == i + 1
                if tam[i] <= MAX_TILES and w <= 64 and h <= 64:
                    out.append(self.registro(arquivo, z, X0 + sl[1].start, Y0 + sl[0].start, comp, nome, X0, Y0))
                    continue
                # recorta em janelas
                for gy in range(0, h, JANELA):
                    for gx in range(0, w, JANELA):
                        sub = comp[gy:gy + JANELA, gx:gx + JANELA]
                        if sub.sum() < MIN_TILES: continue
                        l2, n2 = ndimage.label(sub, structure=np.ones((3, 3)))
                        t2 = ndimage.sum(sub, l2, range(1, n2 + 1))
                        k = int(np.argmax(t2))
                        if t2[k] < MIN_TILES or t2[k] / sub.size < .25: continue
                        peca = l2 == k + 1
                        ys, xs = np.nonzero(peca)
                        out.append(self.registro(arquivo, z, X0 + sl[1].start + gx + int(xs.min()), Y0 + sl[0].start + gy + int(ys.min()),
                                                 peca[ys.min():ys.max() + 1, xs.min():xs.max() + 1], nome, X0, Y0, True))
        return out

    def registro(self, arquivo, z, x0, y0, mask, nome, X0, Y0, janela=False):
        h, w = mask.shape
        hist = collections.Counter(); cats = collections.Counter()
        ys, xs = np.nonzero(mask)
        for yy, xx in zip(ys, xs):
            nm = nome.get((x0 - X0 + int(xx), y0 - Y0 + int(yy)), '?')
            hist[nm] += 1
            cats[NOME2CAT.get(nm, -1)] += 1
        cats.pop(-1, None)
        bioma = CATS[cats.most_common(1)[0][0]] if cats else 'terra'
        return {'mapa': arquivo, 'z': z, 'x0': int(x0), 'y0': int(y0), 'x1': int(x0 + w), 'y1': int(y0 + h), 'tiles': int(mask.sum()),
                'dens': round(float(mask.sum()) / (w * h), 2), 'bioma': bioma, 'sub': z > 7, 'janela': janela,
                'cats': {CATS[k]: int(v) for k, v in cats.most_common(4)}, 'chao': dict(hist.most_common(5))}


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    args = sys.argv[1:]
    maxmb = float(args[0]) if args and args[0].replace('.', '').isdigit() else 30
    arqs = [a for a in args if a.lower().endswith('.otbm')]
    if not arqs:
        arqs = glob.glob(os.path.join(MAPAS, 'mapas1', '*.otbm')) + glob.glob(os.path.join(MAPAS, 'Classicos', '*.otbm'))
        arqs = [a for a in arqs if os.path.getsize(a) <= maxmb * 1e6]
    destino = os.path.join(RAIZ, 'dados', 'regioes_cacada.json')
    A = Analisador(); todas = []
    for f in sorted(arqs, key=os.path.getsize):
        t0 = time.time()
        try:
            tiles = ler(f)['tiles']
            regs = A.regioes(os.path.basename(f), tiles)
        except Exception as e:
            print('erro', f, repr(e), flush=True); continue
        todas += regs
        print(f'{os.path.basename(f)}: {len(regs)} regiões ({time.time() - t0:.1f}s)', flush=True)
        del tiles
    for i, r in enumerate(todas): r['id'] = i
    json.dump(todas, open(destino, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('total', len(todas), collections.Counter(r['bioma'] for r in todas), 'subsolo', sum(r['sub'] for r in todas))


if __name__ == '__main__':
    main()
