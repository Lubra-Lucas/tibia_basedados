#!/usr/bin/env python3
"""
Prepara sprites para o Tibia Idle a partir do pacote do TibiaWiki BR (pasta tibiawiki-sprites).

O canvas do navegador só desenha o 1º quadro de um GIF, então aqui cada GIF vira uma folha PNG
(quadros lado a lado) que o jogo anima sozinho:
  criaturas  → 8 quadros de andar (uma direção); parado = quadro 0
  roupas     → 4 quadros = 4 direções (frente, lado, costas, outro lado)
  magias     → o efeito é recortado do GIF de demonstração (fundo removido) + ícone

Uso: python preparar_sprites.py [--origem PASTA_DO_PACOTE]
Gera ../sprites/*.png e ../sprites.js
"""
import argparse, json, os, shutil, sys
import numpy as np
from PIL import Image, ImageSequence

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, '..', 'sprites')
ORIGEM_PADRAO = os.path.join(os.path.expanduser('~'), 'Downloads', 'tibiawiki-sprites', 'tibiawiki-sprites')

CRIATURAS = {'goblin': 'Goblin', 'goblin_scavenger': 'Goblin_Scavenger', 'goblin_assassin': 'Goblin_Assassin', 'goblin_leader': 'Goblin_Leader'}
ROUPAS = {'knight': 'Knight', 'paladin': 'Hunter', 'sorcerer': 'Mage', 'druid': 'Druid'}
# id da magia no jogo → (nome no wiki, tipo de posicionamento)
#   alvo: toca no monstro atingido | conjurador: em volta de quem lança | onda: sai de quem lança na direção do alvo
MAGIAS = {
    'exura': ('Light_Healing', 'conjurador'), 'exura_gran': ('Intense_Healing', 'conjurador'), 'exura_vita': ('Ultimate_Healing', 'conjurador'),
    'exura_gran_san': ('Salvation', 'conjurador'), 'exura_ico': ('Wound_Cleansing', 'conjurador'), 'exura_med_ico': ('Intense_Wound_Cleansing', 'conjurador'),
    'exori_ico': ('Brutal_Strike', 'alvo'), 'exori': ('Berserk', 'conjurador'), 'exori_gran': ('Fierce_Berserk', 'conjurador'),
    'exori_con': ('Ethereal_Spear', 'alvo'), 'exori_san': ('Divine_Missile', 'alvo'), 'exevo_mas_san': ('Divine_Caldera', 'conjurador'),
    'exori_vis': ('Energy_Strike', 'alvo'), 'exori_gran_vis': ('Strong_Energy_Strike', 'alvo'), 'exori_max_vis': ('Ultimate_Energy_Strike', 'alvo'),
    'exevo_vis_hur': ('Energy_Wave', 'onda'), 'exevo_gran_mas_vis': ('Rage_of_the_Skies', 'conjurador'),
    'exori_frigo': ('Ice_Strike', 'alvo'), 'exori_gran_frigo': ('Strong_Ice_Strike', 'alvo'), 'exori_max_frigo': ('Ultimate_Ice_Strike', 'alvo'),
    'exevo_frigo_hur': ('Ice_Wave', 'onda'), 'exevo_gran_mas_frigo': ('Eternal_Winter', 'conjurador'),
}


def ler_gif(caminho):
    im = Image.open(caminho)
    q, d = [], []
    for f in ImageSequence.Iterator(im):
        q.append(f.convert('RGBA').copy()); d.append(int(f.info.get('duration', 100) or 100))
    return q, d

def salvar_folha(quadros, destino):
    w, h = quadros[0].size
    s = Image.new('RGBA', (w * len(quadros), h))
    for i, f in enumerate(quadros): s.alpha_composite(f, (i * w, 0))
    s.save(destino, optimize=True)
    return w, h


def personagens(bg):
    """Acha os bonecos parados na demonstração (pixels coloridos sobre o chão cinza) e devolve o tile de cada um."""
    rgb = bg.astype(np.float32) / 255
    sat = rgb.max(2) - rgb.min(2)
    m = sat > .18
    H, W = m.shape
    vis = np.zeros_like(m); achados = []
    for y in range(H):
        for x in range(W):
            if m[y, x] and not vis[y, x]:
                pilha, pts = [(y, x)], []
                vis[y, x] = True
                while pilha:
                    cy, cx = pilha.pop(); pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not vis[ny, nx]:
                                vis[ny, nx] = True; pilha.append((ny, nx))
                if len(pts) > 40:
                    ys, xs = zip(*pts)
                    achados.append((int(np.mean(xs) + 6) // 32, int(np.mean(ys) + 6) // 32, len(pts)))
    achados.sort()
    return achados


def efeito(caminho_preview, tipo):
    q, dur = ler_gif(caminho_preview)
    F = np.stack([np.array(f).astype(np.int16) for f in q])
    bg = np.median(F[..., :3], axis=0)
    diff = np.abs(F[..., :3] - bg).max(axis=3) > 40
    # em magias grandes o chão da demonstração também "muda" (a tela pisca/escurece);
    # então só conta como efeito a cor que nunca aparece no fundo (chão e bonecos parados)
    cod = lambda a: (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2].astype(np.int64)
    cores_fundo = np.unique(cod(np.rint(bg).astype(np.int64)))
    diff &= ~np.isin(cod(F[..., :3]), cores_fundo)
    ativos = diff.reshape(len(F), -1).sum(1)
    # primeiro lançamento: do 1º quadro com mudança até uma pausa de 4 quadros
    ini = int(np.argmax(ativos > 0)); fim = ini; vazio = 0
    for i in range(ini, len(F)):
        if ativos[i] > 0: fim = i; vazio = 0
        else:
            vazio += 1
            if vazio >= 4: break
    T, H, W = diff.shape
    chars = personagens(bg)
    tiles_w, tiles_h = W // 32, H // 32
    if tipo == 'alvo' and len(chars) >= 2:
        ancora = chars[-1][:2]                      # boneco de treino (mais à direita)
    elif chars:
        ancora = chars[0][:2]                       # quem lança (mais à esquerda)
    else:
        ancora = (tiles_w // 2, tiles_h // 2)
    regiao = np.zeros((H, W), bool)
    if tipo == 'alvo':                              # só em volta do alvo (até 2 tiles)
        ax, ay = ancora
        regiao[max(0, (ay - 2) * 32):(ay + 3) * 32, max(0, (ax - 2) * 32):(ax + 3) * 32] = True
    else:
        regiao[:] = True
    mascaras = diff[ini:fim + 1] & regiao
    uniao = mascaras.any(0)
    if not uniao.any(): return None
    ys, xs = np.where(uniao)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    quadros = []
    for k, i in enumerate(range(ini, fim + 1)):
        a = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        mk = mascaras[k][y0:y1, x0:x1]
        a[mk] = F[i][y0:y1, x0:x1][mk].astype(np.uint8); a[mk, 3] = 255
        quadros.append(Image.fromarray(a, 'RGBA'))
    return {'quadros': quadros, 'ms': dur[ini:fim + 1], 'ax': int(ancora[0] * 32 - x0), 'ay': int(ancora[1] * 32 - y0), 'ancora': ancora, 'preview_tiles': (tiles_w, tiles_h)}


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    ap = argparse.ArgumentParser(); ap.add_argument('--origem', default=ORIGEM_PADRAO); a = ap.parse_args()
    org = a.origem
    for sub in ('criaturas', 'roupas', 'magias'): os.makedirs(os.path.join(DESTINO, sub), exist_ok=True)
    man = {'criaturas': {}, 'roupas': {}, 'magias': {}}

    for k, nome in CRIATURAS.items():
        q, d = ler_gif(os.path.join(org, 'criaturas', nome + '.gif'))
        w, h = salvar_folha(q, os.path.join(DESTINO, 'criaturas', k + '.png'))
        man['criaturas'][k] = {'src': f'tibia-assets/sprites/criaturas/{k}.png', 'w': w, 'h': h, 'n': len(q), 'ms': d}
        print('criatura', k, len(q), 'quadros', f'{w}x{h}')

    for voc, nome in ROUPAS.items():
        man['roupas'][voc] = {}
        for addon, suf in ((0, ''), (1, '_Addon_1'), (2, '_Addon_2'), (3, '_Addon_3')):
            p = os.path.join(org, 'outfits_addons', f'Outfit_{nome}_Male{suf}.gif')
            if not os.path.exists(p): continue
            q, d = ler_gif(p)
            arq = f'{voc}_addon{addon}.png'
            w, h = salvar_folha(q, os.path.join(DESTINO, 'roupas', arq))
            man['roupas'][voc][addon] = {'src': f'tibia-assets/sprites/roupas/{arq}', 'w': w, 'h': h, 'n': len(q)}
        print('roupa', voc, sorted(man['roupas'][voc]))

    for sid, (nome, tipo) in MAGIAS.items():
        ic = os.path.join(org, 'magias', nome + '.gif')
        if os.path.exists(ic):
            Image.open(ic).convert('RGBA').save(os.path.join(DESTINO, 'magias', sid + '_icone.png'))
        e = efeito(os.path.join(org, 'magias', nome + '_Preview.gif'), tipo)
        if not e: print('magia', sid, 'SEM EFEITO'); continue
        w, h = salvar_folha(e['quadros'], os.path.join(DESTINO, 'magias', sid + '.png'))
        man['magias'][sid] = {'src': f'tibia-assets/sprites/magias/{sid}.png', 'icone': f'tibia-assets/sprites/magias/{sid}_icone.png',
                              'w': w, 'h': h, 'n': len(e['quadros']), 'ms': e['ms'], 'ax': e['ax'], 'ay': e['ay'], 'tipo': tipo}
        print(f'magia {sid:22} {nome:24} {tipo:10} {len(e["quadros"]):2} quadros {w}x{h} âncora tile {e["ancora"]} de {e["preview_tiles"]}')

    with open(os.path.join(AQUI, '..', 'sprites.js'), 'w', encoding='utf-8') as f:
        f.write('/* gerado por ferramentas/preparar_sprites.py a partir do pacote do TibiaWiki BR */\nwindow.SPRITES=' + json.dumps(man, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print('ok →', os.path.abspath(DESTINO))


if __name__ == '__main__':
    main()
