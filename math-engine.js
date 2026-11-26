const MAX_EXPRESSION_LENGTH = 240;
const MAX_TOKENS = 120;
const tokenPattern = /\s*(((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|([()+\-*/^×÷]))/gy;

export function tokenize(source) {
  if (typeof source !== 'string' || source.trim() === '') {
    throw new Error('Enter a mathematical expression.');
  }
  if (source.length > MAX_EXPRESSION_LENGTH) {
    throw new Error(`Expression is too long (maximum ${MAX_EXPRESSION_LENGTH} characters).`);
  }
  source = source.trim();
  const tokens = [];
  let cursor = 0;
  while (cursor < source.length) {
    tokenPattern.lastIndex = cursor;
    const match = tokenPattern.exec(source);
    if (!match) throw new Error(`Unsupported character or format at position ${cursor + 1}.`);
    tokens.push(match[1] ?? match[2]);
    if (tokens.length > MAX_TOKENS) throw new Error(`Expression has too many parts (maximum ${MAX_TOKENS}).`);
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
    if (token === undefined || !/^\d|^\./.test(token)) {
      throw new Error('Expected a number or parenthesized expression.');
    }
    const value = Number(token);
    if (!Number.isFinite(value)) throw new Error('Number is outside the supported numeric range.');
    return value;
  }
  function power() {
    const left = primary();
    if (peek() === '^') {
      take();
      return left ** unary();
    }
    return left;
  }
  function unary() {
    if (peek() === '+') { take(); return unary(); }
    if (peek() === '-') { take(); return -unary(); }
    return power();
  }
  function product() {
    let value = unary();
    while (peek() === '*' || peek() === '/' || peek() === '×' || peek() === '÷') {
      const op = take();
      const right = unary();
      if ((op === '/' || op === '÷') && right === 0) {
        throw new Error('Division by zero is undefined.');
      }
      value = op === '*' || op === '×' ? value * right : value / right;
    }
    return value;
  }
  function sum() {
    let value = product();
    while (peek() === '+' || peek() === '-') {
      const op = take();
      const right = product();
      value = op === '+' ? value + right : value - right;
    }
    return value;
  }

  const result = sum();
  if (position !== tokens.length) throw new Error(`Unexpected token “${peek()}”.`);
  if (!Number.isFinite(result)) throw new Error('Result is outside the supported numeric range.');
  return result;
}

function tokenizeEquationSide(source) {
  if (source.trim() === '') throw new Error('Both sides of the equation must contain an expression.');
  if (source.length > MAX_EXPRESSION_LENGTH) {
    throw new Error(`Equation is too long (maximum ${MAX_EXPRESSION_LENGTH} characters).`);
  }
  source = source.trim();
  const pattern = /\s*(((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|([xX])|([()+\-*/^×÷]))/gy;
  const tokens = [];
  let cursor = 0;
  while (cursor < source.length) {
    pattern.lastIndex = cursor;
    const match = pattern.exec(source);
    if (!match) throw new Error(`Unsupported equation character or format at position ${cursor + 1}.`);
    tokens.push(match[2] ?? (match[3] ? 'x' : match[4]));
    if (tokens.length > MAX_TOKENS) throw new Error(`Equation has too many parts (maximum ${MAX_TOKENS}).`);
    cursor = pattern.lastIndex;
  }
  return tokens;
}

const constant = value => ({ coefficient: 0, constant: value });
const finiteAffine = value => {
  if (!Number.isFinite(value.coefficient) || !Number.isFinite(value.constant)) {
    throw new Error('Equation is outside the supported numeric range.');
  }
  return value;
};
const addAffine = (left, right, sign = 1) => finiteAffine({
  coefficient: left.coefficient + sign * right.coefficient,
  constant: left.constant + sign * right.constant
});
const scaleAffine = (value, factor) => finiteAffine({
  coefficient: value.coefficient * factor,
  constant: value.constant * factor
});
const multiplyAffine = (left, right) => {
  if (left.coefficient !== 0 && right.coefficient !== 0) {
    throw new Error('Nonlinear equations are not supported; the equation must be linear in x.');
  }
  if (left.coefficient !== 0) return scaleAffine(left, right.constant);
  if (right.coefficient !== 0) return scaleAffine(right, left.constant);
  return constant(left.constant * right.constant);
};

function parseLinearExpression(source) {
  const tokens = tokenizeEquationSide(source);
  let position = 0;
  const peek = () => tokens[position];
  const take = () => tokens[position++];

  function primary() {
    const token = take();
    if (token === '(') {
      const value = sum();
      if (take() !== ')') throw new Error('Missing closing parenthesis in equation.');
      return value;
    }
    if (token === 'x') return { coefficient: 1, constant: 0 };
    if (token === undefined || !/^\d|^\./.test(token)) {
      throw new Error('Expected a number, x, or parenthesized expression in the equation.');
    }
    const value = Number(token);
    if (!Number.isFinite(value)) throw new Error('Number is outside the supported range.');
    return constant(value);
  }
  function power() {
    const base = primary();
    if (peek() !== '^') return base;
    take();
    const exponent = unary();
    if (exponent.coefficient !== 0) {
      throw new Error('The exponent cannot contain x in a linear equation.');
    }
    if (base.coefficient !== 0) {
      if (exponent.constant === 1) return base;
      if (exponent.constant === 0) return constant(1);
      throw new Error('Nonlinear powers of x are not supported.');
    }
    return constant(base.constant ** exponent.constant);
  }
  function unary() {
    if (peek() === '+') { take(); return unary(); }
    if (peek() === '-') { take(); return scaleAffine(unary(), -1); }
    return power();
  }
  function product() {
    let value = unary();
    while (true) {
      const op = peek();
      if (op === '*' || op === '×') {
        take();
        value = multiplyAffine(value, unary());
      } else if (op === '/' || op === '÷') {
        take();
        const divisor = unary();
        if (divisor.coefficient !== 0) {
          throw new Error('Division by an expression containing x is nonlinear or unsupported.');
        }
        if (divisor.constant === 0) throw new Error('Division by zero is undefined.');
        value = scaleAffine(value, 1 / divisor.constant);
      } else if (op === 'x' || op === '(') {
        // Coefficient notation such as 2x and grouped products such as 2(x + 1).
        value = multiplyAffine(value, unary());
      } else {
        break;
      }
    }
    return finiteAffine(value);
  }
  function sum() {
    let value = product();
    while (peek() === '+' || peek() === '-') {
      const op = take();
      value = addAffine(value, product(), op === '+' ? 1 : -1);
    }
    return value;
  }

  const result = sum();
  if (position !== tokens.length) throw new Error(`Unexpected token “${peek()}” in equation.`);
  return finiteAffine(result);
}

export function solveLinearEquation(source) {
  if (typeof source !== 'string' || source.trim() === '') {
    throw new Error('Enter a linear equation using x.');
  }
  if (source.length > MAX_EXPRESSION_LENGTH) {
    throw new Error(`Equation is too long (maximum ${MAX_EXPRESSION_LENGTH} characters).`);
  }
  const sides = source.split('=');
  if (sides.length !== 2 || sides.some(side => !side.trim())) {
    throw new Error('Enter one equation with exactly one equals sign and two non-empty sides.');
  }
  const left = parseLinearExpression(sides[0]);
  const right = parseLinearExpression(sides[1]);
  const coefficient = left.coefficient - right.coefficient;
  const constantTerm = right.constant - left.constant;
  if (coefficient === 0) {
    return constantTerm === 0 ? { kind: 'all-real' } : { kind: 'none' };
  }
  const value = constantTerm / coefficient;
  if (!Number.isFinite(value)) throw new Error('Solution is outside the supported numeric range.');
  return { kind: 'unique', value };
}
