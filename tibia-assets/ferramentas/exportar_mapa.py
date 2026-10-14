#!/usr/bin/env python3
"""Exporta um mapa .otbm para o visualizador (tibia-assets/visualizador/<nome>.js).

Uso: python exportar_mapa.py CAMINHO\\mapa.otbm nome
Depois abra visualizador/index.html?mapa=nome
"""
import json, os, sys, xml.etree.ElementTree as ET
from collections import Counter
sys.setrecursionlimit(10000)
from ler_otbm import ler

AQUI = os.path.dirname(os.path.abspath(__file__))


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    otbm, nome_mapa = sys.argv[1], sys.argv[2]
    m = ler(otbm)
    nome = {}
    for it in ET.parse(sys.argv[3] if len(sys.argv) > 3 else os.path.join(AQUI, '..', 'dados', '_items.xml')).getroot().iter('item'):
        n = it.get('name') or ''
        ids = [int(it.get('id'))] if it.get('id') else range(int(it.get('fromid', 0)), int(it.get('toid', -1)) + 1)
        for i in ids: nome[i] = n
    t = m['tiles']
    xs = [k[0] for k in t]; ys = [k[1] for k in t]
    x0, y0 = min(xs), min(ys)
    pasta = os.path.dirname(otbm); base = os.path.splitext(os.path.basename(otbm))[0]
    npcs = []
    p = os.path.join(pasta, base + '-npc.xml')
    if os.path.exists(p):
        for g in ET.parse(p).getroot():
            for n in g: npcs.append([n.get('name'), int(g.get('centerx')) + int(n.get('x', 0)) - x0, int(g.get('centery')) + int(n.get('y', 0)) - y0, int(g.get('centerz'))])
    andar_npc = Counter(z for *_, z in npcs).most_common(1)
    centro = [sum(n[1] for n in npcs) // len(npcs), sum(n[2] for n in npcs) // len(npcs)] if npcs else [(max(xs) - x0) // 2, (max(ys) - y0) // 2]
    dados = {'nome': nome_mapa, 'x0': x0, 'y0': y0, 'w': max(xs) - x0 + 1, 'h': max(ys) - y0 + 1,
             'andares': sorted({z for _, _, z in t}), 'andar_cidade': andar_npc[0][0] if andar_npc else 7, 'centro': centro, 'npcs': npcs,
             'tiles': [[x - x0, y - y0, z, [[i, nome.get(i, '')] for i in v]] for (x, y, z), v in t.items()]}
    destino = os.path.join(AQUI, '..', 'visualizador', nome_mapa + '.js')
    with open(destino, 'w', encoding='utf-8') as f:
        f.write('window.MAPA=' + json.dumps(dados, ensure_ascii=False, separators=(',', ':')) + ';')
    print(f'{len(t)} tiles, andares {dados["andares"]}, cidade no andar {dados["andar_cidade"]}, {len(npcs)} NPCs → {os.path.abspath(destino)}')


if __name__ == '__main__':
    main()
