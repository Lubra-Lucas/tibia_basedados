#!/usr/bin/env python3
"""Lê os scripts de magias e runas do Canary e devolve registros normalizados para o jogo.

Cada magia vira um dicionário com: id (palavras com _), nome, voc, lv, mana, cd, gcd, focus, grupo e
um tipo de jogo 't':
  ataque:  'alvo' (strike), 'dot' (dano contínuo), 'onda' (na direção), 'self' (área em volta)
  cura:    'cura' (cura a si), 'cura_amigo' (exura sio: só em outro), 'regen' (utura), 'cura_cond' (exana)
  suporte: 'haste', 'buff' (blood rage, protector, sharpshooter), 'escudo', 'conjurar', 'familiar', 'invocar', 'util'
Runas (Spell("rune")): 'alvo', 'area' (área no alvo), 'cura', 'lento' (paralyze), 'campo', 'util'.

A fórmula é traduzida de Lua para o corpo de uma função JS (parâmetros: player + os da função original).
"""
import json, os, re

COND_EL = {'FIRE': 'fire', 'ENERGY': 'energy', 'CURSED': 'death', 'POISON': 'earth', 'BLEEDING': 'phys', 'FREEZING': 'ice', 'DAZZLED': 'holy'}
EL = {'ENERGY': 'energy', 'FIRE': 'fire', 'DEATH': 'death', 'EARTH': 'earth', 'ICE': 'ice', 'HOLY': 'holy', 'PHYSICAL': 'phys'}
VOCS = ('knight', 'paladin', 'sorcerer', 'druid')


def lua2js(corpo):
    """Traduz o corpo de uma função de fórmula Lua para JS (devolve [min, max])."""
    out = []
    for l in corpo.split('\n'):
        l = re.sub(r'--.*$', '', l).rstrip()
        if not l.strip(): continue
        s = l.strip()
        s = s.replace('player:getLevel()', 'player.level').replace('player:getMagicLevel()', 'player.ml')
        s = re.sub(r'(\w+):(\w+)\(', r'\1.\2(', s)
        s = re.sub(r'\bmath\.', 'Math.', s)
        s = s.replace('~=', '!=')
        s = re.sub(r'\band\b', '&&', s); s = re.sub(r'\bor\b', '||', s); s = re.sub(r'\bnot\b', '!', s)
        s = re.sub(r'\blocal\s+', 'let ', s)
        s = re.sub(r'=\s*\{([^{}]*)\}\s*$', r'= [null, \1]', s)                 # tabela Lua (índice 1) → array JS
        m = re.match(r'^if (.+) then$', s)
        if m: out.append(f'if ({m.group(1)}) {{'); continue
        m = re.match(r'^elseif (.+) then$', s)
        if m: out.append(f'}} else if ({m.group(1)}) {{'); continue
        if s == 'else': out.append('} else {'); continue
        if s == 'end': out.append('}'); continue
        m = re.match(r'^return (.+)$', s)
        if m:
            partes = dividir_virgulas(m.group(1))
            out.append(f'return [{", ".join(partes)}];' if len(partes) == 2 else f'return {m.group(1)};'); continue
        out.append(s + ('' if s.endswith(('{', '}')) else ';'))
    js = '\n'.join(out)
    js = re.sub(r'\b(WHEEL_GRADE_\w+|[A-Z][A-Z0-9_]{3,})\b', '0', js)       # constantes do servidor → 0
    return js


def dividir_virgulas(s):
    partes, prof, atual = [], 0, ''
    for c in s:
        if c in '([': prof += 1
        if c in ')]': prof -= 1
        if c == ',' and prof == 0: partes.append(atual.strip()); atual = ''
        else: atual += c
    partes.append(atual.strip())
    return partes


def formula(s):
    """Acha a função de fórmula (formulaFunction ou onGetFormulaValues*) e devolve (params, corpo_js)."""
    cands = [c for c in re.finditer(r'function\s+([\w.:]+)\s*\(\s*_?player\s*,\s*([^)]*)\)[^\n]*\n(.*?)\nend\b', s, re.S) if 'ormula' in c.group(1)]
    if not cands: return None
    pref = [c for c in cands if 'formulaFunction' in c.group(1)] or [c for c in cands if 'onGetFormulaValues' in c.group(1)] or cands
    c = pref[0]
    params = [p.strip() for p in c.group(2).split(',') if p.strip()]
    corpo = c.group(3)
    # corta no 'end' que fecha a função: conta blocos if/function
    linhas, prof, ok = [], 0, []
    for l in corpo.split('\n'):
        t = re.sub(r'--.*$', '', l).strip()
        if re.match(r'^(if .+ then|function\b.*)$', t): prof += 1
        if t == 'end':
            if prof == 0: break
            prof -= 1
        ok.append(l)
    return params, lua2js('\n'.join(ok))


def areas(caminho):
    txt = open(caminho, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^(AREA\w*)\s*=\s*\{(.*?)^\}', txt, re.S | re.M):
        linhas = [[int(v) for v in re.findall(r'-?\d+', l)] for l in re.findall(r'\{([^{}]*)\}', m.group(2))]
        if linhas: out[m.group(1)] = linhas
    return out


def num(rx, s, padrao=None, f=float):
    m = re.search(rx, s)
    return f(m.group(1)) if m else padrao


def ms(expr):
    try: return int(eval(expr.replace('math.', '')))
    except Exception: return None


def ler(caminho, me, ani, AREAS, itens_campo=None):
    s = open(caminho, encoding='utf-8').read()
    runa = 'Spell("rune")' in s
    pref = 'rune' if runa else 'spell'
    nome = num(rf'{pref}:name\("([^"]+)"\)', s, None, str)
    if not nome: return None
    palavras = num(rf'{pref}:words\("([^"]+)"\)', s, '', str)
    g = re.search(rf'{pref}:group\(([^)]*)\)', s)
    grupos = re.findall(r'"(\w+)"', g.group(1)) if g else []
    vt = ' '.join(re.findall(r'vocation\(([^)]*)\)', s)).lower()
    voc = [v for v in VOCS if v in vt]
    gcd = re.search(rf'{pref}:groupCooldown\(([^,)]+)(?:,\s*([^)]+))?\)', s)
    m = {'nome': nome, 'palavras': palavras, 'grupo': grupos[0] if grupos else None, 'grupos': grupos, 'voc': voc,
         'lv': int(num(rf'{pref}:level\((\d+)\)', s, 1)), 'mana': int(num(rf'{pref}:mana\((\d+)\)', s, 0)),
         'cd': ms(num(rf'{pref}:cooldown\(([^)]+)\)', s, '2000', str)) or 0,
         'gcd': (ms(gcd.group(1)) or 0) if gcd else 2000,
         'focus': (ms(gcd.group(2)) or 0) if gcd and gcd.group(2) and 'focus' in grupos else 0,
         'alcance': int(num(rf'{pref}:range\((\d+)\)', s, 0)),
         'arma': 'needWeapon(true)' in s, 'aprender': 'needLearn(true)' in s,
         'arquivo': os.path.basename(caminho)}
    tipo = num(r'COMBAT_PARAM_TYPE,\s*COMBAT_(\w+)', s, None, str)
    if tipo:
        tipo = tipo.replace('DAMAGE', '')
        m['el'] = 'cura' if tipo == 'HEALING' else EL.get(tipo, 'phys')
    elif 'COMBAT_HEALING' in s: m['el'] = 'cura'
    ef = re.search(r'COMBAT_PARAM_EFFECT,\s*(CONST_ME_\w+)', s)
    if ef: m['ef'] = me.get(ef.group(1))
    tr = re.search(r'COMBAT_PARAM_DISTANCEEFFECT,\s*(CONST_ANI_\w+)', s)
    if tr: m['tiro'] = ani.get(tr.group(1)) if tr.group(1) != 'CONST_ANI_WEAPONTYPE' else -1   # -1 = projétil da arma
    ar = re.search(r'createCombat(?:Area)?\((?:\w+,\s*)?(AREA_\w+)', s)
    if ar and ar.group(1) in AREAS: m['area'] = AREAS[ar.group(1)]; m['area_nome'] = ar.group(1)
    f = formula(s)
    if not f:   # fórmula solta (ex.: Mass Healing calcula min/max dentro do callback do alvo)
        mn, mx = re.search(r'local min = (.+)', s), re.search(r'local max = (.+)', s)
        if mn and mx and ('getMagicLevel' in mn.group(1) or 'getLevel' in mn.group(1)):
            f = ([], lua2js(f'local min = {mn.group(1)}\nlocal max = {mx.group(1)}\nreturn min, max'))
    if f:
        m['fparams'], m['f'] = f
        m['ftipo'] = 'sk' if 'SKILLVALUE' in s else 'lm'
    def qtd(e):
        r = re.match(r'math\.random\((\d+),\s*(\d+)\)', e.strip())
        return (int(r.group(1)) + int(r.group(2))) // 2 if r else int(e)
    ticks = [[qtd(n), int(i), int(d)] for n, i, d in re.findall(r'addDamage\(([^,]+(?:,\s*\d+\))?),\s*(\d+),\s*-(\d+)\)', s)]
    if ticks:
        m['dot'] = ticks
        c = re.search(r'Condition\(CONDITION_(\w+)', s)
        m['dot_el'] = COND_EL.get(c.group(1), m.get('el', 'phys')) if c else m.get('el', 'phys')
    disp = re.findall(r'COMBAT_PARAM_DISPEL,\s*CONDITION_(\w+)', s)
    if disp: m['dispel'] = [d.lower() for d in disp]
    if runa:
        m['runa'] = True
        m['item'] = int(num(r'rune:runeId\((\d+)\)', s, 0))
        m['cargas'] = int(num(r'rune:charges\((\d+)\)', s, 1))
        m['ml'] = int(num(r'rune:magicLevel\((\d+)\)', s, 0))
        cria = re.search(r'COMBAT_PARAM_CREATEITEM,\s*(\w+)', s)
        if cria: m['cria'] = cria.group(1)
    # ---- condições de suporte
    def pt(p):
        v = num(rf'CONDITION_PARAM_{p},\s*([\d.]+)', s)
        if v is None:   # valor numa variável local (ex.: Sap Strength: local buff = 90)
            nomev = num(rf'CONDITION_PARAM_{p},\s*(\w+)\)', s, None, str)
            if nomev: v = num(rf'local {nomev}\s*=\s*([\d.]+)', s)
        return v
    dur = num(r'CONDITION_PARAM_TICKS,\s*([^)]+)\)', s, None, str)
    dur = ms(dur) if dur else None
    if re.search(r'spellDuration\s*=\s*(\d+)', s): dur = int(re.search(r'spellDuration\s*=\s*(\d+)', s).group(1))
    hf = re.search(r'Condition\(CONDITION_HASTE\).*?setFormula\(([\d.]+)', s, re.S)
    pf = re.search(r'Condition\(CONDITION_PARALYZE\).*?setFormula\((-?[\d.]+)', s, re.S)
    buff = {k: pt(p) for k, p in (('melee', 'SKILL_MELEEPERCENT'), ('dist', 'SKILL_DISTANCEPERCENT'), ('escudo', 'SKILL_SHIELDPERCENT'),
                                  ('feito', 'BUFF_DAMAGEDEALT'), ('recebido', 'BUFF_DAMAGERECEIVED')) if pt(p)}
    if 'DISABLE_DEFENSE, true' in s: buff['sem_defesa'] = True
    conj = re.search(r'conjureItem\((\d+),\s*(\d+),\s*(\d+)', s)
    # ---- classificação
    g0 = m['grupo']
    if runa:
        if m.get('el') == 'cura': m['t'] = 'cura'
        elif pf: m['t'] = 'lento'; m['lento'] = float(pf.group(1)); m['dur'] = dur or 20000
        elif m.get('cria'): m['t'] = 'campo'
        elif ticks and not m.get('f'): m['t'] = 'dot'; m['alcance'] = 7
        elif m.get('f') and 'needTarget(true)' in s: m['t'] = 'alvo'
        elif m.get('f') and m.get('area'): m['t'] = 'area'
        elif m.get('f'): m['t'] = 'alvo'
        else: m['t'] = 'util'
    elif conj: m['t'] = 'conjurar'; m['conj'] = [int(conj.group(1)), int(conj.group(2)), int(conj.group(3))]
    elif 'CreateFamiliarSpell' in s: m['t'] = 'familiar'
    elif palavras == 'utevo res': m['t'] = 'invocar'
    elif 'CONDITION_MANASHIELD' in s: m['t'] = 'escudo'
    elif m.get('el') == 'cura':
        m['t'] = 'cura_amigo' if ('needTarget(true)' in s and 'isSelfTarget' not in s) else 'cura'
    elif 'CONDITION_REGENERATION' in s:
        m['t'] = 'regen'; m['regen'] = [pt('HEALTHGAIN') or 0, pt('HEALTHTICKS') or 3000]; m['dur'] = dur or 60000
    elif disp and not m.get('f'): m['t'] = 'cura_cond'
    elif m.get('f') or ticks:
        if not m.get('f') and ticks: m['t'] = 'dot'
        elif m.get('area'): m['t'] = 'onda' if 'needDirection(true)' in s else 'self'
        else: m['t'] = 'alvo'
        if not m['alcance'] and m['t'] in ('alvo', 'dot'): m['alcance'] = 1 if m.get('arma') and not m.get('tiro') else 3
    elif buff and 'target:addCondition' in s:   # Expose Weakness / Sap Strength: enfraquece quem está na área
        m['t'] = 'debuff'; m['buff'] = buff; m['dur'] = dur or 16000
    elif buff:
        m['t'] = 'buff'; m['buff'] = buff; m['dur'] = dur or 10000
        if hf: m['haste'] = float(hf.group(1))
        if pf: m['lento_self'] = float(pf.group(1))
    elif hf:
        m['t'] = 'haste'; m['haste'] = float(hf.group(1)); m['dur'] = dur or 30000
    else:
        m['t'] = 'util'
    m['id'] = ('runa_' + str(m['item'])) if runa else (palavras.replace(' ', '_') or nome.lower().replace(' ', '_'))
    return m
