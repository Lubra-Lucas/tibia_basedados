#!/usr/bin/env python3
"""Lê .dat/.spr modernos (10.x até 15.x no formato do OTClient: sprites estendidos u32,
grupos de quadros nas criaturas e animação melhorada).

Flags brutas (versão >= 10.00; a 16 é 'sem animação de mover' e da 17 em diante soma 1 em relação ao 7.x):
"""
import struct, sys

# flag bruta → (nome, formato dos dados)
FLAGS = {0: ('chao', 'H'), 1: ('borda_chao', ''), 2: ('embaixo', ''), 3: ('em_cima', ''), 4: ('recipiente', ''), 5: ('empilhavel', ''),
         6: ('uso_forcado', ''), 7: ('multiuso', ''), 8: ('escrevivel', 'H'), 9: ('escrevivel_1x', 'H'), 10: ('recipiente_liquido', ''),
         11: ('poca', ''), 12: ('bloqueia', ''), 13: ('fixo', ''), 14: ('bloqueia_projetil', ''), 15: ('bloqueia_caminho', ''),
         16: ('sem_anim_mover', ''), 17: ('pegavel', ''), 18: ('pendurável', ''), 19: ('gancho_sul', ''), 20: ('gancho_leste', ''),
         21: ('giravel', ''), 22: ('luz', 'HH'), 23: ('nao_esconde', ''), 24: ('translucido', ''), 25: ('deslocamento', 'HH'),
         26: ('elevacao', 'H'), 27: ('cadaver_deitado', ''), 28: ('anima_sempre', ''), 29: ('cor_minimapa', 'H'), 30: ('ajuda', 'H'),
         31: ('chao_cheio', ''), 32: ('olhar', ''), 33: ('roupa', 'H'), 34: ('mercado', 'MKT'), 35: ('acao_padrao', 'H'),
         36: ('embrulhavel', ''), 37: ('desembrulhavel', ''), 38: ('efeito_topo', ''), 39: ('?39', ''), 40: ('?40', ''),
         252: ('?252', ''), 253: ('?253', ''), 254: ('usavel', ''), 255: None}


class DatModerno:
    def __init__(self, caminho, desconhecidas=None):
        b = self.b = open(caminho, 'rb').read()
        self.assinatura, self.ult_item, self.n_cria, self.n_efe, self.n_proj = struct.unpack_from('<IHHHH', b, 0)
        self.p = 12
        self.itens, self.criaturas, self.efeitos, self.projeteis = {}, {}, {}, {}
        self.flags_vistas = {}
        for dic, ids, cat in [(self.itens, range(100, self.ult_item + 1), 'item'), (self.criaturas, range(1, self.n_cria + 1), 'criatura'),
                              (self.efeitos, range(1, self.n_efe + 1), 'efeito'), (self.projeteis, range(1, self.n_proj + 1), 'projetil')]:
            for i in ids:
                ini = self.p
                try:
                    dic[i] = self._coisa(cat)
                except Exception as e:
                    raise RuntimeError(f'{cat} {i} no byte {ini}: {e}')
        self.lido, self.total = self.p, len(b)

    def _u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def _coisa(self, cat):
        b = self.b; fl = {}
        while True:
            f = self._u8()
            if f == 0xFF: break
            if f not in FLAGS or FLAGS[f] is None: raise ValueError(f'flag desconhecida {f}')
            nome, fmt = FLAGS[f]
            self.flags_vistas[nome] = self.flags_vistas.get(nome, 0) + 1
            if fmt == 'MKT':
                cat_, troca, mostra, n = struct.unpack_from('<HHHH', b, self.p); self.p += 8
                txt = b[self.p:self.p + n].decode('latin-1'); self.p += n
                prof, nivel = struct.unpack_from('<HH', b, self.p); self.p += 4
                fl[nome] = {'cat': cat_, 'nome': txt, 'nivel': nivel}
            elif fmt:
                v = struct.unpack_from('<' + fmt, b, self.p); self.p += struct.calcsize(fmt)
                fl[nome] = v[0] if len(v) == 1 else v
            else:
                fl[nome] = True
        grupos = []
        ng = self._u8() if cat == 'criatura' else 1
        for _ in range(ng):
            tipo = self._u8() if cat == 'criatura' else 0
            w, h = self._u8(), self._u8()
            if w > 1 or h > 1: self._u8()
            layers, px, py, pz, fases = (self._u8() for _ in range(5))
            anim = None
            if fases > 1:
                assinc, loop, ini = struct.unpack_from('<BiB', b, self.p); self.p += 6
                dur = struct.unpack_from(f'<{2 * fases}I', b, self.p); self.p += 8 * fases
                anim = {'assinc': assinc, 'loop': loop, 'ini': ini, 'ms': [(dur[2 * k] + dur[2 * k + 1]) // 2 for k in range(fases)]}
            n = w * h * layers * px * py * pz * fases
            spr = list(struct.unpack_from(f'<{n}I', b, self.p)); self.p += 4 * n
            grupos.append({'tipo': tipo, 'w': w, 'h': h, 'layers': layers, 'px': px, 'py': py, 'pz': pz, 'fases': fases, 'anim': anim, 'spr': spr})
        return {'flags': fl, 'grupos': grupos}

    @staticmethod
    def idx(g, x=0, y=0, layer=0, px=0, py=0, pz=0, fase=0):
        """Ordem do OTClient: fase, padrãoZ, padrãoY, padrãoX, camada, altura, largura."""
        return ((((((fase * g['pz'] + pz) * g['py'] + py) * g['px'] + px) * g['layers'] + layer) * g['h'] + y) * g['w'] + x)


class SprModerno:
    """Sprites 32x32 em RLE. Com transparência, cada pixel colorido tem 4 bytes (RGBA); sem, 3 (RGB)."""
    def __init__(self, caminho):
        self.f = open(caminho, 'rb')
        cab = self.f.read(8)
        self.assinatura, self.qtd = struct.unpack('<II', cab)
        self.end = struct.unpack(f'<{self.qtd}I', self.f.read(4 * self.qtd))
        self.alfa = self._detecta_alfa()

    def _bruto(self, sid):
        p = self.end[sid - 1]
        if not p: return None
        self.f.seek(p + 3)
        tam, = struct.unpack('<H', self.f.read(2))
        return self.f.read(tam)

    def _detecta_alfa(self):
        """Testa os dois formatos nos primeiros sprites: o certo fecha exatamente no tamanho do bloco."""
        for bpp in (4, 3):
            ok = 0
            for sid in range(1, min(self.qtd, 400)):
                d = self._bruto(sid)
                if not d: continue
                p = pos = 0
                while p + 4 <= len(d) and pos < 1024:
                    t, c = struct.unpack_from('<HH', d, p); p += 4 + c * bpp; pos += t + c
                ok += (p == len(d) and pos <= 1024)
            if ok > 300 * 0.8: return bpp == 4
        return True

    def sprite(self, sid):
        from PIL import Image
        im = Image.new('RGBA', (32, 32))
        if sid < 1 or sid > self.qtd: return im
        d = self._bruto(sid)
        if not d: return im
        px = im.load(); p = pos = 0; bpp = 4 if self.alfa else 3
        while p + 4 <= len(d) and pos < 1024:
            t, c = struct.unpack_from('<HH', d, p); p += 4; pos += t
            for _ in range(c):
                if pos >= 1024: break
                r, g, bb = d[p], d[p + 1], d[p + 2]; a = d[p + 3] if bpp == 4 else 255
                px[pos % 32, pos // 32] = (r, g, bb, a); p += bpp; pos += 1
        return im


def montar(spr, g, px=0, py=0, pz=0, fase=0, layers=(0,)):
    """Imagem completa de uma coisa (cresce para cima e para a esquerda a partir do canto inferior direito)."""
    from PIL import Image
    W, H = g['w'] * 32, g['h'] * 32
    im = Image.new('RGBA', (W, H))
    for layer in layers:
        if layer >= g['layers']: continue
        for y in range(g['h']):
            for x in range(g['w']):
                i = DatModerno.idx(g, x, y, layer, px % g['px'], py % g['py'], pz % g['pz'], fase % g['fases'])
                if i < len(g['spr']) and g['spr'][i]:
                    im.alpha_composite(spr.sprite(g['spr'][i]), (W - (x + 1) * 32, H - (y + 1) * 32))
    return im


if __name__ == '__main__':
    d = DatModerno(sys.argv[1])
    print(hex(d.assinatura), 'itens', len(d.itens), 'criaturas', len(d.criaturas), 'efeitos', len(d.efeitos), 'projéteis', len(d.projeteis))
    print('lido', d.lido, 'de', d.total, 'OK' if d.lido == d.total else 'DIFERENTE!')
    print(sorted(d.flags_vistas.items(), key=lambda a: -a[1]))
