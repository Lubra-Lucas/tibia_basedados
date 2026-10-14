#!/usr/bin/env python3
"""Procura salas que sirvam de arena nos .otbm de uma pasta.

Arena boa = região andável conectada, quase retangular (preenche 85%+ da caixa), de 10 a 22 tiles
de lado, com poucos objetos dentro e cercada (a borda da caixa não vaza para fora).
Uso: python achar_arenas.py PASTA [max_kb]
"""
import glob, os, sys
sys.setrecursionlimit(20000)
from ler_otbm import ler
from renderizar_otbm import Pintor

P = Pintor()


def flags(sid):
    _, t = P.coisa(sid)
    return t['flags'] if t else {}


def analisar(caminho):
    tiles = ler(caminho)['tiles']
    achados = []
    for z in sorted({k[2] for k in tiles}):
        anda, obj = {}, {}
        for (x, y, zz), its in tiles.items():
            if zz != z or not its: continue
            fs = [flags(i) for i in its]
            anda[(x, y)] = any('chao' in f for f in fs[:1]) and not any('bloqueia' in f or 'bloqueia_caminho' in f for f in fs)
            obj[(x, y)] = sum(1 for f in fs[1:] if not ('borda_chao' in f or 'chao' in f))
        vistos = set()
        for c, v in anda.items():
            if not v or c in vistos: continue
            fila, reg = [c], []
            vistos.add(c)
            while fila:
                x, y = fila.pop(); reg.append((x, y))
                if len(reg) > 600: break
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + d[0], y + d[1])
                    if anda.get(n) and n not in vistos: vistos.add(n); fila.append(n)
            if len(reg) > 600 or fila: continue
            xs = [p[0] for p in reg]; ys = [p[1] for p in reg]
            w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if not (10 <= w <= 22 and 9 <= h <= 18): continue
            preench = len(reg) / (w * h)
            limpo = sum(1 for p in reg if obj.get(p, 0) == 0) / len(reg)
            if preench >= .85 and limpo >= .8:
                achados.append({'z': z, 'x0': min(xs), 'y0': min(ys), 'w': w, 'h': h, 'preench': round(preench, 2), 'limpo': round(limpo, 2), 'tiles': len(reg)})
    return achados


if __name__ == '__main__':
    pasta = sys.argv[1]; maxkb = int(sys.argv[2]) if len(sys.argv) > 2 else 9000
    for f in sorted(glob.glob(os.path.join(pasta, '*.otbm')), key=os.path.getsize):
        if os.path.getsize(f) / 1024 > maxkb: continue
        try: a = analisar(f)
        except Exception as e: print('erro', f, e); continue
        for r in sorted(a, key=lambda r: -r['preench'] * r['limpo'])[:3]:
            print(os.path.basename(f), r, flush=True)
