const TOKEN = /\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|([A-Za-z]+)|([()+\-*/^]))/gy;
const FUNCTIONS = Object.freeze({
  sin: Math.sin, cos: Math.cos, tan: Math.tan,
  sqrt: Math.sqrt, abs: Math.abs, ln: Math.log,
  log: Math.log10, exp: Math.exp
});

function tokenize(source) {
  if (typeof source !== 'string' || !source.trim()) throw new Error('Enter a function, for example x^2 or sin(x).');
  if (source.length > 120) throw new Error('Graph expression is too long (maximum 120 characters).');
  const tokens = [];
  let cursor = 0;
  while (cursor < source.length) {
    TOKEN.lastIndex = cursor;
    const match = TOKEN.exec(source);
    if (!match) throw new Error('Unsupported graph character at position ' + (cursor + 1) + '.');
    tokens.push(match[1] ?? match[2]?.toLowerCase() ?? match[3]);
    cursor = TOKEN.lastIndex;
  }
  return tokens;
}

function compile(source) {
  const tokens = tokenize(source);
  let position = 0;
  const peek = () => tokens[position];
  const take = () => tokens[position++];

  function primary() {
    const token = take();
    if (token === '(') {
      const value = sum();
      if (take() !== ')') throw new Error('Missing closing parenthesis.');
      return value;
    }
    if (token === undefined) throw new Error('Expected a value.');
    if (/^\d/.test(token)) return () => Number(token);
    if (token === 'x') return x => x;
    if (token === 'pi') return () => Math.PI;
    if (token === 'e') return () => Math.E;
    if (Object.hasOwn(FUNCTIONS, token)) {
      if (take() !== '(') throw new Error('Function ' + token + ' requires parentheses.');
      const argument = sum();
      if (take() !== ')') throw new Error('Missing closing parenthesis after ' + token + '.');
      return x => FUNCTIONS[token](argument(x));
    }
    throw new Error('Unknown graph name: ' + token + '. Use x, pi, e, or a supported function.');
  }
  function power() {
    const left = primary();
    if (peek() === '^') { take(); const right = unary(); return x => left(x) ** right(x); }
    return left;
  }
  function unary() {
    if (peek() === '+') { take(); return unary(); }
    if (peek() === '-') { take(); const value = unary(); return x => -value(x); }
    return power();
  }
  function product() {
    let value = unary();
    while (peek() === '*' || peek() === '/') {
      const op = take(), right = unary(), left = value;
      value = x => op === '*' ? left(x) * right(x) : left(x) / right(x);
    }
    return value;
  }
  function sum() {
    let value = product();
    while (peek() === '+' || peek() === '-') {
      const op = take(), right = product(), left = value;
      value = x => op === '+' ? left(x) + right(x) : left(x) - right(x);
    }
    return value;
  }
  const fn = sum();
  if (position !== tokens.length) throw new Error('Unexpected token: ' + tokens[position] + '.');
  return fn;
}

function xmlEscape(value) {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[ch]));
}

export function createGraphSvg(expression, options = {}) {
  const minX = Number(options.minX ?? -10), maxX = Number(options.maxX ?? 10);
  const width = Math.round(Number(options.width ?? 600)), height = Math.round(Number(options.height ?? 340));
  const samples = Math.round(Number(options.samples ?? 600));
  if (!Number.isFinite(minX) || !Number.isFinite(maxX) || minX >= maxX || maxX - minX > 10000) throw new Error('Choose a valid x-domain with minX < maxX and width no greater than 10,000.');
  if (!Number.isFinite(width) || width < 240 || width > 1000 || !Number.isFinite(height) || height < 180 || height > 800) throw new Error('Graph size must be between 240×180 and 1000×800.');
  if (!Number.isFinite(samples) || samples < 100 || samples > 2000) throw new Error('Graph sampling must be between 100 and 2,000 points.');
  const fn = compile(expression.trim().replace(/^y\s*=\s*/i, ''));
  const pad = 34, plotW = width - pad * 2, plotH = height - pad * 2;
  const xs = Array.from({length: 11}, (_, i) => minX + (maxX - minX) * i / 10);
  const ys = [];
  for (let i = 0; i <= samples; i++) {
    const x = minX + (maxX - minX) * i / samples;
    let y;
    try { y = fn(x); } catch { y = NaN; }
    if (Number.isFinite(y) && Math.abs(y) < 1e6) ys.push(y);
  }
  let minY = ys.length ? Math.min(...ys) : -10, maxY = ys.length ? Math.max(...ys) : 10;
  if (minY === maxY) { minY -= 1; maxY += 1; }
  const margin = Math.max((maxY - minY) * 0.08, 0.5);
  minY -= margin; maxY += margin;
  const px = x => pad + (x - minX) / (maxX - minX) * plotW;
  const py = y => pad + (maxY - y) / (maxY - minY) * plotH;
  const grid = [];
  for (let i = 0; i <= 10; i++) {
    const x = pad + plotW * i / 10, y = pad + plotH * i / 10;
    grid.push('<line x1="'+x.toFixed(2)+'" y1="'+pad+'" x2="'+x.toFixed(2)+'" y2="'+(height-pad)+'" class="graph-grid"/>');
    grid.push('<line x1="'+pad+'" y1="'+y.toFixed(2)+'" x2="'+(width-pad)+'" y2="'+y.toFixed(2)+'" class="graph-grid"/>');
  }
  const axisX = minY <= 0 && maxY >= 0 ? py(0) : height - pad;
  const axisY = minX <= 0 && maxX >= 0 ? px(0) : pad;
  const path = [];
  let drawing = false;
  for (let i = 0; i <= samples; i++) {
    const x = minX + (maxX - minX) * i / samples;
    let y;
    try { y = fn(x); } catch { y = NaN; }
    if (!Number.isFinite(y) || Math.abs(y) > 1e6 || y < minY - 2*(maxY-minY) || y > maxY + 2*(maxY-minY)) { drawing = false; continue; }
    path.push((drawing ? 'L' : 'M') + px(x).toFixed(2) + ' ' + py(y).toFixed(2));
    drawing = true;
  }
  return '<svg class="ultron-graph" viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Graph of y='+xmlEscape(expression)+'"><title>y='+xmlEscape(expression)+'</title><rect x="0" y="0" width="'+width+'" height="'+height+'" rx="12" class="graph-background"/>'+grid.join('')+'<line x1="'+pad+'" y1="'+axisX.toFixed(2)+'" x2="'+(width-pad)+'" y2="'+axisX.toFixed(2)+'" class="graph-axis"/><line x1="'+axisY.toFixed(2)+'" y1="'+pad+'" x2="'+axisY.toFixed(2)+'" y2="'+(height-pad)+'" class="graph-axis"/><path d="'+path.join(' ')+'" class="graph-curve" fill="none" stroke-linecap="round" stroke-linejoin="round"/><text x="'+pad+'" y="'+(height-10)+'" class="graph-label">x: '+minX+' to '+maxX+'</text><text x="'+(width-pad)+'" y="18" text-anchor="end" class="graph-label">y='+xmlEscape(expression)+'</text></svg>';
}
