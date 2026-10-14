#!/usr/bin/env python3
"""Desenha um .otbm (TFS 10.98, ids do servidor) com os sprites do cliente moderno (.dat/.spr 15.x).

Uso: python renderizar_otbm.py mapa.otbm saida.png [z_baixo] [z_alto] [x0 y0 x1 y1]
  - z_baixo/z_alto: andares desenhados (o de cima é deslocado 32px para cima/esquerda por andar, como no Tibia)
  - o recorte usa coordenadas absolutas do mapa
Ordem dentro do tile (como no cliente): chão e bordas → 'embaixo' (paredes) → itens comuns → 'em cima'.
Elevação empurra os itens seguintes para cima/esquerda; deslocamento move o próprio sprite.
"""
import os, sys
from PIL import Image
sys.setrecursionlimit(20000)
from ler_otbm import ler
from ler_items_otb import ler as ler_otb
from ler_dat_moderno import DatModerno, SprModerno

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMP = os.path.expandvars(r'%LOCALAPPDATA%\Temp')
DAT = os.environ.get('TIBIA_DAT', os.path.join(TEMP, 'Tibia (1).dat'))
SPR = os.environ.get('TIBIA_SPR', os.path.join(TEMP, 'Tibia.spr'))
OTB = os.path.join(AQUI, '..', 'dados', '_items_tfs1098.otb')


class Pintor:
    def __init__(self):
        self.dat, self.spr, self.s2c = DatModerno(DAT), SprModerno(SPR), ler_otb(OTB)
        self.cache = {}

    def sprite(self, sid):
        im = self.cache.get(sid)
        if im is None: im = self.cache[sid] = self.spr.sprite(sid)
        return im

    def coisa(self, sid_servidor):
        cid = self.s2c.get(sid_servidor, sid_servidor)        # fora do otb: assume que já é id do cliente
        return cid, self.dat.itens.get(cid)

    def camada(self, t):
        f = t['flags']
        if 'chao' in f or 'borda_chao' in f: return 0
        if 'embaixo' in f: return 1
        if 'em_cima' in f: return 3
        return 2

    def desenhar_item(self, tela, t, X, Y, x, y, z, elev):
        g = t['grupos'][0]; f = t['flags']
        dx, dy = f.get('deslocamento', (0, 0)) if isinstance(f.get('deslocamento'), tuple) else (0, 0)
        px, py, pz = x % g['px'], y % g['py'], z % g['pz']
        for layer in range(g['layers']):
            for yy in range(g['h']):
                for xx in range(g['w']):
                    i = DatModerno.idx(g, xx, yy, layer, px, py, pz, 0)
                    s = g['spr'][i] if i < len(g['spr']) else 0
                    if s: tela.alpha_composite(self.sprite(s), (X - xx * 32 - dx - elev, Y - yy * 32 - dy - elev))
            if layer == 0 and g['layers'] > 1 and 'cadaver_deitado' not in f: break   # camadas extras são máscara/variação
        return f.get('elevacao', 0) or 0

    def render(self, otbm, z_baixo, z_alto, caixa=None):
        tiles = ler(otbm)['tiles']
        if caixa is None:
            xs = [k[0] for k in tiles]; ys = [k[1] for k in tiles]
            caixa = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        x0, y0, x1, y1 = caixa
        M = 2                                                   # margem para sprites grandes
        tela = Image.new('RGBA', ((x1 - x0 + M) * 32, (y1 - y0 + M) * 32), (0, 0, 0, 255))
        sem = set()
        for z in range(z_baixo, z_alto - 1, -1):
            off = (z_baixo - z) * 32
            por_tile = sorted((k for k in tiles if k[2] == z and x0 <= k[0] - (z_baixo - z) < x1 + M and y0 <= k[1] - (z_baixo - z) < y1 + M),
                              key=lambda k: (k[1], k[0]))
            for (x, y, _) in por_tile:
                X = (x - x0 + M - 1) * 32 - off; Y = (y - y0 + M - 1) * 32 - off
                itens = []
                for sid in tiles[(x, y, z)]:
                    cid, t = self.coisa(sid)
                    if not t: sem.add(sid); continue
                    itens.append(t)
                ordem = [t for c in (0, 1, 2) for t in (itens if c != 2 else reversed(itens)) if self.camada(t) == c] + [t for t in itens if self.camada(t) == 3]
                elev = 0
                for t in ordem:
                    elev += self.desenhar_item(tela, t, X, Y, x, y, z, elev)
        return tela.crop((32, 32, tela.width - 32, tela.height - 32)), sem


if __name__ == '__main__':
    otbm, saida = sys.argv[1], sys.argv[2]
    zb = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    za = int(sys.argv[4]) if len(sys.argv) > 4 else zb
    caixa = tuple(int(v) for v in sys.argv[5:9]) if len(sys.argv) > 8 else None
    im, sem = Pintor().render(otbm, zb, za, caixa)
    im.save(saida)
    print(saida, im.size, 'itens sem sprite:', sorted(sem)[:20], len(sem))
