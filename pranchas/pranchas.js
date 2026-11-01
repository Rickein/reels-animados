'use strict';
// ================= base =================
const W = 1080, H = 1920, VIDEO = '/Bruto/snapinsta-1793403401783.mp4';
const MX = 40, MY = 230, MW = 540, MH = 960;   // onde a previa do video fica na prancha
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const prog = (t, a, d) => clamp((t - a) / d);
const E = {
  outExpo: t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t),
  outCubic: t => 1 - Math.pow(1 - t, 3),
  inOut: t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
  back: (t, s = 1.70158) => { const c = s + 1; return 1 + c * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2); },
};
function rng(seed) { let a = (seed * 2654435761) >>> 0; return () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function shake(t, t0, dur, amp, fps, grade) {
  if (t < t0 || t > t0 + dur) return [0, 0];
  const k = 1 - (t - t0) / dur, r = rng(Math.floor((t - t0) * fps) + 17);
  let dx = (r() * 2 - 1) * amp * k, dy = (r() * 2 - 1) * amp * k;
  if (grade) { dx = Math.round(dx / grade) * grade; dy = Math.round(dy / grade) * grade; }
  return [dx, dy];
}
function rrect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`; }
function fit(g, fn, text, size, maxW) { while (size > 8) { g.font = fn(size); if (g.measureText(text).width <= maxW) break; size -= 2; } return size; }
function wrapLines(g, text, maxW) { const ws = text.split(' '), out = []; let cur = ''; for (const w of ws) { const t = cur ? cur + ' ' + w : w; if (cur && g.measureText(t).width > maxW) { out.push(cur); cur = w; } else cur = t; } if (cur) out.push(cur); return out; }
function para(g, text, x, y, maxW, lh) { const ls = wrapLines(g, text, maxW); ls.forEach((l, i) => g.fillText(l, x, y + i * lh)); return ls.length * lh; }
function heartGeo(g, cx, cy, s) {
  const r = s / 4; g.beginPath(); g.moveTo(cx, cy + 1.8 * r);
  g.lineTo(cx - r - 0.866 * r, cy + 0.1 * r);
  g.arc(cx - r, cy - 0.4 * r, r, 5 * Math.PI / 6, 2 * Math.PI, false);
  g.arc(cx + r, cy - 0.4 * r, r, Math.PI, 2 * Math.PI + Math.PI / 6, false);
  g.closePath();
}

// ---- legenda: palavras, blocos e diagramacao ----
function mkWords(text, t0, step, chunks, keys) {
  const ws = text.split(' '); let i = 0; const out = [];
  chunks.forEach((n, c) => { for (let j = 0; j < n; j++, i++) out.push({ w: ws[i], t: t0 + i * step, c, k: keys.includes(i), i }); });
  return out;
}
function chunkAt(ws, t) { let c = -1; for (const w of ws) if (w.t <= t) c = w.c; return c < 0 ? null : ws.filter(w => w.c === c); }
function lineW(l, sp) { return l.reduce((a, w, i) => a + w.ww + (i ? sp : 0), 0); }
function layout(g, ws, fn, sizes, maxW, upper) {
  let res;
  for (const s of sizes) {
    g.font = fn(s); const sp = g.measureText(' ').width; const lines = [[]]; let lw = 0;
    for (const w of ws) {
      const txt = upper ? w.w.toUpperCase() : w.w, ww = g.measureText(txt).width, cur = lines[lines.length - 1];
      const add = (cur.length ? sp : 0) + ww, item = { ...w, txt, ww };
      if (cur.length && lw + add > maxW) { lines.push([item]); lw = ww; } else { cur.push(item); lw += add; }
    }
    res = { s, lines, sp };
    if (lines.length <= 2 && lines.every(l => lineW(l, sp) <= maxW)) return res;
  }
  return res;
}

// ---- traco a mao (direcao B) ----
function subdiv(pts, step) { const out = []; for (let i = 0; i < pts.length - 1; i++) { const [x0, y0] = pts[i], [x1, y1] = pts[i + 1]; const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / step)); for (let j = 0; j < n; j++) out.push([x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n]); } out.push(pts[pts.length - 1]); return out; }
function jitter(pts, seed, amp) { const r = rng(seed); let ox = 0, oy = 0; return pts.map(([x, y]) => { ox = ox * .7 + (r() * 2 - 1) * amp * .5; oy = oy * .7 + (r() * 2 - 1) * amp * .5; return [x + ox, y + oy]; }); }
function cutPts(pts, f0, f1) {
  if (f0 <= 0 && f1 >= 1) return pts;
  const d = [0]; for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const L = d[d.length - 1], a = f0 * L, b = f1 * L;
  const at = s => { let i = 1; while (i < pts.length - 1 && d[i] < s) i++; const k = (s - d[i - 1]) / ((d[i] - d[i - 1]) || 1); return [lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)]; };
  const out = [at(a)]; for (let i = 0; i < pts.length; i++) if (d[i] > a && d[i] < b) out.push(pts[i]); out.push(at(b)); return out;
}
function smooth(g, pts) {
  if (pts.length < 2) return; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length - 1; i++) g.quadraticCurveTo(pts[i][0], pts[i][1], (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2);
  const l = pts[pts.length - 1]; g.lineTo(l[0], l[1]); g.stroke();
}
function hand(g, pts, o = {}) {
  const { seed = 1, amp = 2.5, w = 7, color = '#000', f0 = 0, f1 = 1, closed = false, step = 12 } = o;
  if (f1 <= f0) return;
  const p = subdiv(closed ? [...pts, pts[0]] : pts, step);
  g.save(); g.lineCap = 'round'; g.lineJoin = 'round'; g.strokeStyle = color; g.lineWidth = w;
  smooth(g, cutPts(jitter(p, seed, amp), f0, f1));
  g.globalAlpha *= .5; g.lineWidth = w * .45; smooth(g, cutPts(jitter(p, seed + 31, amp * 1.3), f0, f1));
  g.restore();
}
const rectPts = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
function ellPts(cx, cy, rx, ry, turns = 1, a0 = -2.4, n = 40) { const p = [], N = Math.round(n * turns); for (let i = 0; i <= N; i++) { const a = a0 + i / n * Math.PI * 2, k = 1 + 0.06 * (i / N); p.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); } return p; }
function zigPts(x, y, w, h, n) { const p = []; for (let i = 0; i <= n; i++) p.push([x + w * i / n + (i % 2 ? -8 : 8), i % 2 ? y + h : y]); return p; }
function bezPts(p0, p1, p2, p3, n = 28) { const o = []; for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t; o.push([u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0], u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]]); } return o; }
function arrowHead(g, from, to, len, o) { const a = Math.atan2(to[1] - from[1], to[0] - from[0]); hand(g, [[to[0] - Math.cos(a - 0.5) * len, to[1] - Math.sin(a - 0.5) * len], to, [to[0] - Math.cos(a + 0.5) * len, to[1] - Math.sin(a + 0.5) * len]], o); }

// ---- pixel (direcao C) ----
const P = 6, snap = v => Math.round(v / P) * P;
function pxBox(g, x, y, w, h, o) {
  const { fill, border, shadow, p = P } = o; x = snap(x); y = snap(y); w = snap(w); h = snap(h);
  if (shadow) { g.fillStyle = shadow; g.fillRect(x + 2 * p, y + p, w - 2 * p, h); g.fillRect(x + p, y + 2 * p, w, h - 2 * p); }
  g.fillStyle = border; g.fillRect(x + p, y, w - 2 * p, h); g.fillRect(x, y + p, w, h - 2 * p);
  g.fillStyle = fill; g.fillRect(x + 2 * p, y + p, w - 4 * p, h - 2 * p); g.fillRect(x + p, y + 2 * p, w - 2 * p, h - 4 * p);
}
const SPR = {
  heart: ['.rr...rr.', 'rwrr.rrrr', 'rwrrrrrrr', 'rrrrrrrrr', '.rrrrrrr.', '..rrrrr..', '...rrr...', '....r....'],
  heartE: ['.cc...cc.', 'c..c.c..c', 'c...c...c', 'c.......c', '.c.....c.', '..c...c..', '...c.c...', '....c....'],
  phone: ['.ccccc.', 'ccccccc', 'cnnnnnc', 'cnrnrnc', 'cnrrrnc', 'cnnrnnc', 'cnnnnnc', 'cnnnnnc', 'ccccccc', 'ccc.ccc', '.ccccc.'],
  coin: ['..gggg..', '.gccggg.', 'gcgggggg', 'gcggnggg', 'ggggnggg', 'ggggnggg', '.gggggg.', '..gggg..'],
  dumbbell: ['.cc......cc.', 'ccc......ccc', 'cccccccccccc', 'cccccccccccc', 'ccc......ccc', '.cc......cc.'],
  check: ['......g', '.....gg', 'g...gg.', 'gg.gg..', '.ggg...', '..g....'],
  tri: ['g...', 'gg..', 'ggg.', 'gggg', 'ggg.', 'gg..', 'g...'],
  down: ['ggggg', '.ggg.', '..g..'],
};
function sprite(g, name, x, y, p, map) { SPR[name].forEach((row, j) => { for (let i = 0; i < row.length; i++) { const ch = row[i]; if (ch === '.') continue; g.fillStyle = map[ch]; g.fillRect(x + i * p, y + j * p, p, p); } }); }

// ================= sons sintetizados =================
let AC = null, MASTER = null;
function audio() { if (!AC) { AC = new AudioContext(); MASTER = AC.createGain(); MASTER.gain.value = 0.35; MASTER.connect(AC.destination); } if (AC.state === 'suspended') AC.resume(); return AC; }
function tone(type, f0, f1, dur, peak, at = 0) {
  const c = audio(), t = c.currentTime + at, o = c.createOscillator(); o.type = type;
  o.frequency.setValueAtTime(f0, t); if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
  const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(MASTER); o.start(t); o.stop(t + dur + 0.02);
}
function chiado(dur, peak, { tipo = 'bandpass', f = 3000, f1, q = 1 } = {}, at = 0) {
  const c = audio(), t = c.currentTime + at, n = Math.ceil(c.sampleRate * dur), b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  const s = c.createBufferSource(); s.buffer = b; const fl = c.createBiquadFilter(); fl.type = tipo; fl.frequency.setValueAtTime(f, t);
  if (f1) fl.frequency.exponentialRampToValueAtTime(f1, t + dur); fl.Q.value = q;
  const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + 0.003); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  s.connect(fl).connect(g).connect(MASTER); s.start(t); s.stop(t + dur + 0.02);
}
const SONS = {
  bipe: () => tone('square', 2950, 0, 0.11, 0.12),
  clique: () => { chiado(0.025, 0.5, { tipo: 'highpass', f: 3500 }); tone('sine', 1800, 900, 0.03, 0.2); },
  impressora: () => { for (let i = 0; i < 10; i++) chiado(0.022, 0.35, { f: 2400 + (i % 2) * 600, q: 3 }, i * 0.03); },
  tum: () => { tone('sine', 130, 38, 0.38, 0.9); chiado(0.09, 0.4, { tipo: 'lowpass', f: 700 }); },
  plim: () => { tone('triangle', 1568, 0, 0.5, 0.25); tone('triangle', 2093, 0, 0.7, 0.2, 0.08); },
  caneta: () => { for (let i = 0; i < 14; i++) chiado(0.03, 0.18 + Math.random() * 0.12, { f: 2200 + Math.random() * 1800, q: 1.5 }, i * 0.028); },
  rangido: () => { tone('sine', 1150, 1750, 0.18, 0.12); tone('sine', 1180, 1700, 0.18, 0.06, 0.01); },
  pop: () => tone('sine', 900, 180, 0.08, 0.6),
  boing: () => {
    const c = audio(), t = c.currentTime, o = c.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(160, t); o.frequency.exponentialRampToValueAtTime(420, t + 0.09); o.frequency.exponentialRampToValueAtTime(240, t + 0.45);
    const l = c.createOscillator(); l.frequency.value = 16; const lg = c.createGain(); lg.gain.value = 35; l.connect(lg).connect(o.frequency);
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.5, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
    o.connect(g).connect(MASTER); o.start(t); l.start(t); o.stop(t + 0.52); l.stop(t + 0.52);
  },
  pagina: () => chiado(0.28, 0.3, { f: 700, f1: 3800, q: 0.7 }),
  blip: () => tone('square', 880, 0, 0.035, 0.06),
  moeda: () => { tone('square', 988, 0, 0.07, 0.1); tone('square', 1319, 0, 0.25, 0.1, 0.07); },
  hit: () => { chiado(0.2, 0.6, { tipo: 'lowpass', f: 2000, f1: 300 }); tone('square', 170, 55, 0.2, 0.2); },
  powerup: () => [523, 659, 784, 1047, 1319].forEach((f, i) => tone('square', f, 0, 0.06, 0.08, i * 0.05)),
  powerdown: () => [784, 659, 523, 392, 262].forEach((f, i) => tone('square', f, 0, 0.07, 0.08, i * 0.06)),
  selecao: () => { tone('square', 1320, 0, 0.035, 0.08); tone('square', 1760, 0, 0.05, 0.08, 0.04); },
};
function tocar(n) { try { if (SONS[n]) SONS[n](); } catch (e) { console.warn(e); } }

// ================= DIRECAO A: Tabela Nutricional =================
const DA = {
  id: 'A', titulo: 'TABELA NUTRICIONAL', tSize: 104, tY: 58, sY: 172,
  subt: 'Seco, irônico e factual: a pira da magreza lida como rótulo de embalagem.',
  c: { fundo: '#F4F1EA', principal: '#141414', destaque: '#FFCF1A', texto: '#FFFFFF', apoio: '#2B4EFF' },
  roles: [['fundo', 'FUNDO', 'cartelas e caixas'], ['principal', 'PRINCIPAL', 'filetes, contornos, títulos'], ['destaque', 'DESTAQUE', 'palavra-chave e impacto'], ['texto', 'TEXTO', 'letras sobre tarja preta'], ['apoio', 'APOIO', 'números, dados, setas']],
  fT: s => `900 extra-condensed ${s}px "Archivo"`, fL: s => `800 ${s}px "Inter Tight"`, fN: s => `500 ${s}px "Inter Tight"`,
  fontes: [['VERDADE Nº 7', 'Archivo Extra Condensed Black · licença OFL', 84], ['SAÚDE IMPORTA', 'Inter Tight ExtraBold · licença OFL', 46]],
  txt1: '#141414', txt2: '#4A4A4A', fontC1: '#141414',
  mov: ['Entra deslizando de trás de um filete (máscara), ease-out expo em 6 a 8 quadros. Nada quica.',
    'Linhas se desenham da esquerda para a direita; números contam como odômetro.',
    'Palavra-chave: “soco” de zoom a 108% + tremida curta de 3 quadros.',
    'Sai com corte seco ou máscara para baixo. Ritmo rápido, pausas firmes.'],
  legenda: 'Legenda: faixa do peito (cobre a legenda antiga) · caixa papel com borda de 8 px · CAIXA ALTA · palavra-chave em tarja amarela.',
  transNome: 'persiana de tabela',
  sons: [['bipe', 'Bipe de leitor de código'], ['clique', 'Clique seco de régua'], ['impressora', 'Impressora de cupom'], ['tum', 'Tum grave (impacto)'], ['plim', 'Plim de caixa registradora']],
  seg: 14.2, L: 4.9, TR: 0.4, hero: 4.45,
  words: mkWords('A internet convenceu vocês que ser magra é o que importa e ter saúde é meio irrelevante', .15, .245, [3, 2, 2, 4, 3, 3], [6, 13, 16]),
  ev() { const T = i => this.T(i); return [{ t: 0.03, s: 'clique' }, { t: T(1), s: 'bipe' }, { t: T(1) + 1.3, s: 'plim' }, { t: T(6), s: 'impressora' }, { t: T(13), s: 'clique' }, { t: T(16), s: 'tum' }, { t: this.L - this.TR, s: 'impressora' }]; },

  bg(g) { const c = this.c; g.fillStyle = c.fundo; g.fillRect(0, 0, W, H); g.strokeStyle = c.principal; g.lineWidth = 10; g.strokeRect(14, 14, W - 28, H - 28); },
  rule(g, x, y, w, k) { g.fillStyle = this.c.principal; g.fillRect(x, y, w, k === 'grossa' ? 14 : 4); },
  label(g, t, x, y, w) { g.fillStyle = this.c.principal; g.font = this.fT(38); g.fillText(t, x, y); g.fillRect(x, y + 42, w, 6); return g.measureText(t).width; },
  chip(g, x, y, s, hex) { g.fillStyle = hex; g.fillRect(x, y, s, s); g.lineWidth = 4; g.strokeStyle = this.c.principal; g.strokeRect(x + 2, y + 2, s - 4, s - 4); },
  panel(g, x, y, w, h) { g.fillStyle = this.c.fundo; g.fillRect(x, y, w, h); g.lineWidth = 4; g.strokeStyle = this.c.principal; g.strokeRect(x + 2, y + 2, w - 4, h - 4); },
  frame(g) { g.lineWidth = 8; g.strokeStyle = this.c.principal; g.strokeRect(MX - 4, MY - 4, MW + 8, MH + 8); },
  icons(g) {
    const c = this.c, cy = 1048;
    let cx = 658; rrect(g, cx - 26, cy - 42, 52, 84, 8); g.fillStyle = c.fundo; g.fill(); g.lineWidth = 7; g.strokeStyle = c.principal; g.stroke(); g.fillStyle = c.apoio; g.fillRect(cx - 17, cy - 30, 34, 52);
    cx = 766; heartGeo(g, cx, cy - 6, 76); g.fillStyle = c.destaque; g.fill(); g.lineWidth = 6; g.strokeStyle = c.principal; g.stroke();
    cx = 874; g.fillStyle = c.principal; g.fillRect(cx - 40, cy - 40, 7, 80); g.fillRect(cx - 40, cy + 33, 82, 7); g.fillRect(cx - 24, cy + 5, 16, 28); g.fillRect(cx - 2, cy - 15, 16, 48); g.fillStyle = c.apoio; g.fillRect(cx + 20, cy - 35, 16, 68);
    cx = 982; g.fillStyle = c.fundo; g.fillRect(cx - 40, cy - 34, 80, 54); g.lineWidth = 7; g.strokeStyle = c.principal; g.strokeRect(cx - 40, cy - 34, 80, 54);
    g.beginPath(); g.moveTo(cx - 22, cy + 20); g.lineTo(cx - 26, cy + 42); g.lineTo(cx - 4, cy + 20); g.closePath(); g.fillStyle = c.principal; g.fill();
    [-18, 0, 18].forEach(dx => g.fillRect(cx + dx - 5, cy - 12, 10, 10));
  },
  sig(g) {
    const c = this.c, x = 610, y = 1100, w = 430, h = 90;
    g.fillStyle = c.principal; g.fillRect(x, y, w, h);
    g.strokeStyle = c.texto; g.lineWidth = 6; g.beginPath(); g.arc(x + 44, y + 40, 20, 0, Math.PI * 2); g.stroke();
    g.lineWidth = 9; g.beginPath(); g.moveTo(x + 58, y + 54); g.lineTo(x + 74, y + 72); g.stroke();
    g.fillStyle = c.texto; g.font = this.fL(22); g.fillText('ALTO EM', x + 96, y + 10);
    fit(g, this.fT, 'PRESSÃO ESTÉTICA', 46, w - 112); g.fillText('PRESSÃO ESTÉTICA', x + 96, y + 36);
  },
  curve(g, x, y, w, h) {
    const c = this.c; this.panel(g, x, y, w, h); const px = x + 30, py = y + 26, pw = w - 60, ph = h - 96;
    g.fillStyle = c.principal; g.fillRect(px, py + ph, pw, 3); g.fillRect(px, py, 3, ph);
    g.beginPath(); for (let i = 0; i <= 60; i++) { const u = i / 60, X = px + u * pw, Y = py + ph - E.outExpo(u) * ph; i ? g.lineTo(X, Y) : g.moveTo(X, Y); }
    g.lineWidth = 6; g.strokeStyle = c.principal; g.stroke();
    g.fillStyle = c.apoio; g.fillRect(px - 6, py + ph - 6, 12, 12); g.fillRect(px + pw - 6, py - 6, 12, 12);
    g.fillStyle = c.principal; g.font = this.fL(20); g.fillText('EASE-OUT EXPO', x + 20, y + h - 56); g.font = this.fN(18); g.fillText('6–8 quadros · sem quique', x + 20, y + h - 30);
  },
  trans(g, old, nw, p) {
    const c = this.c, n = 6, bh = H / n;
    if (p < .5) {
      g.drawImage(old, 0, 0); const q0 = p / .5;
      for (let i = 0; i < n; i++) { const q = E.outExpo(clamp(q0 * 1.5 - i * 0.1)); g.fillStyle = c.principal; g.fillRect(0, i * bh, W * q, bh + 1); if (q > 0 && q < 1) { g.fillStyle = c.destaque; g.fillRect(W * q - 12, i * bh, 12, bh + 1); } }
    } else {
      g.drawImage(nw, 0, 0); const q0 = (p - .5) / .5;
      for (let i = 0; i < n; i++) { const q = E.outExpo(clamp(q0 * 1.5 - i * 0.1)); g.fillStyle = c.principal; g.fillRect(W * q, i * bh, W * (1 - q), bh + 1); if (q > 0 && q < 1) { g.fillStyle = c.destaque; g.fillRect(W * q, i * bh, 12, bh + 1); } }
    }
  },
  camera(t) { const tI = this.T(16); let s = 1; if (t >= tI) s = 1 + 0.08 * (1 - E.outCubic(prog(t, tI, 0.45))); const [dx, dy] = shake(t, tI, 0.1, 16, 30); return { s, dx, dy }; },
  caption(g, t) {
    const c = this.c; g.fillStyle = c.fundo; g.fillRect(160, 1145, 760, 215); g.lineWidth = 8; g.strokeStyle = c.principal; g.strokeRect(164, 1149, 752, 207);
    const ws = chunkAt(this.words, t); if (!ws) return;
    const Lt = layout(g, ws, this.fL, [84, 76, 68, 60], 680, true), lh = Lt.s * 1.1, y0 = 1252 - Lt.lines.length * lh / 2;
    Lt.lines.forEach((line, li) => {
      let x = 540 - lineW(line, Lt.sp) / 2; const y = y0 + li * lh;
      line.forEach(w => {
        if (t >= w.t) {
          const a = E.outExpo(prog(t, w.t, 0.22));
          g.save(); g.beginPath(); g.rect(x - 12, y - 4, w.ww + 24, lh + 4); g.clip();
          if (w.k) { g.fillStyle = c.destaque; g.fillRect(x - 8, y + Lt.s * 0.04, (w.ww + 16) * E.outExpo(prog(t, w.t, 0.16)), Lt.s * 1.0); }
          g.fillStyle = c.principal; g.font = this.fL(Lt.s); g.fillText(w.txt, x, y + (1 - a) * lh); g.restore();
        }
        x += w.ww + Lt.sp;
      });
    });
  },
  overlay(g, t) {
    const c = this.c, T = i => this.T(i);
    // contador de verdades
    g.fillStyle = c.principal; g.fillRect(60, 340, 400 * E.outExpo(prog(t, 0, 0.2)), 8);
    const a = E.outExpo(prog(t, 0.08, 0.35));
    if (a > 0) {
      g.font = this.fT(54); const tw = g.measureText('VERDADE Nº 02/07').width + 40;
      g.save(); g.beginPath(); g.rect(40, 240, 480, 100); g.clip(); const y = 268 + (1 - a) * 80;
      g.fillStyle = c.principal; g.fillRect(60, y, tw, 66); g.fillStyle = c.texto; g.fillText('VERDADE Nº 02/07', 80, y + 6); g.restore();
    }
    // "internet": celular sobe de tras do filete
    const t1 = T(1);
    if (t >= t1) {
      g.fillStyle = c.principal; g.fillRect(60, 812, 236 * E.outExpo(prog(t, t1, 0.15)), 8);
      const ph = E.outExpo(prog(t, t1 + 0.06, 0.35));
      g.save(); g.beginPath(); g.rect(40, 300, 300, 512); g.clip(); g.translate(0, (1 - ph) * 400);
      rrect(g, 76, 452, 200, 350, 26); g.fillStyle = c.fundo; g.fill(); g.lineWidth = 10; g.strokeStyle = c.principal; g.stroke();
      g.fillStyle = c.apoio; g.fillRect(94, 494, 164, 272); g.fillStyle = c.principal; g.fillRect(151, 470, 50, 8);
      heartGeo(g, 176, 580, 70); g.fillStyle = c.texto; g.fill();
      const n = Math.round(9874 * E.outCubic(prog(t, t1 + 0.3, 1.0)));
      g.textAlign = 'center'; g.font = this.fL(42); g.fillText(n.toLocaleString('pt-BR'), 176, 650); g.font = this.fN(22); g.fillText('curtidas', 176, 702); g.textAlign = 'left';
      g.restore();
    }
    // "magra": tabela nutricional
    const t6 = T(6);
    if (t >= t6) {
      const x = 580, y = 856, w = 420, h = 254;
      g.fillStyle = c.principal; g.fillRect(x, y, w * E.outExpo(prog(t, t6, 0.15)), 14);
      const op = E.outExpo(prog(t, t6 + 0.08, 0.35));
      if (op > 0) {
        g.save(); g.beginPath(); g.rect(x, y + 14, w, (h - 14) * op); g.clip();
        g.fillStyle = c.fundo; g.fillRect(x, y, w, h); g.lineWidth = 8; g.strokeStyle = c.principal; g.strokeRect(x + 4, y + 4, w - 8, h - 8);
        g.fillStyle = c.principal; g.font = this.fT(46); g.fillText('PORÇÃO: 1 FEED', x + 22, y + 24); g.fillRect(x + 12, y + 80, w - 24, 10);
        g.font = this.fL(36); g.fillText('MAGREZA', x + 22, y + 102); g.textAlign = 'right'; g.fillStyle = c.apoio; g.fillText('100%', x + w - 22, y + 102); g.textAlign = 'left';
        g.fillStyle = c.principal; g.fillRect(x + 12, y + 158, w - 24, 4);
        g.restore();
        const t13 = T(13);
        if (t >= t13) {
          const r = E.outExpo(prog(t, t13, 0.25));
          g.save(); g.beginPath(); g.rect(x + 8, y + 166, w - 16, 80); g.clip(); const yy = y + 178 + (1 - r) * 70;
          g.fillStyle = c.principal; g.font = this.fL(36); g.fillText('SAÚDE', x + 22, yy);
          const t16 = T(16), v = t < t16 ? 100 : Math.round(100 * (1 - E.outExpo(prog(t, t16, 0.35)))), txt = v + '%', vw = g.measureText(txt).width;
          if (t >= t16 + 0.3) { g.fillStyle = c.destaque; g.fillRect(x + w - 32 - vw, yy - 4, (vw + 20) * E.outExpo(prog(t, t16 + 0.3, 0.15)), 46); }
          g.textAlign = 'right'; g.fillStyle = v === 0 ? c.principal : c.apoio; g.fillText(txt, x + w - 22, yy); g.textAlign = 'left'; g.restore();
        }
      }
    }
  },
};

// ================= DIRECAO B: Correcao a Caneta =================
const DB = {
  id: 'B', titulo: 'Correção a Caneta', tSize: 88, tY: 58, sY: 172,
  subt: 'Debochada e humana: a nutri pegou a caneta e corrigiu a internet ao vivo.',
  // paleta escolhida: Ameixa (a primeira versao era azul Bic #1F3FBF + amarelo #FFE14D + verde #19A974)
  c: { fundo: '#FFF8F1', principal: '#6E2A6B', destaque: '#FFB48F', texto: '#2A1A2B', apoio: '#D9467A' },
  roles: [['fundo', 'FUNDO', 'papel de caderno'], ['principal', 'PRINCIPAL', 'tinta ameixa, rabiscos'], ['destaque', 'DESTAQUE', 'marca-texto pêssego'], ['texto', 'TEXTO', 'legenda e anotações'], ['apoio', 'APOIO', 'o que é verdade (✓)']],
  fT: s => `${s}px "Permanent Marker"`, fL: s => `800 ${s}px "Shantell Sans"`, fN: s => `400 ${s}px "Shantell Sans"`,
  fontes: [['Verdade!', 'Permanent Marker · licença Apache 2.0', 80], ['sem medo de pão', 'Shantell Sans ExtraBold · licença OFL', 46]],
  txt1: '#2A1A2B', txt2: '#7A6377', fontC1: '#6E2A6B',
  mov: ['Traços se desenham na velocidade da mão; objetos entram com passada (back-out) e esticam.',
    'Linhas “fervem”: redesenhadas a cada 2 quadros (12 fps), como animação feita à mão.',
    'Palavra-chave: círculo rabiscado + tremida de 4 quadros. Mentira é riscada na hora.',
    'Sai como borracha ou com um “puf”. Ritmo solto, levemente irregular.'],
  legenda: 'Legenda: tira de caderno torta (−1,5°) com contorno ameixa tremido · minúsculas · palavra-chave com marca-texto passando por trás.',
  transNome: 'rabisco que cobre e revela',
  sons: [['caneta', 'Caneta riscando'], ['rangido', 'Rangido de marcador'], ['pop', 'Pop de bolha'], ['boing', 'Boing de mola'], ['pagina', 'Virar página']],
  seg: 18.6, L: 7.1, TR: 0.45, hero: 6.75,
  words: mkWords('alimentação limpa é o nome que vocês estão dando para quem tem medo de carboidrato', .3, .42, [2, 4, 3, 3, 3], [1, 14]),
  ev() { const T = i => this.T(i); return [{ t: 0.03, s: 'caneta' }, { t: T(0), s: 'caneta' }, { t: T(4), s: 'caneta' }, { t: T(10), s: 'rangido' }, { t: T(12), s: 'pop' }, { t: T(14), s: 'caneta' }, { t: T(14) + 0.05, s: 'boing' }, { t: this.L - this.TR, s: 'pagina' }]; },
  boil(t) { return Math.floor(t * 12) % 3; },
  pauta() { return hexA(this.c.principal, 0.16); },   // linhas do caderno derivadas da tinta

  bg(g) {
    const c = this.c; g.fillStyle = c.fundo; g.fillRect(0, 0, W, H);
    g.strokeStyle = this.pauta(); g.lineWidth = 2; for (let y = 258; y < H; y += 54) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.strokeStyle = hexA(this.c.destaque, 0.8); g.beginPath(); g.moveTo(26, 0); g.lineTo(26, H); g.stroke();
  },
  rule(g, x, y, w, k) { hand(g, [[x, y + 6], [x + w, y + 4]], { seed: y, amp: 2, w: k === 'grossa' ? 7 : 4, color: this.c.principal, step: 30 }); },
  label(g, t, x, y, w) { g.fillStyle = this.c.principal; g.font = this.fT(36); g.fillText(t, x, y); const tw = g.measureText(t).width; hand(g, [[x, y + 46], [x + tw + 20, y + 44]], { seed: x + y, amp: 1.5, w: 5, color: this.c.principal, step: 20 }); return tw; },
  chip(g, x, y, s, hex) { g.fillStyle = hex; g.fillRect(x + 3, y + 3, s - 6, s - 6); hand(g, rectPts(x, y, s, s), { seed: y, amp: 2, w: 4, color: this.c.principal, closed: true, step: 14 }); },
  panel(g, x, y, w, h) { g.fillStyle = this.c.fundo; g.fillRect(x, y, w, h); hand(g, rectPts(x, y, w, h), { seed: x * 7 + y, amp: 2.2, w: 4, color: this.c.principal, closed: true, step: 16 }); },
  frame(g) { hand(g, rectPts(MX - 6, MY - 6, MW + 12, MH + 12), { seed: 5, amp: 2.5, w: 7, color: this.c.principal, closed: true, step: 18 }); },
  icons(g) {
    const c = this.c, cy = 1048, o = { amp: 2, w: 6, color: c.principal };
    let cx = 658; g.fillStyle = c.destaque; g.fillRect(cx - 20, cy - 28, 44, 50); hand(g, rectPts(cx - 26, cy - 42, 52, 84), { ...o, closed: true, seed: 3 }); hand(g, [[cx - 8, cy + 32], [cx + 8, cy + 32]], { ...o, seed: 4 });
    cx = 766; const hp = []; for (let i = 0; i <= 40; i++) { const a = i / 40 * Math.PI * 2, X = 16 * Math.pow(Math.sin(a), 3), Y = -(13 * Math.cos(a) - 5 * Math.cos(2 * a) - 2 * Math.cos(3 * a) - Math.cos(4 * a)); hp.push([cx + X * 2.4, cy + Y * 2.4 - 4]); }
    g.fillStyle = c.destaque; g.beginPath(); hp.forEach(([X, Y], i) => i ? g.lineTo(X + 6, Y + 5) : g.moveTo(X + 6, Y + 5)); g.fill(); hand(g, hp, { ...o, seed: 6 });
    cx = 874; hand(g, [[cx - 40, cy - 40], [cx - 40, cy + 36], [cx + 42, cy + 36]], { ...o, seed: 8 }); hand(g, [[cx - 30, cy - 26], [cx - 8, cy - 6], [cx + 8, cy - 14], [cx + 34, cy + 20]], { ...o, seed: 9 }); arrowHead(g, [cx + 8, cy - 14], [cx + 34, cy + 20], 16, { ...o, seed: 10 });
    cx = 982; hand(g, ellPts(cx, cy - 8, 42, 30, 1, 0, 30), { ...o, seed: 11 }); hand(g, [[cx - 18, cy + 16], [cx - 30, cy + 40], [cx - 2, cy + 20]], { ...o, seed: 12 });
  },
  sig(g) {
    const c = this.c; g.fillStyle = c.texto; g.font = this.fL(38); g.fillText('corpo perfeito', 614, 1100); const w = g.measureText('corpo perfeito').width;
    hand(g, [[606, 1130], [624 + w, 1120]], { seed: 21, amp: 1.5, w: 6, color: c.principal });
    hand(g, [[616, 1172], [676, 1170]], { seed: 22, amp: 1.2, w: 5, color: c.principal }); arrowHead(g, [616, 1172], [676, 1170], 16, { seed: 23, amp: 1, w: 5, color: c.principal });
    g.fillStyle = c.apoio; g.font = this.fT(40); g.fillText('é tudo ângulo', 690, 1146); const w2 = g.measureText('é tudo ângulo').width;
    hand(g, [[704 + w2, 1170], [716 + w2, 1184], [742 + w2, 1146]], { seed: 24, amp: 1, w: 6, color: c.apoio });
  },
  curve(g, x, y, w, h) {
    const c = this.c; this.panel(g, x, y, w, h); const px = x + 30, py = y + 34, pw = w - 60, ph = h - 100;
    hand(g, [[px, py - 8], [px, py + ph], [px + pw + 6, py + ph]], { seed: 31, amp: 1.5, w: 4, color: c.texto });
    const pts = []; for (let i = 0; i <= 40; i++) { const u = i / 40; pts.push([px + u * pw, py + ph - E.back(u, 2.2) * ph * 0.8]); }
    hand(g, pts, { seed: 32, amp: 2, w: 6, color: c.principal, step: 10 });
    g.fillStyle = c.texto; g.font = this.fL(21); g.fillText('back-out + passada', x + 18, y + h - 58); g.font = this.fN(19); g.fillText('12 fps nos desenhos', x + 18, y + h - 32);
  },
  trans(g, old, nw, p) {
    const c = this.c;
    if (!this.sp) { const pts = []; let y = -120, left = true; while (y < H + 200) { pts.push([left ? -160 : W + 160, y]); y += 150; left = !left; } this.sp = jitter(subdiv(pts, 40), 77, 10); }
    g.save(); g.lineCap = 'round'; g.lineJoin = 'round'; g.strokeStyle = c.principal; g.lineWidth = 310;
    if (p < .5) { g.drawImage(old, 0, 0); smooth(g, cutPts(this.sp, 0, E.inOut(p / .5))); }
    else { g.drawImage(nw, 0, 0); smooth(g, cutPts(this.sp, E.inOut((p - .5) / .5), 1)); }
    g.restore();
  },
  camera(t) { const tI = this.T(14); let s = 1; if (t >= tI) { const u = t - tI; s = 1 + 0.05 * Math.exp(-7 * u) * Math.cos(18 * u); } const [dx, dy] = shake(t, tI, 0.17, 11, 12); return { s, dx, dy }; },
  caption(g, t) {
    const c = this.c, b = this.boil(t);
    g.save(); g.translate(540, 1252); g.rotate(-1.5 * Math.PI / 180);
    g.fillStyle = c.fundo; g.fillRect(-392, -110, 784, 220);
    g.strokeStyle = this.pauta(); g.lineWidth = 2; for (let y = -60; y < 110; y += 50) { g.beginPath(); g.moveTo(-392, y); g.lineTo(392, y); g.stroke(); }
    hand(g, rectPts(-392, -110, 784, 220), { seed: 40 + b, amp: 2.6, w: 6, color: c.principal, closed: true, step: 16 });
    const ws = chunkAt(this.words, t);
    if (ws) {
      const Lt = layout(g, ws, this.fL, [78, 70, 62, 56], 700, false), lh = Lt.s * 1.12, y0 = -Lt.lines.length * lh / 2;
      Lt.lines.forEach((line, li) => {
        let x = -lineW(line, Lt.sp) / 2; const y = y0 + li * lh;
        line.forEach(w => {
          if (t >= w.t) {
            const a = prog(t, w.t, 0.25);
            if (w.k) { g.save(); g.globalCompositeOperation = 'multiply'; g.fillStyle = c.destaque; g.fillRect(x - 11, y + Lt.s * 0.2, (w.ww + 22) * E.inOut(prog(t, w.t + 0.04, 0.24)), Lt.s * 0.86); g.restore(); }
            const sc = 0.4 + 0.6 * E.back(a, 2.6), r = rng(w.i * 13 + 7), rot = (r() * 2 - 1) * 2.5 * Math.PI / 180;
            g.save(); g.translate(x + w.ww / 2, y + lh / 2); g.rotate(rot); g.scale(sc, sc); g.globalAlpha = clamp(a * 5);
            g.fillStyle = c.texto; g.font = this.fL(Lt.s); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(w.txt, 0, 0); g.restore();
          }
          x += w.ww + Lt.sp;
        });
      });
    }
    g.restore();
  },
  overlay(g, t) {
    const c = this.c, T = i => this.T(i), b = this.boil(t);
    // contador "verdade #3" escrito a mao
    g.font = this.fT(56); const ct = 'verdade #3', cw = g.measureText(ct).width, wr = E.inOut(prog(t, 0, 0.45));
    if (wr > 0) { g.save(); g.beginPath(); g.rect(50, 250, (cw + 40) * wr, 110); g.clip(); g.lineWidth = 12; g.lineJoin = 'round'; g.strokeStyle = c.fundo; g.strokeText(ct, 70, 272); g.fillStyle = c.principal; g.fillText(ct, 70, 272); g.restore(); }
    hand(g, ellPts(70 + cw - 17, 306, 34, 38, 1.15, -2.4, 30), { seed: 50 + b, amp: 2, w: 5, color: c.principal, f1: E.inOut(prog(t, 0.45, 0.3)) });
    // "alimentacao limpa" escrito e depois riscado
    const t0 = T(0);
    if (t >= t0) {
      g.save(); g.translate(800, 300); g.rotate(-4 * Math.PI / 180); g.font = this.fT(64); g.textAlign = 'center';
      const l1 = '“alimentação', l2 = 'limpa”', w1 = g.measureText(l1).width, wr2 = E.inOut(prog(t, t0, 0.75));
      const w2 = g.measureText(l2).width;
      g.save(); g.beginPath(); g.rect(-w1 / 2 - 30, -70, (w1 + 60) * wr2, 180); g.clip();
      g.lineWidth = 12; g.lineJoin = 'round'; g.strokeStyle = c.fundo; g.strokeText(l1, 0, -50); g.strokeText(l2, 0, 24);
      g.fillStyle = c.principal; g.fillText(l1, 0, -50); g.fillText(l2, 0, 24); g.restore();
      // risca cada linha com um traco (continua legivel o que foi riscado)
      const t4 = T(4);
      if (t >= t4) {
        hand(g, [[-w1 / 2 - 16, -14], [w1 / 2 + 16, -24]], { seed: 60 + b, amp: 2.5, w: 9, color: c.principal, f1: E.inOut(prog(t, t4, 0.22)) });
        hand(g, [[-w2 / 2 - 16, 56], [w2 / 2 + 16, 48]], { seed: 61 + b, amp: 2.5, w: 9, color: c.principal, f1: E.inOut(prog(t, t4 + 0.18, 0.2)) });
      }
      g.restore();
    }
    // seta descendo ate o pao
    const t10 = T(10);
    if (t >= t10) {
      const ap = bezPts([945, 392], [1010, 560], [990, 720], [878, 832]), f = E.inOut(prog(t, t10, 0.45));
      hand(g, ap, { seed: 70 + b, amp: 2, w: 18, color: c.fundo, f1: f }); hand(g, ap, { seed: 70 + b, amp: 2, w: 8, color: c.principal, f1: f });
      if (f >= 1) arrowHead(g, ap[ap.length - 4], ap[ap.length - 1], 34, { seed: 71 + b, amp: 1.5, w: 8, color: c.principal });
    }
    // "medo": pao assustado tremendo
    const t12 = T(12);
    if (t >= t12) {
      const sc = E.back(prog(t, t12, 0.3), 2.4), tr = t >= t12 + 0.3 ? Math.sin(Math.floor(t * 12) * 2.1) * 5 : 0;
      g.save(); g.translate(790 + tr, 960); g.scale(sc, sc); this.pao(g, b, t - t12); g.restore();
    }
    // "carboidrato": circulo rabiscado
    const t14 = T(14);
    if (t >= t14) hand(g, ellPts(790, 950, 170, 145, 1.12, -2.6, 40), { seed: 80 + b, amp: 4, w: 9, color: c.principal, f1: E.inOut(prog(t, t14, 0.35)) });
  },
  pao(g, b, u) {
    const c = this.c, pts = [[-95, 85], [-95, -24]];
    for (let i = 0; i <= 24; i++) { const a = Math.PI + i / 24 * Math.PI; pts.push([Math.cos(a) * 112, -40 + Math.sin(a) * 72]); }
    pts.push([95, -24], [95, 85]);
    g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fillStyle = c.fundo; g.fill();
    g.save(); g.globalAlpha = .55; g.fillStyle = c.destaque; g.fill(); g.restore();
    hand(g, pts, { seed: 90 + b, amp: 2.5, w: 8, color: c.principal, closed: true, step: 14 });
    [[-36, -6], [36, -6]].forEach(([x, y]) => { g.fillStyle = c.principal; g.beginPath(); g.arc(x, y, 13, 0, Math.PI * 2); g.fill(); g.fillStyle = c.fundo; g.beginPath(); g.arc(x + 4, y - 4, 4, 0, Math.PI * 2); g.fill(); });
    hand(g, [[-54, -40], [-22, -30]], { seed: 91 + b, amp: 1, w: 6, color: c.principal }); hand(g, [[54, -40], [22, -30]], { seed: 92 + b, amp: 1, w: 6, color: c.principal });
    hand(g, [[-22, 40], [-11, 32], [0, 40], [11, 32], [22, 40]], { seed: 93 + b, amp: 1.5, w: 6, color: c.principal, step: 6 });
    if (u > 0.3) [[-128, -60], [120, -84]].forEach(([x, y], k) => {
      const d = clamp((u - 0.3 - k * 0.1) / 0.2); if (d <= 0) return;
      g.save(); g.translate(x, y + ((u * 12 | 0) % 3) * 2); g.scale(d, d); g.beginPath(); g.moveTo(0, -20); g.quadraticCurveTo(14, 4, 0, 10); g.quadraticCurveTo(-14, 4, 0, -20);
      g.fillStyle = c.fundo; g.fill(); g.lineWidth = 5; g.strokeStyle = c.principal; g.stroke(); g.restore();
    });
  },
};

// ================= DIRECAO C: Modo Dificil =================
const DC = {
  id: 'C', titulo: 'MODO DIFÍCIL', tSize: 128, tY: 48, sY: 168, quant: 15,
  subt: 'Divertida e sarcástica: a pira da magreza vira um jogo impossível de zerar.',
  c: { fundo: '#1E2140', principal: '#FFF3D6', destaque: '#FFC233', texto: '#FFFFFF', apoio: '#FF6B5E' },
  roles: [['fundo', 'FUNDO', 'caixas de diálogo e HUD'], ['principal', 'PRINCIPAL', 'bordas, pixels, ícones'], ['destaque', 'DESTAQUE', 'palavra-chave e moedas'], ['texto', 'TEXTO', 'legenda'], ['apoio', 'APOIO', 'vida, dano e alerta']],
  // Jersey e condensada e de olho pequeno: legenda e texto corrido ganham 25% de tamanho para ler igual as outras
  fT: s => `${s}px "Jersey 25"`, fL: s => `${Math.round(s * 1.25)}px "Jersey 15"`, fN: s => `${Math.round(s * 1.25)}px "Jersey 15"`,
  fontes: [['FASE 4', 'Jersey 25 · licença OFL', 84], ['fazer igual?', 'Jersey 15 · licença OFL', 52]],
  txt1: '#FFF3D6', txt2: '#A9AEDB', fontC1: '#FFC233', hdr: '#FFC233',
  mov: ['Tudo anda na grade de 6 px e a 15 fps: movimento em degraus, como jogo de 16 bits.',
    'Entra piscando 3 vezes (spawn) ou cai com quique de 3 quadros.',
    'Palavra-chave: “hit”, com flash de 1 quadro, tremida de 6 quadros e número de dano subindo.',
    'Barras de energia drenam, moedas sobem; sai com um “poof” de pixels.'],
  legenda: 'Legenda: caixa de diálogo de RPG com etiqueta NUTRI · cada palavra entra com um blip · palavra-chave em ouro · ▼ piscando no fim do bloco.',
  transNome: 'mosaico de pixels',
  sons: [['blip', 'Blip de texto'], ['moeda', 'Moeda'], ['hit', 'Hit 8-bit (impacto)'], ['powerup', 'Power-up / power-down'], ['selecao', 'Seleção de menu']],
  seg: 25.9, L: 9.0, TR: 0.45, hero: 8.25,
  words: mkWords('As influencers vendem rotinas absurdas, até mesmo com 3 atividades físicas por dia... e vocês acham que conseguem fazer igual tendo rotina CLT.', .2, .33, [3, 2, 3, 3, 2, 4, 3, 3], [4, 8, 22]),
  ev() {
    const T = i => this.T(i), e = [{ t: 0.03, s: 'selecao' }, { t: T(3), s: 'selecao' }];
    this.words.forEach((w, i) => { if (![3, 22].includes(i)) e.push({ t: w.t, s: 'blip' }); });
    [17, 18, 19].forEach(i => e.push({ t: T(i) + 0.02, s: 'moeda' }));
    e.push({ t: T(22), s: 'hit' }, { t: T(22) + 0.12, s: 'powerdown' }, { t: this.L - this.TR, s: 'selecao' });
    return e;
  },
  map() { const c = this.c; return { c: c.principal, g: c.destaque, r: c.apoio, w: c.texto, n: c.fundo }; },

  bg(g) { const c = this.c; g.fillStyle = c.fundo; g.fillRect(0, 0, W, H); g.fillStyle = '#191B37'; for (let y = 0; y < H; y += 12) for (let x = ((y / 12) % 2) * 12; x < W; x += 24) g.fillRect(x, y, 6, 6); },
  rule(g, x, y, w, k) { g.fillStyle = this.c.principal; const st = k === 'grossa' ? 12 : 18, ww = k === 'grossa' ? 12 : 6; for (let i = 0; i < w; i += st) g.fillRect(snap(x + i), snap(y), ww, 6); },
  label(g, t, x, y, w) { sprite(g, 'tri', x, y + 10, 3, { g: this.c.destaque }); g.fillStyle = this.c.destaque; g.font = this.fT(46); g.fillText(t, x + 24, y - 2); return g.measureText(t).width + 24; },
  chip(g, x, y, s, hex) { pxBox(g, x, y, s, s, { fill: hex, border: this.c.principal }); },
  panel(g, x, y, w, h) { pxBox(g, x, y, w, h, { fill: this.c.fundo, border: this.c.principal, shadow: '#0E1026' }); },
  frame(g) { const c = this.c; g.fillStyle = c.principal; g.fillRect(MX - 6, MY - 12, MW + 12, 6); g.fillRect(MX - 6, MY + MH + 6, MW + 12, 6); g.fillRect(MX - 12, MY - 6, 6, MH + 12); g.fillRect(MX + MW + 6, MY - 6, 6, MH + 12); },
  icons(g) { const m = this.map(); sprite(g, 'heart', 658 - 36, 1048 - 32, 8, m); sprite(g, 'phone', 766 - 28, 1048 - 44, 8, m); sprite(g, 'coin', 874 - 32, 1048 - 32, 8, m); sprite(g, 'dumbbell', 982 - 48, 1048 - 24, 8, m); },
  sig(g) {
    const c = this.c, m = this.map(); pxBox(g, 610, 1098, 430, 90, { fill: c.fundo, border: c.principal, shadow: '#0E1026' });
    g.fillStyle = c.principal; g.font = this.fT(36); g.fillText('SAÚDE', 634, 1124);
    for (let i = 0; i < 5; i++) sprite(g, i < 2 ? 'heart' : 'heartE', 732 + i * 48, 1124, 5, m);
    g.fillStyle = c.apoio; g.font = this.fT(50); g.fillText('-3', 982, 1114);
  },
  curve(g, x, y, w, h) {
    const c = this.c; this.panel(g, x, y, w, h); const px = x + 30, py = y + 30, pw = w - 60, ph = h - 100;
    g.fillStyle = c.principal; g.fillRect(snap(px), snap(py + ph), snap(pw), 6); g.fillRect(snap(px), snap(py), 6, snap(ph));
    const n = 10; for (let i = 0; i < n; i++) { const u = (i + 1) / n, v = Math.round(E.back(u, 1.7) * 6) / 6, bx = snap(px + 12 + i * (pw - 12) / n), bw = snap((pw - 12) / n) - 6, bh = snap(v * ph * 0.85); g.fillStyle = c.destaque; g.fillRect(bx, snap(py + ph) - bh, bw, bh); }
    g.fillStyle = c.principal; g.font = this.fT(30); g.fillText('DEGRAUS', x + 22, y + h - 66); g.font = this.fN(18); g.fillText('15 fps · grade de 6 px', x + 22, y + h - 34);
  },
  trans(g, old, nw, p) {
    const src = p < .5 ? old : nw, q = p < .5 ? E.inOut(p / .5) : 1 - E.inOut((p - .5) / .5), bs = Math.max(1, Math.round(q * 72 / 6) * 6);
    if (bs <= 1) { g.drawImage(src, 0, 0); return; }
    const w = Math.ceil(W / bs), h = Math.ceil(H / bs); if (!this.tiny) this.tiny = document.createElement('canvas');
    this.tiny.width = w; this.tiny.height = h; this.tiny.getContext('2d').drawImage(src, 0, 0, w, h);
    g.imageSmoothingEnabled = false; g.drawImage(this.tiny, 0, 0, w, h, 0, 0, w * bs, h * bs); g.imageSmoothingEnabled = true;
  },
  camera(t) { const [dx, dy] = shake(t, this.T(22), 0.27, 14, 15, 6); return { s: 1, dx, dy }; },
  flash(g, t) { const tI = this.T(22); if (t >= tI && t < tI + 1 / 15) { g.fillStyle = 'rgba(255,255,255,0.75)'; g.fillRect(0, 0, W, H); } },
  caption(g, t) {
    const c = this.c;
    pxBox(g, 150, 1140, 780, 222, { fill: c.fundo, border: c.principal, shadow: '#0E1026' });
    pxBox(g, 174, 1098, 180, 60, { fill: c.fundo, border: c.principal });
    g.fillStyle = c.destaque; g.font = this.fT(44); g.fillText('NUTRI', 210, 1104);
    const ws = chunkAt(this.words, t); if (!ws) return;
    const Lt = layout(g, ws, this.fL, [64, 58, 52], 690, false), lh = Lt.s * 1.3, y0 = 1254 - Lt.lines.length * lh / 2;
    Lt.lines.forEach((line, li) => {
      let x = 192; const y = y0 + li * lh;
      line.forEach(w => {
        if (t >= w.t) { const f = Math.floor((t - w.t) * 15); let dy = f < 1 ? 6 : 0; if (w.k) dy += [-12, -6, 0][Math.min(2, f)]; g.fillStyle = w.k ? c.destaque : c.texto; g.font = this.fL(Lt.s); g.fillText(w.txt, x, snap(y + dy)); }
        x += w.ww + Lt.sp;
      });
    });
    const last = ws[ws.length - 1]; if (t > last.t + 0.3 && Math.floor(t * 4) % 2 === 0) sprite(g, 'down', 882, 1320, 4, { g: c.destaque });
  },
  overlay(g, t) {
    const c = this.c, T = i => this.T(i), m = this.map();
    const blink = t0 => t >= t0 && (t > t0 + 0.27 || Math.floor((t - t0) * 15) % 2 === 0);
    // HUD: contador e energia
    if (blink(0)) { g.font = this.fT(54); const vw = g.measureText('VERDADE 4/7').width; pxBox(g, 54, 264, vw + 60, 72, { fill: c.fundo, border: c.principal, shadow: '#0E1026' }); g.fillStyle = c.principal; g.fillText('VERDADE 4/7', 82, 268); }
    const tI = T(22);
    if (blink(0.1)) {
      pxBox(g, 594, 264, 414, 72, { fill: c.fundo, border: c.principal, shadow: '#0E1026' }); g.fillStyle = c.destaque; g.font = this.fT(28); g.fillText('ENERGIA', 618, 270);
      let lv = 10; if (t >= tI) lv = Math.max(1, 10 - Math.floor(prog(t, tI, 0.5) * 10));
      for (let i = 0; i < 10; i++) { const low = lv <= 2; g.fillStyle = i < lv ? (low ? (Math.floor(t * 6) % 2 ? c.apoio : c.principal) : c.destaque) : '#34385F'; g.fillRect(618 + i * 36, 306, 30, 18); }
    }
    if (t >= tI && t < tI + 1.0) { const u = prog(t, tI, 1.0); g.globalAlpha = u > 0.7 ? 1 - (u - 0.7) / 0.3 : 1; g.fillStyle = c.apoio; g.font = this.fT(64); g.fillText('-90', 880, snap(350 - u * 60)); g.globalAlpha = 1; }
    // "rotinas": painel de missoes
    const t3 = T(3);
    if (blink(t3)) {
      const x = 60, y = 840; pxBox(g, x, y, 450, 246, { fill: c.fundo, border: c.principal, shadow: '#0E1026' });
      g.fillStyle = c.destaque; g.font = this.fT(40); g.fillText('MISSÕES DO DIA', x + 30, y + 16);
      ['CORRIDA 5H', 'ACADEMIA', 'PILATES'].forEach((it, i) => {
        const ti = T(8 + i); if (t < ti) return;
        const f = Math.min(3, Math.floor((t - ti) * 15)), ox = (3 - f) * -12, yy = y + 74 + i * 54;
        g.fillStyle = c.principal; g.fillRect(snap(x + 30 + ox), yy + 6, 30, 30); g.fillStyle = c.fundo; g.fillRect(snap(x + 36 + ox), yy + 12, 18, 18);
        if (t >= T(17 + i)) sprite(g, 'check', snap(x + 30 + ox), yy, 5, m);
        g.fillStyle = c.texto; g.font = this.fL(38); g.fillText(it, snap(x + 78 + ox), yy - 4);
      });
    }
    // "CLT": selo de modo dificil
    if (blink(tI + 0.07)) { pxBox(g, 564, 972, 438, 96, { fill: c.fundo, border: c.apoio, shadow: '#0E1026' }); g.fillStyle = c.destaque; g.font = this.fT(68); g.fillText('MODO DIFÍCIL', 596, 980); }
  },
};

// ================= prancha =================
const DIRS = [DA, DB, DC];
DIRS.forEach(d => { d.T = i => d.words[i].t; d.events = d.ev(); });
const boards = [];
const canvas = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };

class Board {
  constructor(d) {
    this.d = d; this.cv = canvas(); this.g = this.cv.getContext('2d');
    this.F = canvas(); this.gF = this.F.getContext('2d'); this.tmp = canvas(); this.cache = canvas();
    this.v = document.createElement('video'); this.v.src = VIDEO; this.v.muted = true; this.v.playsInline = true; this.v.preload = 'auto';
    this.som = false; this.prevT = 0; this.hits = []; this.pausado = false;
    this.cv.addEventListener('click', e => {
      const r = this.cv.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W, y = (e.clientY - r.top) / r.height * H;
      if (x >= MX && x <= MX + MW && y >= MY && y <= MY + MH) { this.alternarSom(); return; }
      for (const h of this.hits) if (x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h) { audio(); tocar(h.som); return; }
    });
  }
  alternarSom() {
    boards.forEach(o => { if (o !== this) { o.som = false; o.v.muted = true; } });
    this.som = !this.som; this.v.muted = !this.som; if (this.som) audio();
  }
  renderStatic() {
    const d = this.d, c = d.c, g = this.cache.getContext('2d');
    g.textBaseline = 'top'; g.textAlign = 'left'; d.bg(g);
    // cabecalho
    g.fillStyle = d.hdr2 || c.principal; g.font = d.fN(24); g.fillText('DIREÇÃO ' + d.id, 48, 30);
    g.fillStyle = d.hdr || c.principal; fit(g, d.fT, d.titulo, d.tSize, 990); g.fillText(d.titulo, 44, d.tY);
    g.fillStyle = d.txt2; fit(g, d.fN, d.subt, 27, 990); g.fillText(d.subt, 48, d.sY);
    d.rule(g, 40, 212, 1000, 'grossa');
    // paleta
    d.label(g, 'PALETA', 610, 236, 430);
    d.roles.forEach(([k, nome, uso], i) => {
      const y = 296 + i * 74; d.chip(g, 610, y, 62, c[k]);
      g.fillStyle = d.txt1; g.font = d.fL(24); g.fillText(nome, 690, y + 2);
      g.textAlign = 'right'; g.font = d.fN(22); g.fillText(c[k].toUpperCase(), 1040, y + 4); g.textAlign = 'left';
      g.fillStyle = d.txt2; g.font = d.fN(20); g.fillText(uso, 690, y + 36);
    });
    // fontes
    d.label(g, 'FONTES', 610, 670, 430);
    const [s1, n1, z1i] = d.fontes[0], z1 = fit(g, d.fT, s1, z1i, 430); g.fillStyle = d.fontC1; g.fillText(s1, 610, 730);
    g.fillStyle = d.txt2; g.font = d.fN(20); g.fillText(n1, 612, 730 + z1 * 1.08 + 4);
    const [s2, n2, z2i] = d.fontes[1], z2 = fit(g, d.fL, s2, z2i, 430); g.fillStyle = d.txt1; g.fillText(s2, 610, 852);
    g.fillStyle = d.txt2; g.font = d.fN(20); g.fillText(n2, 612, 852 + z2 * 1.2 + 4);
    // elementos
    d.label(g, 'ELEMENTOS', 610, 946, 430); d.icons(g); d.sig(g);
    // movimento
    d.rule(g, 40, 1206, 1000, 'grossa');
    d.label(g, 'MOVIMENTO', 40, 1224, 1000);
    d.curve(g, 40, 1284, 290, 236);
    g.font = d.fN(22); g.fillStyle = d.txt1; let y = 1286;
    d.mov.forEach(m => { g.fillText('•', 358, y); y += para(g, m, 380, y, 655, 28) + 6; });
    // transicao + sons
    d.rule(g, 40, 1544, 1000, 'fina');
    const lw = d.label(g, 'TRANSIÇÃO', 40, 1558, 590); g.fillStyle = d.txt2; g.font = d.fN(21); g.fillText(d.transNome, 40 + lw + 14, 1566);
    const tF = canvas(), tg = tF.getContext('2d');
    [0.06, 0.2, 0.5, 0.7, 0.94].forEach((p, i) => { tg.save(); d.trans(tg, this.old, this.nw, p); tg.restore(); g.drawImage(tF, 40 + i * 116, 1616, 104, 184); });
    d.label(g, 'SONS', 680, 1558, 360);
    d.sons.forEach(([k, nome], i) => {
      const yy = 1616 + i * 38; d.panel(g, 680, yy, 360, 33); g.fillStyle = d.txt1; g.font = d.fN(20); g.fillText('▶  ' + nome, 696, yy + 6);
      this.hits.push({ x: 680, y: yy, w: 360, h: 33, som: k });
    });
    // legenda
    d.rule(g, 40, 1814, 1000, 'fina');
    g.fillStyle = d.txt1; g.font = d.fN(22); para(g, d.legenda, 48, 1830, 990, 28);
  }
  frame(t, still) {
    const d = this.d, g = this.g;
    g.drawImage(this.cache, 0, 0);
    this.renderMock(t, still);
    g.drawImage(this.F, MX, MY, MW, MH); d.frame(g);
    if (!still) {
      const txt = this.som ? '🔊 som ligado' : '🔇 clique para ouvir';
      g.font = '600 22px system-ui, sans-serif'; const tw = g.measureText(txt).width;
      g.fillStyle = 'rgba(0,0,0,0.55)'; rrect(g, MX + 12, MY + 12, tw + 24, 36, 18); g.fill(); g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.fillText(txt, MX + 24, MY + 31); g.textBaseline = 'top';
    }
  }
  // desenha so o quadro do video (1080x1920) com os elementos e a legenda em this.F
  renderMock(t, still) {
    const d = this.d, gF = this.gF;
    const tt = d.quant ? Math.floor(t * d.quant) / d.quant : t, cam = still ? { s: 1, dx: 0, dy: 0 } : d.camera(tt);
    gF.save(); gF.translate(W / 2 + cam.dx, H / 2 + cam.dy); gF.scale(cam.s, cam.s); gF.translate(-W / 2, -H / 2);
    gF.fillStyle = '#000'; gF.fillRect(-40, -40, W + 80, H + 80);
    if (this.v.readyState >= 2) gF.drawImage(this.v, 0, 0, W, H);
    gF.textBaseline = 'top'; gF.textAlign = 'left'; d.overlay(gF, tt); gF.restore();
    gF.textBaseline = 'top'; gF.textAlign = 'left'; d.caption(gF, tt);
    if (d.flash && !still) d.flash(gF, tt);
    if (!still && t > d.L - d.TR) { this.tmp.getContext('2d').drawImage(this.F, 0, 0); gF.save(); d.trans(gF, this.tmp, this.nw, prog(t, d.L - d.TR, d.TR)); gF.restore(); }
  }
  tick() {
    if (this.pausado) return;
    const d = this.d; let t = this.v.currentTime - d.seg;
    if (t >= d.L || t < -0.3) { this.v.currentTime = d.seg; this.prevT = 0; t = 0; }
    t = Math.max(0, t);
    if (this.som) for (const e of d.events) if (e.t > this.prevT && e.t <= t) tocar(e.s);
    this.prevT = t; this.frame(t, false);
  }
}

async function capturar(v, t) { await new Promise(r => { v.onseeked = r; v.currentTime = t; }); const c = canvas(); c.getContext('2d').drawImage(v, 0, 0, W, H); return c; }
async function carregarFontes() {
  const fs = ['900 extra-condensed 50px "Archivo"', '800 50px "Inter Tight"', '500 50px "Inter Tight"', '50px "Permanent Marker"', '800 50px "Shantell Sans"', '400 50px "Shantell Sans"', '50px "Jersey 25"', '50px "Jersey 15"'];
  await Promise.all(fs.map(f => document.fonts.load(f, 'AÁÇÃÕÉÍ aãçé 0123')));
}
async function main() {
  await carregarFontes();
  const cap = document.createElement('video'); cap.src = VIDEO; cap.muted = true; cap.preload = 'auto';
  await new Promise(r => { if (cap.readyState >= 2) r(); else cap.onloadeddata = r; });
  for (const d of DIRS) {
    const b = new Board(d); b.old = await capturar(cap, d.seg + d.L - 0.15); b.nw = await capturar(cap, d.seg + 0.05);
    b.renderStatic(); boards.push(b); document.getElementById('quadros').appendChild(b.cv);
  }
  for (const b of boards) { b.v.currentTime = b.d.seg; try { await b.v.play(); } catch (e) { console.warn(e); } }
  const loop = () => { boards.forEach(b => b.tick()); requestAnimationFrame(loop); }; loop();
  window.pronto = true;
}
// grava as pranchas (quadro "heroi" de cada uma) como PNG na pasta pranchas/
async function salvar() {
  for (const b of boards) {
    b.pausado = true; b.v.pause();
    await new Promise(r => { b.v.onseeked = r; b.v.currentTime = b.d.seg + b.d.hero; });
    b.frame(b.d.hero, true);
    const blob = await new Promise(r => b.cv.toBlob(r, 'image/png'));
    await fetch('/salvar?nome=prancha_' + b.d.id + '.png', { method: 'POST', body: blob });
  }
  const all = document.createElement('canvas'); all.width = W * 3 + 80; all.height = H + 40; const ag = all.getContext('2d');
  ag.fillStyle = '#1b1b1d'; ag.fillRect(0, 0, all.width, all.height); boards.forEach((b, i) => ag.drawImage(b.cv, 20 + i * (W + 20), 20));
  const blob = await new Promise(r => all.toBlob(r, 'image/png'));
  await fetch('/salvar?nome=pranchas_lado_a_lado.png', { method: 'POST', body: blob });
  for (const b of boards) { b.pausado = false; b.v.currentTime = b.d.seg; b.v.play(); }
  return 'ok';
}
window.salvar = salvar; window.boards = boards;

document.querySelectorAll('[data-v]').forEach(bt => bt.addEventListener('click', () => {
  document.querySelectorAll('[data-v]').forEach(x => x.classList.toggle('on', x === bt));
  const v = bt.dataset.v; document.body.classList.toggle('uma', v !== 'todas');
  boards.forEach(b => b.cv.classList.toggle('sel', b.d.id === v));
}));
// paginas que so reaproveitam as funcoes (ex.: paletas.html) definem SEM_MAIN antes de carregar este arquivo
if (!window.SEM_MAIN) main();
