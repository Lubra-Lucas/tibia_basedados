#!/usr/bin/env python3
"""Raio-x de uma pasta de mapas .otbm: versão, descrição, tamanho, andares e cobertura de tradução de ids.

Lê os nós sem montar a árvore inteira (os mapas grandes passam de 70 MB).
Uso: python inventario_mapas.py PASTA [saida.json]
"""
import glob, json, os, re, struct, sys
from collections import Counter
from ler_items_otb import ler as ler_otb

AQUI = os.path.dirname(os.path.abspath(__file__))
S2C = ler_otb(os.path.join(AQUI, '..', 'dados', '_items_tfs1098.otb'))
NS, NE, ESC = 0xFE, 0xFF, 0xFD
ESPECIAL = re.compile(rb'[\xfd-\xff]')


def nos(b):
    """Percorre os nós em ordem, devolvendo (profundidade, tipo, dados) de cada um (dados sem escape, sem filhos)."""
    pilha = []                      # (tipo, bytearray)
    i, n = 4, len(b)
    while i < n:
        c = b[i]
        if c == NS:
            pilha.append((b[i + 1], bytearray())); i += 2
        elif c == NE:
            t, d = pilha.pop(); yield len(pilha), t, d; i += 1
        elif c == ESC:
            pilha[-1][1].append(b[i + 1]); i += 2
        else:
            # copia o trecho até o próximo byte especial de uma vez
            m = ESPECIAL.search(b, i); j = m.start() if m else n
            pilha[-1][1].extend(b[i:j]); i = j


def textos_mapdata(d):
    out, p = {}, 0
    while p < len(d):
        a = d[p]; p += 1
        if a in (1, 11, 13):       # descrição, arquivo de spawn, arquivo de casas
            n, = struct.unpack_from('<H', d, p); p += 2
            out.setdefault({1: 'descricao', 11: 'spawn', 13: 'casas'}[a], []).append(d[p:p + n].decode('latin-1', 'replace')); p += n
        else: break
    return out


def analisar(caminho):
    b = open(caminho, 'rb').read()
    # cabeçalho da raiz (logo depois do identificador e do 0xFE tipo)
    cab = bytearray(); i = 6
    while len(cab) < 16:
        if b[i] == ESC: cab.append(b[i + 1]); i += 2
        else: cab.append(b[i]); i += 1
    ver, w, h, imaj, imin = struct.unpack_from('<IHHII', bytes(cab))
    zs, ids, info = Counter(), Counter(), {}
    area = None
    xs = [1 << 30, -1]; ys = [1 << 30, -1]
    cidades, npcs = [], 0
    for prof, t, d in nos(b):
        if t == 2: info = textos_mapdata(bytes(d))
        elif t == 4:                                   # TILE_AREA (os tiles filhos já passaram)
            pass
        elif t in (5, 14):                              # TILE / HOUSETILE
            p = 2 + (4 if t == 14 else 0)
            while p < len(d):
                a = d[p]; p += 1
                if a == 3: p += 4
                elif a == 9: ids[struct.unpack_from('<H', d, p)[0]] += 1; p += 2
                else: break
        elif t == 6:                                    # ITEM
            ids[struct.unpack_from('<H', d, 0)[0]] += 1
        elif t == 13:                                   # TOWN: id u32, nome, templo
            tid, n = struct.unpack_from('<IH', d, 0); cidades.append(bytes(d[6:6 + n]).decode('latin-1', 'replace'))
    # andares/extensão: segunda passada só nos TILE_AREA (barata)
    for prof, t, d in nos(b):
        if t == 4:
            x, y, z = struct.unpack_from('<HHB', d, 0); zs[z] += 1
            xs = [min(xs[0], x), max(xs[1], x + 255)]; ys = [min(ys[0], y), max(ys[1], y + 255)]
    tot = sum(ids.values()) or 1
    cobre = sum(c for i, c in ids.items() if i in S2C) / tot
    return {'arquivo': os.path.basename(caminho), 'kb': round(len(b) / 1024), 'otbm': ver, 'otb': f'{imaj}.{imin}',
            'itens': tot, 'tipos': len(ids), 'id_max': max(ids) if ids else 0, 'cobertura_1098': round(cobre * 100, 1),
            'andares': sorted(zs), 'areas_256': sum(zs.values()), 'cidades': cidades,
            'descricao': ' | '.join(info.get('descricao', []))[:160], 'spawn': (info.get('spawn') or [''])[0], 'casas': (info.get('casas') or [''])[0]}


if __name__ == '__main__':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    pasta = sys.argv[1]; saida = sys.argv[2] if len(sys.argv) > 2 else None
    res = []
    for f in sorted(glob.glob(os.path.join(pasta, '**', '*.otbm'), recursive=True), key=os.path.getsize):
        try: r = analisar(f)
        except Exception as e: r = {'arquivo': os.path.basename(f), 'erro': str(e)[:120]}
        res.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
    if saida: json.dump(res, open(saida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
