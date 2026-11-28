import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { evaluateExpression, solveLinearEquation, tokenize } from '../math-engine.js';

test('TypeScript source declares explicit token and equation result types', async () => {
  const [source, packageJson, packageLock] = await Promise.all([
    readFile(new URL('../src/math-engine.ts', import.meta.url), 'utf8'),
    readFile(new URL('../package.json', import.meta.url), 'utf8'),
    readFile(new URL('../package-lock.json', import.meta.url), 'utf8'),
  ]);
  const manifest = JSON.parse(packageJson);
  const lock = JSON.parse(packageLock);
  const scripts = manifest.scripts;
  const declaredTypeScript = manifest.devDependencies?.typescript;
  assert.match(declaredTypeScript ?? '', /^\d+\.\d+\.\d+$/);
  assert.equal(lock.packages?.['']?.devDependencies?.typescript, declaredTypeScript);
  assert.equal(lock.packages?.['node_modules/typescript']?.version, declaredTypeScript);
  assert.ok(scripts['build:math'].includes('tsc'));
  assert.match(scripts.test, /build:math/);
  assert.match(source, /export type LinearEquationSolution/);
  assert.match(source, /export function tokenize\(source: string\): string\[\]/);
  assert.match(source, /export function evaluateExpression\(source: string\): number/);
  assert.match(source, /export function solveLinearEquation\(source: string\): LinearEquationSolution/);
  assert.doesNotMatch(source, /:\s*any\b/);
});

test('compiled browser math engine preserves expression and equation behavior', () => {
  assert.deepEqual(tokenize('2 × (3 + 4)'), ['2', '×', '(', '3', '+', '4', ')']);
  assert.equal(evaluateExpression('-2^2 + 3 * 4'), 8);
  assert.equal(evaluateExpression('2^3^2'), 512);
  assert.deepEqual(solveLinearEquation('2x + 3 = 11'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('x = x'), { kind: 'all-real' });
  assert.deepEqual(solveLinearEquation('x = x + 1'), { kind: 'none' });
  assert.throws(() => evaluateExpression('5 / 0'), /Division by zero/);
});
