#!/usr/bin/env python3
"""Catálogo de todos os monstros do Canary que têm sprite no cliente 15.01.

Lê dados/catalogo_monstros.json (montado cruzando monstros_canary.json com o .dat) e gera:
  - catalogo_monstros.md: lista por categoria (pasta do Canary), com estrelas, vida, exp e se já está no jogo;
  - spr_previa/catalogo/<categoria>.png: folha com o sprite (parado, olhando para o sul) e o nome de cada um.
"""
import json, os, sys, unicodedata
from collections import defaultdict
from PIL import Image, ImageDraw
from gerar_sprites15 import Gerador

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
NOMES = {'quests': 'Quests', 'bosses': 'Bosses', 'humanoids': 'Humanoides', 'mammals': 'Mamíferos', 'humans': 'Humanos', 'magicals': 'Mágicos',
         'undeads': 'Mortos-vivos', 'vermins': 'Insetos e vermes', 'raids': 'Raids', 'reptiles': 'Répteis', 'aquatics': 'Aquáticos', 'demons': 'Demônios',
         'event_creatures': 'Eventos', 'constructs': 'Constructos', 'dawnport': 'Dawnport', 'elementals': 'Elementais', 'fey': 'Fadas (Fey)',
         'birds': 'Aves', 'dragons': 'Dragões', 'giants': 'Gigantes', 'lycanthropes': 'Licantropos', 'plants': 'Plantas', 'traps': 'Armadilhas',
         'amphibics': 'Anfíbios', 'slimes': 'Gosmas', 'extra_dimensional': 'Extradimensionais', 'nostalgia': 'Nostalgia', 'familiars': 'Familiares', 'trainers': 'Treino'}


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    cat = json.load(open(os.path.join(RAIZ, 'dados', 'catalogo_monstros.json'), encoding='utf-8'))
    canary = {m['nome']: m for m in json.load(open(os.path.join(RAIZ, 'dados', 'monstros_canary.json'), encoding='utf-8'))}
    grupos = defaultdict(list)
    for m in cat: grupos[m['pasta']].append(m)
    ordem = sorted(grupos, key=lambda k: (k in ('quests', 'bosses', 'raids', 'event_creatures', 'trainers'), -len(grupos[k])))
    # ---- lista em markdown
    L = ['# Catálogo de monstros com sprite e animação (cliente 15.01 + Canary)', '',
         f'Total: **{len(cat)}** monstros. ✅ = já está no jogo. Estrelas = dificuldade no Bestiário do Tibia (0 a 5).', '']
    for k in ordem:
        ms = sorted(grupos[k], key=lambda m: ((m['estrelas'] or 0), m['exp'] or 0, m['nome']))
        L.append(f"## {NOMES.get(k, k)} ({len(ms)})"); L.append('')
        L.append('| Monstro | Estrelas | Vida | Exp | Andar | No jogo |'); L.append('|---|---|---|---|---|---|')
        for m in ms:
            L.append(f"| {m['nome']} | {'★' * (m['estrelas'] or 0) or '–'} | {m['hp'] or '–'} | {m['exp'] or 0} | {m['quadros_andar']} quadros | {'✅' if m['no_jogo'] else ''} |")
        L.append('')
    open(os.path.join(RAIZ, 'catalogo_monstros.md'), 'w', encoding='utf-8').write('\n'.join(L))
    # ---- folhas visuais
    G = Gerador(); pasta = os.path.join(RAIZ, 'spr_previa', 'catalogo'); os.makedirs(pasta, exist_ok=True)
    CW, CH, COLS = 96, 92, 12
    for k in ordem:
        ms = sorted(grupos[k], key=lambda m: ((m['estrelas'] or 0), m['exp'] or 0, m['nome']))
        linhas = (len(ms) + COLS - 1) // COLS
        folha = Image.new('RGBA', (COLS * CW, linhas * CH + 26), (22, 24, 32, 255)); d = ImageDraw.Draw(folha)
        sa = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()   # a fonte padrão não tem acentos
        d.text((6, 6), sa(f"{NOMES.get(k, k)} - {len(ms)} monstros (verde = ja no jogo)"), fill=(242, 193, 78))
        for i, m in enumerate(ms):
            c = canary.get(m['nome'], {}); x, y = (i % COLS) * CW, 26 + (i // COLS) * CH
            im = None
            try:
                if m['tipo'] == 'criatura':
                    t = G.dat.criaturas[m['look']]; g = t['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
                    im = Image.new('RGBA', (W, H))
                    for py in [0] + [p for p in (1, 2) if (c.get('addons') or 0) & p]:
                        if py < g['py']: im.alpha_composite(G.colorido(g, 2, py, 0, (c.get('head', 0), c.get('body', 0), c.get('legs', 0), c.get('feet', 0)), W, H))
                else:
                    t = G.dat.itens[c['lookTypeEx']]; g = t['grupos'][0]; im = G.quadro(g, 0, 0, 0, 0, g['w'] * 32, g['h'] * 32)
            except Exception:
                im = None
            if im:
                if im.width > 64 or im.height > 64: im.thumbnail((64, 64), Image.NEAREST)
                folha.alpha_composite(im, (x + (CW - im.width) // 2, y + 64 - im.height))
            cor = (127, 224, 127) if m['no_jogo'] else (210, 214, 226)
            d.text((x + 3, y + 66), sa(m['nome'])[:15], fill=cor); d.text((x + 3, y + 77), f"{'*' * (m['estrelas'] or 0)} {m['exp'] or 0}xp", fill=(140, 146, 160))
        folha.convert('RGB').save(os.path.join(pasta, f'{k}.png'), optimize=True)
        print(k, len(ms))


if __name__ == '__main__':
    main()
