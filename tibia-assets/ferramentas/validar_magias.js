// Valida as fórmulas traduzidas de Lua para JS (uso: node validar_magias.js magias.json)
const L = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const player = { level: 100, ml: 80, upgradeSpellsWOD: () => 0, instantSkillWOD: () => false };
const roda = m => new Function('player', ...m.fparams, m.f)(player, ...(m.ftipo === 'sk' ? [90, 50, 1] : [100, 80]));
let ok = 0; const falha = [], tipos = {};
for (const m of L) {
  tipos[m.t] = (tipos[m.t] || 0) + 1;
  if (!m.f) continue;
  try { const r = roda(m); if (!Array.isArray(r) || r.some(v => typeof v !== 'number' || isNaN(v))) throw new Error('retorno ' + JSON.stringify(r)); ok++; }
  catch (e) { falha.push(m.nome + ': ' + e.message); }
}
console.log('total', L.length, 'fórmulas ok', ok, 'falhas', falha);
console.log(JSON.stringify(tipos));
console.log('sem fórmula:', L.filter(m => ['alvo', 'onda', 'self', 'area', 'cura'].includes(m.t) && !m.f).map(m => m.nome).join(', '));
for (const n of process.argv.slice(3)) {
  const m = L.find(x => x.nome.toLowerCase() === n.toLowerCase()); if (!m) { console.log('??', n); continue; }
  const r = m.f ? roda(m) : null;
  console.log(m.nome, '|', m.t, m.el || '', m.ftipo || '', r && r.map(Math.round), JSON.stringify(m.buff || ''), m.area_nome || '', m.dur || '');
}
