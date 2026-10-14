#!/usr/bin/env python3
"""Gera as folhas de andar do personagem a partir do Tibia 7.4 (.spr + .dat).

Cada outfit do 7.4 tem 4 direções × 3 fases (0 = parado, 1 e 2 = passos) e 2 camadas:
a camada 1 é a máscara (amarelo = cabeça, vermelho = corpo, verde = pernas, azul = pés)
que recebe a cor escolhida multiplicada sobre a camada 0, como no cliente.

Saída: sprites/roupas74/<vocacao>.png (colunas = fases, linhas = direções na ordem do jogo:
0 = sul, 1 = leste, 2 = norte, 3 = oeste) e roupas74.js (window.ROUPAS74).
Uso: python gerar_roupas74.py [Tibia.spr] [Tibia.dat]
"""
import json, os, sys
from PIL import Image
from ler_spr import Spr
from ler_dat import Dat

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, '..')
SPR = sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(r'%LOCALAPPDATA%\Temp\Tibia (1).spr')
DAT = sys.argv[2] if len(sys.argv) > 2 else os.path.expandvars(r'%LOCALAPPDATA%\Temp\Tibia.dat')

# vocação → (lookType do 7.4, cores cabeça/corpo/pernas/pés na paleta de 133 cores do Tibia)
VOC = {'knight': (131, (78, 76, 58, 95)), 'paladin': (129, (78, 69, 58, 76)),
       'sorcerer': (133, (78, 94, 79, 115)), 'druid': (130, (78, 82, 101, 114))}
ORDEM_JOGO = (2, 1, 0, 3)          # direção do jogo (S, L, N, O) → padrãoX do .dat (N, L, S, O)


def cor_outfit(c):
    """Paleta HSI do Tibia (19 matizes × 7 saturação/brilho), igual ao Outfit::getColor do OTClient."""
    H, SI = 19, 7
    if c >= H * SI: c = 0
    if c % H:
        h = c % H / 18.0
        s, i = [(.25, 1), (.25, .75), (.5, .75), (.667, .75), (1, 1), (1, .75), (1, .5)][c // H]
    else:
        h, s, i = 0, 0, 1 - c / H / SI
    if i == 0: return (0, 0, 0)
    if s == 0: v = int(i * 255); return (v, v, v)
    if h < 1 / 6: r = i; b = i * (1 - s); g = b + (i - b) * 6 * h
    elif h < 2 / 6: g = i; b = i * (1 - s); r = g - (i - b) * (6 * h - 1)
    elif h < 3 / 6: g = i; r = i * (1 - s); b = r + (i - r) * (6 * h - 2)
    elif h < 4 / 6: b = i; r = i * (1 - s); g = b - (i - r) * (6 * h - 3)
    elif h < 5 / 6: b = i; g = i * (1 - s); r = g + (i - g) * (6 * h - 4)
    else: r = i; g = i * (1 - s); b = r - (i - g) * (6 * h - 5)
    return (int(r * 255), int(g * 255), int(b * 255))


def colorir(base, mascara, cores):
    """Multiplica a cor de cada parte (pela máscara) sobre o sprite base."""
    cab, cor, per, pes = (cor_outfit(c) for c in cores)
    out = base.copy(); po, pm = out.load(), mascara.load()
    for y in range(base.height):
        for x in range(base.width):
            r, g, b, a = pm[x, y]
            if not a: continue
            k = cab if (r and g and not b) else cor if (r and not g) else per if (g and not r) else pes if b else None
            if k is None: continue
            br, bg, bb, ba = po[x, y]
            po[x, y] = (br * k[0] // 255, bg * k[1] // 255, bb * k[2] // 255, ba)
    return out


def quadro(spr, t, d, f, layer):
    im = Image.new('RGBA', (t['w'] * 32, t['h'] * 32))
    for y in range(t['h']):
        for x in range(t['w']):
            i = Dat.sprite_idx(None, t, x, y, layer, d, 0, f)
            if t['spr'][i]: im.alpha_composite(spr.sprite(t['spr'][i]), ((t['w'] - 1 - x) * 32, (t['h'] - 1 - y) * 32))
    return im


def main():
    spr, dat = Spr(SPR), Dat(DAT)
    pasta = os.path.join(RAIZ, 'sprites', 'roupas74'); os.makedirs(pasta, exist_ok=True)
    meta = {}
    for voc, (look, cores) in VOC.items():
        t = dat.criaturas[look]; w, h = t['w'] * 32, t['h'] * 32
        folha = Image.new('RGBA', (w * t['fases'], h * 4))
        for linha, d in enumerate(ORDEM_JOGO):
            for f in range(t['fases']):
                im = quadro(spr, t, d, f, 0)
                if t['layers'] > 1: im = colorir(im, quadro(spr, t, d, f, 1), cores)
                folha.paste(im, (f * w, linha * h))
        folha.save(os.path.join(pasta, voc + '.png'))
        desl = 8 if t['flags'].get('deslocamento') else 0          # no 7.4 o deslocamento é fixo: 8px para cima/esquerda
        meta[voc] = {'src': f'tibia-assets/sprites/roupas74/{voc}.png', 'w': w, 'h': h, 'fases': t['fases'], 'desl': desl, 'look': look}
        print(voc, 'look', look, f'{w}x{h}', t['fases'], 'fases', 'desl', desl)
    with open(os.path.join(RAIZ, 'roupas74.js'), 'w', encoding='utf-8') as fp:
        fp.write('/* gerado por ferramentas/gerar_roupas74.py */\nwindow.ROUPAS74=' + json.dumps(meta, separators=(',', ':')) + ';\n')
    # prévia ampliada para conferir
    prev = Image.new('RGBA', (len(meta) * 3 * 34 + 8, 4 * 34 + 8), (40, 30, 20, 255))
    for k, voc in enumerate(meta):
        fo = Image.open(os.path.join(pasta, voc + '.png'))
        for d in range(4):
            for f in range(3): prev.alpha_composite(fo.crop((f * 32, d * 32, f * 32 + 32, d * 32 + 32)), (4 + (k * 3 + f) * 34, 4 + d * 34))
    prev.resize((prev.width * 3, prev.height * 3), Image.NEAREST).save(os.path.join(RAIZ, 'spr_previa', 'roupas74_previa.png'))


if __name__ == '__main__':
    main()
