#!/usr/bin/env python3
"""Biblioteca de outfits do 15.01 para colorir no jogo (adversários da arena).

Cada outfit vira uma folha com 6 blocos empilhados (cada bloco = 4 linhas de direção do .dat, N/L/S/O):
  addon 0 base, addon 0 máscara, addon 1 base, addon 1 máscara, addon 2 base, addon 2 máscara.
Colunas = quadros parados (grupo 0) + quadros de andar (grupo 1). O jogo pinta a máscara com as
cores escolhidas (paleta de 133 cores), como faz o cliente.

Saída: sprites15/outfits/<lookType>.png e outfits15.js (window.OUTFITS15).
"""
import json, os, sys, xml.etree.ElementTree as ET
from PIL import Image
from gerar_sprites15 import Gerador

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
MAX_POR_SEXO = 45


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    G = Gerador(); dat = G.dat
    pasta = os.path.join(RAIZ, 'sprites15', 'outfits'); os.makedirs(pasta, exist_ok=True)
    xml = ET.parse(os.path.join(RAIZ, 'dados', 'outfits_canary.xml')).getroot()
    lista = {'0': [], '1': []}
    for o in xml.iter('outfit'):
        sexo, look, nome = o.get('type'), int(o.get('looktype')), o.get('name')
        if sexo not in lista or len(lista[sexo]) >= MAX_POR_SEXO or o.get('enabled') == 'no': continue
        t = dat.criaturas.get(look)
        if not t or len(t['grupos']) < 2 or t['grupos'][0]['layers'] < 2: continue
        lista[sexo].append((look, nome))
    meta = {}
    for sexo, itens in lista.items():
        for look, nome in itens:
            t = dat.criaturas[look]; gs = t['grupos']
            W = max(g['w'] for g in gs) * 32; H = max(g['h'] for g in gs) * 32
            cols = [(gs[0], f) for f in range(gs[0]['fases'])] + [(gs[1], f) for f in range(gs[1]['fases'])]
            folha = Image.new('RGBA', (W * len(cols), H * 4 * 6))
            for py in range(3):
                for camada in range(2):
                    bloco = py * 2 + camada
                    for d in range(4):
                        for c, (g, f) in enumerate(cols):
                            if py >= g['py']: continue
                            folha.paste(G.quadro(g, d, py, f, camada, W, H), (c * W, (bloco * 4 + d) * H))
            folha.save(os.path.join(pasta, f'{look}.png'), optimize=True)
            desl = t['flags'].get('deslocamento') or (0, 0)
            meta[look] = {'nome': nome, 'sexo': 'f' if sexo == '0' else 'm', 'src': f'tibia-assets/sprites15/outfits/{look}.png', 'w': W, 'h': H,
                          'parado': gs[0]['fases'], 'andar': gs[1]['fases'], 'ms': gs[0]['anim']['ms'] if gs[0]['anim'] else [300],
                          'desl': list(desl) if isinstance(desl, tuple) else [8, 8], 'addons': gs[0]['py'] > 1}
    with open(os.path.join(RAIZ, 'outfits15.js'), 'w', encoding='utf-8') as fp:
        fp.write('/* gerado por ferramentas/gerar_outfits15.py (outfits do cliente 15.01 com máscara de cores) */\nwindow.OUTFITS15=' + json.dumps(meta, separators=(',', ':'), ensure_ascii=False) + ';\n')
    print(len(meta), 'outfits:', ', '.join(f"{v['nome']}({v['sexo']})" for v in meta.values()))


if __name__ == '__main__':
    main()
