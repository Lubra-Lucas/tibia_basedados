#!/usr/bin/env python3
"""Lê um Tibia.spr antigo (7.x): assinatura u32, quantidade u16, endereços u32 e
cada sprite 32x32 em RLE: cor-chave (3 bytes), tamanho u16, depois blocos
(transparentes u16, coloridos u16, RGB * coloridos)."""
import struct, sys
from PIL import Image


class Spr:
    def __init__(self, caminho):
        self.b = open(caminho, 'rb').read()
        self.assinatura, self.qtd = struct.unpack_from('<IH', self.b, 0)
        self.end = struct.unpack_from(f'<{self.qtd}I', self.b, 6)

    def sprite(self, sid):
        """sid começa em 1 (como no Tibia). Devolve Image RGBA 32x32 (vazia se não existir)."""
        im = Image.new('RGBA', (32, 32))
        if sid < 1 or sid > self.qtd: return im
        p = self.end[sid - 1]
        if p == 0: return im
        p += 3                                        # cor-chave
        tam, = struct.unpack_from('<H', self.b, p); p += 2
        fim = p + tam; pos = 0
        px = im.load()
        while p < fim and pos < 1024:
            transp, cor = struct.unpack_from('<HH', self.b, p); p += 4
            pos += transp
            for _ in range(cor):
                r, g, bb = self.b[p], self.b[p + 1], self.b[p + 2]; p += 3
                px[pos % 32, pos // 32] = (r, g, bb, 255); pos += 1
        return im


if __name__ == '__main__':
    s = Spr(sys.argv[1])
    print(hex(s.assinatura), s.qtd, 'sprites')
