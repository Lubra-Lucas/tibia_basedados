#!/usr/bin/env python3
"""Gera as folhas do personagem, dos monstros e dos cadáveres a partir do cliente 15.01 (.dat/.spr).

Folha de criatura: linhas = 4 direções na ordem do .dat (0 = norte, 1 = leste, 2 = sul, 3 = oeste);
colunas = quadros parados (grupo 0) seguidos dos quadros de andar (grupo 1).
As roupas são coloridas pela máscara (camada 1) com a paleta de 133 cores, e os addons
(padrãoY 1 e 2) são desenhados por cima da base, como no cliente.

Saída: sprites15/{roupas,criaturas,cadaveres}/*.png e sprites15.js (window.SPR15).
Os monstros novos vêm de dados/cacadas100_mobs.json (chave → nome), escrito por gerar_cacadas100.py.
Uso: python gerar_sprites15.py   (variáveis TIBIA_DAT / TIBIA_SPR mudam os arquivos de origem)
"""
import json, os, re, sys
from PIL import Image
from ler_dat_moderno import DatModerno, SprModerno
from gerar_roupas74 import cor_outfit

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..'))
TEMP = os.path.expandvars(r'%LOCALAPPDATA%\Temp')
DAT = os.environ.get('TIBIA_DAT', os.path.join(TEMP, 'Tibia (1).dat'))
SPR = os.environ.get('TIBIA_SPR', os.path.join(TEMP, 'Tibia.spr'))
DESTINO = os.path.join(RAIZ, 'sprites15')

# vocação → lookType masculino (mesmas roupas que o jogo já usava: Knight, Hunter, Mage, Druid) e cores cabeça/corpo/pernas/pés
VOC = {'knight': (131, (78, 76, 58, 95)), 'paladin': (129, (78, 69, 58, 76)),
       'sorcerer': (130, (78, 94, 79, 115)), 'druid': (144, (78, 82, 101, 114))}


class Gerador:
    def __init__(self):
        self.dat, self.spr = DatModerno(DAT), SprModerno(SPR)
        self.cache = {}

    def sprite(self, sid):
        im = self.cache.get(sid)
        if im is None:
            im = self.cache[sid] = self.spr.sprite(sid)
            if len(self.cache) > 20000: self.cache.clear()
        return im

    def quadro(self, g, d, py, fase, layer, W, H):
        im = Image.new('RGBA', (W, H))
        for y in range(g['h']):
            for x in range(g['w']):
                i = DatModerno.idx(g, x, y, layer, d % g['px'], py % g['py'], 0, fase % g['fases'])
                s = g['spr'][i] if i < len(g['spr']) else 0
                if s: im.alpha_composite(self.sprite(s), (W - (x + 1) * 32, H - (y + 1) * 32))
        return im

    def colorido(self, g, d, py, fase, cores, W, H):
        base = self.quadro(g, d, py, fase, 0, W, H)
        if g['layers'] < 2 or not cores: return base
        masc = self.quadro(g, d, py, fase, 1, W, H)
        cab, cor, per, pes = (cor_outfit(c) for c in cores)
        pb, pm = base.load(), masc.load()
        for y in range(H):
            for x in range(W):
                r, gg, b, a = pm[x, y]
                if not a: continue
                k = cab if (r and gg and not b) else cor if (r and not gg) else per if (gg and not r) else pes if b else None
                if k is None: continue
                br, bgc, bb, ba = pb[x, y]
                pb[x, y] = (br * k[0] // 255, bgc * k[1] // 255, bb * k[2] // 255, ba)
        return base

    def folha_criatura(self, look, cores, addons, destino):
        t = self.dat.criaturas.get(look)
        if not t: return None
        gs = t['grupos']
        W = max(g['w'] for g in gs) * 32; H = max(g['h'] for g in gs) * 32
        if len(gs) >= 2:
            parado, andar = [(gs[0], f) for f in range(gs[0]['fases'])], [(gs[1], f) for f in range(gs[1]['fases'])]
        else:                                                   # criatura antiga: fase 0 parada, demais andando
            g = gs[0]; n = g['fases']
            parado = [(g, 0)]; andar = [(g, f) for f in (range(1, n) if n >= 3 else range(n))]
        cols = parado + andar
        folha = Image.new('RGBA', (W * len(cols), H * 4))
        pys = [0] + [k for k in (1, 2) if addons & k]
        for d in range(4):
            for c, (g, f) in enumerate(cols):
                im = Image.new('RGBA', (W, H))
                for py in pys:
                    if py >= g['py']: continue
                    im.alpha_composite(self.colorido(g, d, py, f, cores, W, H))
                folha.paste(im, (c * W, d * H))
        folha.save(destino, optimize=True)
        g0 = gs[0]; desl = t['flags'].get('deslocamento') or (0, 0)
        ms = g0['anim']['ms'] if g0['anim'] else [300]
        return {'w': W, 'h': H, 'parado': len(parado), 'andar': len(andar), 'ms': ms, 'desl': list(desl) if isinstance(desl, tuple) else [8, 8]}

    def folha_item(self, cid, destino):
        """Item como criatura (lookTypeEx) ou cadáver: quadro 0, igual nas 4 direções."""
        t = self.dat.itens.get(cid)
        if not t: return None
        g = t['grupos'][0]; W, H = g['w'] * 32, g['h'] * 32
        im = self.quadro(g, 0, 0, 0, 0, W, H)
        if not im.getbbox(): return None
        im.save(destino, optimize=True)
        return {'w': W, 'h': H}


def main():
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    G = Gerador()
    for sub in ('roupas', 'criaturas', 'cadaveres'): os.makedirs(os.path.join(DESTINO, sub), exist_ok=True)
    out = {'roupas': {}, 'criaturas': {}, 'cadaveres': {}}

    for voc, (look, cores) in VOC.items():
        out['roupas'][voc] = {}
        for addon in range(4):
            arq = f'{voc}_addon{addon}.png'
            m = G.folha_criatura(look, cores, addon, os.path.join(DESTINO, 'roupas', arq))
            m['src'] = f'tibia-assets/sprites15/roupas/{arq}'
            out['roupas'][voc][addon] = m
        print('roupa', voc, look, {k: v for k, v in m.items() if k != 'src'})

    # monstros do jogo (dados_jogo.js) com o visual do Canary
    js = open(os.path.join(RAIZ, 'dados_jogo.js'), encoding='utf-8').read()
    mobs = json.loads(js[js.index('{'):js.rindex('}') + 1])['mobs']
    canary = {m['nome'].lower(): m for m in json.load(open(os.path.join(RAIZ, 'dados', 'monstros_canary.json'), encoding='utf-8'))}
    extra = {'rotworm', 'carrion_worm', 'fire_elemental'}                         # monstros de mapas próprios
    sem = []
    # monstros das 100 caçadas (gerar_cacadas100.py grava chave → nome do Canary)
    arq_extra = os.path.join(RAIZ, 'dados', 'cacadas100_mobs.json')
    novos = {k: v['nome'] for k, v in json.load(open(arq_extra, encoding='utf-8')).items()} if os.path.exists(arq_extra) else {}
    for chave in sorted(set(mobs) | extra | set(novos)):
        nome = novos.get(chave) or (mobs[chave]['n'] if chave in mobs else chave.replace('_', ' '))
        c = canary.get(nome.lower())
        if not c: sem.append(chave); continue
        arq = os.path.join(DESTINO, 'criaturas', chave + '.png')
        if c['lookType']:
            m = G.folha_criatura(c['lookType'], (c['head'], c['body'], c['legs'], c['feet']), c.get('addons', 0) or 0, arq)
        elif c.get('lookTypeEx'):
            m = G.folha_item(c['lookTypeEx'], arq)
            if m: m.update({'parado': 1, 'andar': 1, 'ms': [300], 'desl': [0, 0], 'item': True})
        else: m = None
        if not m: sem.append(chave); continue
        if m.get('item'):                                       # repete o item nas 4 linhas
            im = Image.open(arq); f = Image.new('RGBA', (im.width, im.height * 4))
            for d in range(4): f.paste(im, (0, d * im.height))
            f.save(arq)
        m['src'] = f'tibia-assets/sprites15/criaturas/{chave}.png'
        out['criaturas'][chave] = m
        cad = c.get('cadaver')
        if cad:
            arqc = os.path.join(DESTINO, 'cadaveres', f'{cad}.png')
            mc = out['cadaveres'].get(cad) or G.folha_item(cad, arqc)
            if mc:
                mc['src'] = f'tibia-assets/sprites15/cadaveres/{cad}.png'
                out['cadaveres'][cad] = mc; m['cad'] = cad
    print('monstros', len(out['criaturas']), 'cadáveres', len(out['cadaveres']), 'sem visual', sem)
    with open(os.path.join(RAIZ, 'sprites15.js'), 'w', encoding='utf-8') as fp:
        fp.write('/* gerado por ferramentas/gerar_sprites15.py (cliente Tibia 15.01) */\nwindow.SPR15=' + json.dumps(out, separators=(',', ':')) + ';\n')

    # prévia: as 4 direções de cada roupa (parado + 4 quadros de andar) e alguns monstros
    linhas = []
    for voc in VOC:
        m = out['roupas'][voc][3]; f = Image.open(os.path.join(RAIZ, '..', m['src']))
        linhas.append(f.crop((0, 0, m['w'] * min(9, m['parado'] + m['andar']), m['h'] * 4)))
    for chave in ('rotworm', 'dragon', 'demon', 'cyclops', 'amazon', 'goblin'):
        m = out['criaturas'].get(chave)
        if m: f = Image.open(os.path.join(RAIZ, '..', m['src'])); linhas.append(f.crop((0, 0, min(f.width, m['w'] * 9), m['h'] * 4)))
    Wp = max(l.width for l in linhas); Hp = sum(l.height // 4 for l in linhas)
    prev = Image.new('RGBA', (Wp, Hp), (58, 46, 34, 255)); y = 0
    for l in linhas:
        prev.alpha_composite(l.crop((0, 2 * l.height // 4, l.width, 3 * l.height // 4)), (0, y)); y += l.height // 4   # direção sul
    prev.save(os.path.join(RAIZ, 'spr_previa', 'sprites15_previa.png'))


if __name__ == '__main__':
    main()
