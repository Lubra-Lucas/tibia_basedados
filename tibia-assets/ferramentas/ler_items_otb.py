#!/usr/bin/env python3
"""Lê o items.otb (TFS) e devolve {id do servidor: id do cliente}.

Mesmo formato de árvore do .otbm (0xFE abre, 0xFF fecha, 0xFD escapa). Cada item:
grupo u8, flags u32, depois atributos (tipo u8, tamanho u16, dados); 0x10 = id do servidor, 0x11 = id do cliente.
"""
import struct, sys
from ler_otbm import _arvore


def ler(caminho):
    b = open(caminho, 'rb').read()
    _, cab, filhos, _ = _arvore(b, 4)
    mapa = {}
    for _, d, _ in filhos:
        p = 4                                  # flags (o grupo é o tipo do nó)
        sid = cid = None
        while p + 3 <= len(d):
            a = d[p]; n, = struct.unpack_from('<H', d, p + 1); p += 3
            if a == 0x10: sid, = struct.unpack_from('<H', d, p)
            elif a == 0x11: cid, = struct.unpack_from('<H', d, p)
            p += n
        if sid is not None and cid: mapa[sid] = cid
    return mapa


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    m = ler(sys.argv[1])
    print(len(m), 'itens; exemplos', list(m.items())[:5], 'cliente máx', max(m.values()))
