#!/usr/bin/env python3
"""Lê um mapa .otbm (formato de mapa de servidor do Tibia) e devolve os tiles com os IDs dos itens.

Formato: árvore de nós (0xFE abre, 0xFF fecha, 0xFD escapa o próximo byte).
  raiz → MAP_DATA → TILE_AREA(x,y,z) → TILE / HOUSETILE (dx,dy) → ITEM(id)
"""
import struct, sys

NODE_START, NODE_END, ESC = 0xFE, 0xFF, 0xFD
TILE_AREA, TILE, ITEM, HOUSETILE = 4, 5, 6, 14
ATTR_TILE_FLAGS, ATTR_ITEM = 3, 9


def _arvore(b, i):
    """Lê um nó a partir de b[i] == NODE_START. Devolve (tipo, dados_sem_escape, filhos, próximo_i)."""
    assert b[i] == NODE_START
    i += 1
    tipo = b[i]; i += 1
    dados = bytearray(); filhos = []
    while True:
        c = b[i]
        if c == ESC:
            dados.append(b[i + 1]); i += 2
        elif c == NODE_START:
            f = _arvore(b, i); filhos.append(f[:3]); i = f[3]
        elif c == NODE_END:
            return tipo, bytes(dados), filhos, i + 1
        else:
            dados.append(c); i += 1


def ler(caminho):
    b = open(caminho, 'rb').read()
    tipo, cab, filhos, _ = _arvore(b, 4)
    versao, largura, altura, imaj, imin = struct.unpack_from('<IHHII', cab)
    tiles = {}
    for t, d, fs in filhos:
        if t != 2: continue                      # MAP_DATA
        for at, ad, afs in fs:
            if at != TILE_AREA: continue
            bx, by, bz = struct.unpack_from('<HHB', ad)
            for tt, td, tfs in afs:
                if tt not in (TILE, HOUSETILE): continue
                dx, dy = td[0], td[1]
                p = 2 + (4 if tt == HOUSETILE else 0)
                itens = []
                while p < len(td):               # atributos do tile
                    a = td[p]; p += 1
                    if a == ATTR_TILE_FLAGS: p += 4
                    elif a == ATTR_ITEM: itens.append(struct.unpack_from('<H', td, p)[0]); p += 2
                    else: break
                for it, idd, _ in tfs:
                    if it == ITEM: itens.append(struct.unpack_from('<H', idd)[0])
                tiles[(bx + dx, by + dy, bz)] = itens
    return {'versao': versao, 'largura': largura, 'altura': altura, 'itens_versao': (imaj, imin), 'tiles': tiles}


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    m = ler(sys.argv[1])
    t = m['tiles']
    print('versão', m['versao'], 'tamanho', m['largura'], 'x', m['altura'], 'tiles', len(t))
    zs = sorted({z for _, _, z in t})
    for z in zs:
        xs = [x for x, y, zz in t if zz == z]; ys = [y for x, y, zz in t if zz == z]
        print(f'andar {z}: {len(xs)} tiles, x {min(xs)}-{max(xs)}, y {min(ys)}-{max(ys)}')
