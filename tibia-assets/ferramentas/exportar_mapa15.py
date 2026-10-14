#!/usr/bin/env python3
"""Exporta um andar de um .otbm (TFS 10.98) para o jogo, com os sprites do cliente 15.01.

Cada tile vira no máximo duas imagens já montadas na ordem do cliente:
  - chão: chão + bordas (32x32), desenhado antes de tudo;
  - objetos: paredes, itens e peças por cima, com elevação e deslocamento, ancorados no canto
    inferior direito do tile (como os sprites grandes do Tibia), desenhados linha a linha junto com as criaturas.
Imagens iguais são reaproveitadas e tudo vai para poucas folhas (atlas). Itens animados (água, fogo) guardam os quadros.
Andável = tem chão e nenhum item com as flags 'bloqueia' ou 'bloqueia_caminho'.

Uso: python exportar_mapa15.py mapa.otbm chave "Nome" andar [x0 y0 x1 y1] [--spawns demon:10,rat:4] [--semente N]
  Com --spawns: fica só a maior área andável conectada, o início vai para a beira de baixo dela e os
  spawns são espalhados (6+ tiles entre si, 10+ do início).
Saída: mapas15/<chave>.js (window.MAPAS e window.MAPAS_SPRITES) + mapas15/<chave>_N.png

Como módulo (gerar_cacadas100.py): Exportador().exportar(..., tiles=<já carregado>, plano={'lideres':[...], 'pts':16, 'tempo':40},
  pasta='cacadas', prefixo='h07') reaproveita o mesmo .otbm para várias caçadas e devolve as estatísticas. Com 'plano', os spawns
  saem ordenados por "ponto mais distante" (os primeiros N já cobrem bem a área): Cauteloso usa os 6 primeiros, Ousado 10, Agressivo 16.
"""
import hashlib, json, math, os, random, sys
import numpy as np
from PIL import Image
sys.setrecursionlimit(20000)
from ler_otbm import ler
from renderizar_otbm import Pintor
from ler_dat_moderno import DatModerno

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
MAX_QUADROS = 8
ATLAS_LARG = 2048


def maior_area(walk, W, H):
    """Mantém só a maior região andável conectada (8 vizinhos)."""
    rot = [-1] * len(walk); melhor, tam_melhor = -1, 0
    for i, v in enumerate(walk):
        if not v or rot[i] >= 0: continue
        fila, rot[i], n = [i], i, 0
        while fila:
            c = fila.pop(); n += 1; x, y = c % W, c // W
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and walk[ny * W + nx] and rot[ny * W + nx] < 0:
                        rot[ny * W + nx] = i; fila.append(ny * W + nx)
        if n > tam_melhor: melhor, tam_melhor = i, n
    return [1 if r == melhor else 0 for r in rot]


def espalhar(walk, Wm, Hm, ini, n=16, minimo=3):
    """Pontos de spawn ordenados pelo "mais distante dos já escolhidos" (a partir da entrada): qualquer prefixo da lista cobre bem a área.
    Só tiles com 5+ vizinhos andáveis (cabe um grupo de monstros); a distância mínima cai até `minimo` se a área for apertada."""
    a = np.array(walk, dtype=np.uint8).reshape(Hm, Wm)
    viz = sum(np.pad(a, 1)[1 + dy:1 + dy + Hm, 1 + dx:1 + dx + Wm] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
    ys, xs = np.nonzero((a == 1) & (viz >= 5))
    if len(xs) < n: ys, xs = np.nonzero(a == 1)
    d = np.maximum(abs(xs - ini[0]), abs(ys - ini[1])).astype(int)
    d[d < 7] = 0                                                         # longe da entrada
    out = []
    while len(out) < n:
        k = int(np.argmax(d))
        if d[k] < minimo: break
        out.append((int(xs[k]), int(ys[k])))
        d = np.minimum(d, np.maximum(abs(xs - xs[k]), abs(ys - ys[k])))
        d[d < minimo] = 0
    return out


class Exportador(Pintor):
    def compor(self, itens, x, y, z, fundo):
        """Monta os itens (já na ordem) em n quadros. Devolve lista de imagens recortadas e (w, h)."""
        n = 1
        for t in itens:
            g = t['grupos'][0]
            if g['fases'] > 1: n = max(n, min(MAX_QUADROS, g['fases']))
        T = 32 * 4                                                       # tela de 4x4 tiles com o tile no canto inferior direito
        quadros = []
        for f in range(n):
            tela = Image.new('RGBA', (T, T)); elev = 0
            for t in itens:
                g = t['grupos'][0]; fl = t['flags']
                dx, dy = fl['deslocamento'] if isinstance(fl.get('deslocamento'), tuple) else (0, 0)
                for yy in range(g['h']):
                    for xx in range(g['w']):
                        i = DatModerno.idx(g, xx, yy, 0, x % g['px'], y % g['py'], z % g['pz'], f % g['fases'])
                        s = g['spr'][i] if i < len(g['spr']) else 0
                        if s: tela.alpha_composite(self.sprite(s), (T - 32 - xx * 32 - dx - elev, T - 32 - yy * 32 - dy - elev))
                elev += fl.get('elevacao', 0) or 0
            quadros.append(tela)
        if fundo:                                                         # chão: só o tile
            return [q.crop((T - 32, T - 32, T, T)) for q in quadros], (32, 32)
        caixa = None
        for q in quadros:
            b = q.getbbox()
            if b: caixa = b if not caixa else (min(caixa[0], b[0]), min(caixa[1], b[1]), max(caixa[2], b[2]), max(caixa[3], b[3]))
        if not caixa: return None, None
        x0, y0 = min(caixa[0], T - 32), min(caixa[1], T - 32)               # sempre inclui o próprio tile (âncora embaixo à direita)
        return [q.crop((x0, y0, T, T)) for q in quadros], (T - x0, T - y0)

    def exportar(self, otbm, chave, nome, z, caixa=None, pedidos=None, semente=7, tiles=None, plano=None, pasta='', prefixo=None):
        if tiles is None: tiles = ler(otbm)['tiles']
        prefixo = prefixo or chave
        destino = os.path.join(RAIZ, 'mapas15', pasta); rel = 'tibia-assets/mapas15/' + (pasta + '/' if pasta else '')
        pts = [k for k in tiles if k[2] == z and (not caixa or (caixa[0] <= k[0] < caixa[2] and caixa[1] <= k[1] < caixa[3]))]
        X0 = min(k[0] for k in pts); Y0 = min(k[1] for k in pts)
        Wm = max(k[0] for k in pts) - X0 + 1; Hm = max(k[1] for k in pts) - Y0 + 1
        imagens, chaves_img = [], {}                                      # imagens únicas
        saida_tiles, walk = [], [0] * (Wm * Hm)

        def guardar(quadros, wh):
            h = hashlib.md5(str(wh).encode() + b''.join(q.tobytes() for q in quadros)).hexdigest()
            if h not in chaves_img:
                chaves_img[h] = f'{prefixo}:{len(imagens)}'
                imagens.append((chaves_img[h], quadros, wh))
            return chaves_img[h]

        for (x, y, _) in sorted(pts, key=lambda k: (k[1], k[0])):
            itens = []
            for sid in tiles[(x, y, z)]:
                _, t = self.coisa(sid)
                if t: itens.append(t)
            if not itens: continue
            chao = [t for t in itens if self.camada(t) == 0]
            resto = [t for c in (1, 2) for t in (itens if c == 1 else reversed(itens)) if self.camada(t) == c] + [t for t in itens if self.camada(t) == 3]
            ids = []
            if chao:
                q, wh = self.compor(chao, x, y, z, True); ids.append(guardar(q, wh))
            else: ids.append(None)
            if resto:
                q, wh = self.compor(resto, x, y, z, False)
                if q: ids.append(guardar(q, wh))
            lx, ly = x - X0, y - Y0
            if ids[0] is None and len(ids) == 1: continue
            saida_tiles.append([lx, ly, ids])
            anda = any('chao' in t['flags'] for t in chao) and not any('bloqueia' in t['flags'] or 'bloqueia_caminho' in t['flags'] for t in itens)   # 'bloqueia_caminho': o cliente não anda sozinho por ali (lava, campos)
            walk[ly * Wm + lx] = 1 if anda else 0

        # atlas: prateleiras de 2048 px de largura, cada imagem com seus quadros lado a lado
        os.makedirs(destino, exist_ok=True)
        imagens.sort(key=lambda a: -a[2][1])
        folhas, meta, atual, cx, cy, alt = [], {}, None, 0, 0, 0
        def nova():
            return Image.new('RGBA', (ATLAS_LARG, ATLAS_LARG))
        atual = nova()
        for k, quadros, (w, h) in imagens:
            larg = w * len(quadros)
            if cx + larg > ATLAS_LARG: cx, cy, alt = 0, cy + alt, 0
            if cy + h > ATLAS_LARG:
                folhas.append(atual); atual = nova(); cx = cy = alt = 0
            for i, q in enumerate(quadros): atual.paste(q, (cx + i * w, cy))
            meta[k] = {'f': len(folhas), 'x': cx, 'y': cy, 'w': w, 'h': h, 'n': len(quadros)}
            cx += larg; alt = max(alt, h)
        folhas.append(atual.crop((0, 0, ATLAS_LARG, cy + alt)))
        srcs = []
        for i, f in enumerate(folhas):
            arq = f'{chave}_{i}.png'; f.save(os.path.join(destino, arq), optimize=True)
            srcs.append(rel + arq)
        for m in meta.values(): m['src'] = srcs[m.pop('f')]

        spawns = []
        if plano:
            walk = maior_area(walk, Wm, Hm)
            viz = lambda x, y: sum(walk[(y + dy) * Wm + x + dx] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and 0 <= x + dx < Wm and 0 <= y + dy < Hm)
            cels = [(i % Wm, i // Wm) for i, v in enumerate(walk) if v]
            bons = [c for c in cels if viz(*c) >= 5] or cels
            ymax = max(c[1] for c in bons)
            ini = min((c for c in bons if c[1] >= ymax - 2), key=lambda p: (abs(p[0] - Wm // 2), -p[1]))     # entrada: beira de baixo, perto do meio
            pts = espalhar(walk, Wm, Hm, ini, plano.get('pts', 16))
            L = plano['lideres']
            spawns = [[x, y, L[i % len(L)], plano.get('tempo', 40)] for i, (x, y) in enumerate(pts)]
        elif pedidos:
            walk = maior_area(walk, Wm, Hm)
            cels = [(i % Wm, i // Wm) for i, v in enumerate(walk) if v]
            ini = max(cels, key=lambda p: (p[1], -abs(p[0] - Wm // 2)))          # entrada: beira de baixo
            rng = random.Random(semente); rng.shuffle(cels)
            for mob, n in pedidos:
                for (x, y) in cels:
                    if sum(1 for s in spawns if s[2] == mob) >= n: break
                    if max(abs(x - ini[0]), abs(y - ini[1])) < 10: continue
                    if any(max(abs(x - s[0]), abs(y - s[1])) < 6 for s in spawns): continue
                    spawns.append([x, y, mob, 60])
        else:   # início: tile andável mais perto do centro
            cxm, cym = Wm // 2, Hm // 2
            ini = min(((i % Wm, i // Wm) for i, v in enumerate(walk) if v), key=lambda p: (p[0] - cxm) ** 2 + (p[1] - cym) ** 2)
        mapa = {'nome': nome, 'w': Wm, 'h': Hm, 'origem': [X0, Y0, z], 'tiles': saida_tiles, 'walk': walk, 'spawns': spawns, 'inicio': list(ini), 'escuro': z > 7}
        with open(os.path.join(destino, chave + '.js'), 'w', encoding='utf-8') as fp:
            fp.write(f'/* gerado por ferramentas/exportar_mapa15.py a partir de {os.path.basename(otbm)} (sprites do cliente 15.01) */\n')
            fp.write('window.MAPAS=Object.assign(window.MAPAS||{},{' + json.dumps(chave) + ':' + json.dumps(mapa, separators=(',', ':')) + '});\n')
            fp.write('window.MAPAS_SPRITES=window.MAPAS_SPRITES||{tiles:{},criaturas:{}};Object.assign(window.MAPAS_SPRITES.tiles,' + json.dumps(meta, separators=(',', ':')) + ');\n')
        print(f'{chave}: {Wm}x{Hm} tiles, {len(saida_tiles)} com algo, {sum(walk)} andáveis, {len(imagens)} imagens únicas em {len(folhas)} atlas, início {ini}, {len(spawns)} spawns')
        return {'w': Wm, 'h': Hm, 'andaveis': int(sum(walk)), 'spawns': len(spawns), 'atlas': len(folhas), 'imagens': len(imagens), 'inicio': list(ini), 'origem': [X0, Y0, z]}


if __name__ == '__main__':
    args = sys.argv[1:]; opc = {}
    for k in ('--spawns', '--semente'):
        if k in args: i = args.index(k); opc[k] = args[i + 1]; del args[i:i + 2]
    otbm, chave, nome, z = args[0], args[1], args[2], int(args[3])
    caixa = tuple(int(v) for v in args[4:8]) if len(args) >= 8 else None
    pedidos = [(m, int(n)) for m, n in (p.split(':') for p in opc['--spawns'].split(','))] if '--spawns' in opc else None
    Exportador().exportar(otbm, chave, nome, z, caixa, pedidos, int(opc.get('--semente', 7)))
