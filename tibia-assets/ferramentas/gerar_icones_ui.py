#!/usr/bin/env python3
"""Ícones da interface (cabeçalho, menus e botões) tirados de itens do cliente 15.01.

Saída: sprites15/ui/<nome>.png (32x32). Itens empilháveis (moedas) usam a variação de pilha cheia.
"""
import os
from PIL import Image
from ler_dat_moderno import DatModerno
from gerar_sprites15 import Gerador

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
# nome do ícone → id do item no cliente
ICONES = {'cacadas': 5090, 'prey': 3349, 'bestiario': 3059, 'analisador': 2814, 'regras': 17722, 'config': 8775,
          'personagem': 3391, 'outfit': 3563, 'inventario': 2854, 'arena': 3265, 'loja': 21411, 'depot': 3502,
          'venda': 3040, 'imbuements': 3076, 'forja': 3458, 'blessings': 3077, 'gold': 3031, 'platinum': 3035,
          'crystal': 3043, 'loot': 2853, 'combo': 3281, 'cidade': 2979,
          'mercado': 9058, 'leilao': 3459, 'wiki': 8149}


def main():
    G = Gerador(); pasta = os.path.join(RAIZ, 'sprites15', 'ui'); os.makedirs(pasta, exist_ok=True)
    for nome, cid in ICONES.items():
        g = G.dat.itens[cid]['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
        im = Image.new('RGBA', (W, H))
        px, py = (g['px'] - 1, g['py'] - 1) if 'empilhavel' in G.dat.itens[cid]['flags'] else (0, 0)   # pilha cheia
        for yy in range(g['h']):
            for xx in range(g['w']):
                i = DatModerno.idx(g, xx, yy, 0, px, py, 0, 0)
                s = g['spr'][i] if i < len(g['spr']) else 0
                if s: im.alpha_composite(G.sprite(s), (W - (xx + 1) * 32, H - (yy + 1) * 32))
        caixa = im.getbbox()
        if caixa:
            im = im.crop(caixa); lado = max(im.width, im.height)
            q = Image.new('RGBA', (lado, lado)); q.alpha_composite(im, ((lado - im.width) // 2, (lado - im.height) // 2))
            im = q.resize((32, 32), Image.NEAREST) if lado > 32 else q.resize((lado, lado))
            fundo = Image.new('RGBA', (32, 32)); fundo.alpha_composite(im, ((32 - im.width) // 2, (32 - im.height) // 2)); im = fundo
        im.save(os.path.join(pasta, nome + '.png'))
    print(len(ICONES), 'ícones em', pasta)


if __name__ == '__main__':
    main()
