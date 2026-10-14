#!/usr/bin/env python3
"""Lê o Tibia.dat 7.4 (definição de cada item/criatura/efeito/projétil e quais sprites do .spr ele usa).

Cabeçalho: assinatura u32, último id de item u16 (itens começam no 100), criaturas u16, efeitos u16, projéteis u16.
Cada coisa: flags terminadas em 0xFF, depois largura, altura, [tamanho exato], camadas, padrãoX, padrãoY,
fases de animação e os ids dos sprites (u16). No 7.4 não existe padrãoZ e as flags têm numeração própria
(mapeamento do OTClient para versões 7.40–7.50).
"""
import struct, sys

# flag bruta do 7.4 → (nome, bytes de dados)
FLAGS = {0: ('chao', 2), 1: ('embaixo', 0), 2: ('em_cima', 0), 3: ('recipiente', 0), 4: ('empilhavel', 0), 5: ('uso_forcado', 0),
         6: ('multiuso', 0), 7: ('escrevivel', 2), 8: ('escrevivel_1x', 2), 9: ('recipiente_liquido', 0), 10: ('poca', 0),
         11: ('bloqueia', 0), 12: ('fixo', 0), 13: ('bloqueia_projetil', 0), 14: ('bloqueia_caminho', 0), 15: ('pegavel', 0),
         16: ('luz', 4), 17: ('muda_andar', 0), 18: ('chao_cheio', 0), 19: ('elevacao', 2), 20: ('deslocamento', 0),
         21: ('?21', 0), 22: ('cor_minimapa', 2), 23: ('giravel', 0), 24: ('cadaver', 0), 25: ('anima_sempre', 0), 26: ('?26', 0),
         27: ('?27', 0), 28: ('?28', 0), 29: ('ajuda', 2)}   # neste .dat a 'lens help' é a 29 (com 2 bytes)


class Dat:
    def __init__(self, caminho):
        b = open(caminho, 'rb').read()
        self.assinatura, self.ult_item, self.n_cria, self.n_efe, self.n_proj = struct.unpack_from('<IHHHH', b, 0)
        p = 12
        self.itens, self.criaturas, self.efeitos, self.projeteis = {}, {}, {}, {}
        alvo = [(self.itens, range(100, self.ult_item + 1)), (self.criaturas, range(1, self.n_cria + 1)),
                (self.efeitos, range(1, self.n_efe + 1)), (self.projeteis, range(1, self.n_proj + 1))]
        for dic, ids in alvo:
            for i in ids:
                if p >= len(b): break                     # este .dat tem menos projéteis do que o cabeçalho diz
                fl = {}
                while True:
                    f = b[p]; p += 1
                    if f == 0xFF: break
                    nome, tam = FLAGS.get(f, (f'?{f}', 0))
                    fl[nome] = struct.unpack_from('<H', b, p)[0] if tam == 2 else (struct.unpack_from('<HH', b, p) if tam == 4 else True)
                    p += tam
                w, h = b[p], b[p + 1]; p += 2
                if w > 1 or h > 1: p += 1                 # tamanho exato
                layers, px, py, fases = b[p], b[p + 1], b[p + 2], b[p + 3]; p += 4
                n = w * h * layers * px * py * fases
                spr = list(struct.unpack_from(f'<{n}H', b, p)); p += 2 * n
                dic[i] = {'flags': fl, 'w': w, 'h': h, 'layers': layers, 'px': px, 'py': py, 'fases': fases, 'spr': spr}
        self.lido, self.total = p, len(b)

    def sprite_idx(self, t, x=0, y=0, layer=0, px=0, py=0, fase=0):
        """Índice no vetor de sprites (ordem do OTClient: fase, padrãoY, padrãoX, camada, altura, largura)."""
        return ((((fase * t['py'] + py) * t['px'] + px) * t['layers'] + layer) * t['h'] + y) * t['w'] + x


def montar(spr, t, px=0, py=0, fase=0, layers=(0,)):
    """Monta a imagem completa de uma coisa (itens grandes usam vários sprites 32x32, crescendo para cima/esquerda)."""
    from PIL import Image
    W, H = t['w'] * 32, t['h'] * 32
    im = Image.new('RGBA', (W, H))
    for layer in layers:
        if layer >= t['layers']: continue
        for y in range(t['h']):
            for x in range(t['w']):
                i = Dat.sprite_idx(None, t, x, y, layer, px % t['px'], py % t['py'], fase % t['fases'])
                if i < len(t['spr']) and t['spr'][i]:
                    im.alpha_composite(spr.sprite(t['spr'][i]), (W - (x + 1) * 32, H - (y + 1) * 32))
    return im


if __name__ == '__main__':
    d = Dat(sys.argv[1])
    print(hex(d.assinatura), 'itens', len(d.itens), 'criaturas', len(d.criaturas), 'efeitos', len(d.efeitos), 'projéteis', len(d.projeteis))
    print('lido', d.lido, 'de', d.total, 'bytes', 'OK' if d.lido == d.total else 'DIFERENTE!')
