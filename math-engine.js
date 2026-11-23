const tokenPattern = /\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|([()+\-*/^]))/gy;

export function tokenize(source) {
  if (typeof source !== 'string' || source.trim() === '') throw new Error('Enter a mathematical expression.');
  if (source.length > 240) throw new Error('Expression is too long (maximum 240 characters).');
  source = source.trim();
  const tokens = [];
  let cursor = 0;
  while (cursor < source.length) {
    tokenPattern.lastIndex = cursor;
    const match = tokenPattern.exec(source);
    if (!match) throw new Error(`Unsupported character at position ${cursor + 1}.`);
    tokens.push(match[1] ?? match[2]);
    cursor = tokenPattern.lastIndex;
  }
  return tokens;
}

export function evaluateExpression(source) {
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
    if (token === undefined || !/^\d/.test(token)) throw new Error('Expected a number or parenthesized expression.');
    const value = Number(token);
    if (!Number.isFinite(value)) throw new Error('Number is outside the supported range.');
    return value;
  }
  function power() {
    const left = primary();
    if (peek() === '^') { take(); return left ** unary(); }
    return left;
  }
  function unary() {
    if (peek() === '+') { take(); return unary(); }
    if (peek() === '-') { take(); return -unary(); }
    return power();
  }
  function product() {
    let value = unary();
    while (peek() === '*' || peek() === '/') {
      const op = take(); const right = unary();
      if (op === '/' && right === 0) throw new Error('Division by zero is undefined.');
      value = op === '*' ? value * right : value / right;
    }
    return value;
  }
  function sum() {
    let value = product();
    while (peek() === '+' || peek() === '-') {
      const op = take(); const right = product();
      value = op === '+' ? value + right : value - right;
    }
    return value;
  }
  const result = sum();
  if (position !== tokens.length) throw new Error(`Unexpected token “${peek()}”.`);
  if (!Number.isFinite(result)) throw new Error('Result is outside the supported numeric range.');
  return result;
}

export function solveLinearEquation(source) {
  if (typeof source !== 'string' || source.length > 240) throw new Error('Enter an equation under 240 characters.');
  const sides = source.split('=');
  if (sides.length !== 2 || sides.some(side => !side.trim())) throw new Error('Enter one equation with exactly one equals sign.');
  const expression = side => {
    const normalized = side.replace(/\s+/g, '').replace(/(?<![\d.)])x/g, '1*x').replace(/(?<=[\d.)])x/g, '*x');
    const pieces = normalized.split(/(?=[+-])/).filter(Boolean);
    let coefficient = 0, constant = 0;
    for (const piece of pieces) {
      if (piece.includes('x')) {
        const match = piece.match(/^([+-]?(?:\d+(?:\.\d*)?)?)\*?x$/);
        if (!match) throw new Error('Only linear equations using x are supported.');
        coefficient += match[1] === '' || match[1] === '+' ? 1 : match[1] === '-' ? -1 : Number(match[1]);
      } else constant += evaluateExpression(piece);
    }
    return { coefficient, constant };
  };
  const left = expression(sides[0]), right = expression(sides[1]);
  const coefficient = left.coefficient - right.coefficient;
  const constant = right.constant - left.constant;
  if (coefficient === 0) return constant === 0 ? { kind: 'all-real' } : { kind: 'none' };
  const value = constant / coefficient;
  if (!Number.isFinite(value)) throw new Error('Solution is outside the supported numeric range.');
  return { kind: 'unique', value };
}
