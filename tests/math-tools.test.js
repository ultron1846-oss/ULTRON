import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MATH_TOOL_COMMANDS, tableOfValues, numericalDerivative, numericalIntegral,
  solveQuadratic, solveLinearSystem2x2, executeMathToolCommand, mathToolHelp
} from '../math-tools.js';

test('command directory has unique registered names and useful help',()=>{
  const names=MATH_TOOL_COMMANDS.map(item=>item.name);
  assert.equal(new Set(names).size,names.length);
  assert.ok(names.includes('/calc')&&names.includes('/table')&&names.includes('/quadratic'));
  assert.ok(names.includes('/help')&&names.includes('/graph')&&names.includes('/status'));
  assert.equal(executeMathToolCommand('/graph y=x^2').handled,false);
  for(const name of names)assert.ok(mathToolHelp().includes(name));
});

test('calculator commands check learner attempts and reject malformed expressions',()=>{
  assert.equal(executeMathToolCommand('/calc (12+8)/4').output.includes('without revealing the result'),true);
  assert.equal(executeMathToolCommand('/calc (12+8)/4 = 5').output,'Your calculation is correct.');
  assert.match(executeMathToolCommand('/calc (12+8)/4 = 4').output,/Not quite/);
  assert.equal(executeMathToolCommand('/gcd 84 30').output,'GCD: 6');
  assert.equal(executeMathToolCommand('/lcm 12 18').output,'LCM: 36');
  assert.equal(executeMathToolCommand('/factor 360').output,'360 = 2^3 × 3^2 × 5');
  assert.match(executeMathToolCommand('/calc 1/0').output,/Tool error/);
});

test('equation commands teach or check attempts without revealing final answers',()=>{
  const solveHint=executeMathToolCommand('/solve 2x + 3 = 11').output;
  assert.match(solveHint,/First step/);
  assert.doesNotMatch(solveHint,/x\s*=\s*4/);
  assert.equal(executeMathToolCommand('/solve 2x + 3 = 11 | x=4').output,'Your value satisfies the equation.');
  assert.match(executeMathToolCommand('/solve 2x + 3 = 11 | x=5').output,/Not yet/);

  assert.match(executeMathToolCommand('/quadratic 1 -3 2').output,/discriminant/);
  assert.equal(executeMathToolCommand('/quadratic 1 -3 2 | 1,2').output,'Both roots are correct.');
  assert.equal(executeMathToolCommand('/quadratic 1 2 1 | -1,-1').output,'Both roots are correct.');
  assert.match(executeMathToolCommand('/quadratic 1 -3 2 | 0,3').output,/I will not reveal the roots/);

  assert.match(executeMathToolCommand('/system 2 1 1 -1 5 1').output,/eliminate/);
  assert.equal(executeMathToolCommand('/system 2 1 1 -1 5 1 | 2,1').output,'Your pair satisfies the system.');
  assert.match(executeMathToolCommand('/system 2 1 1 -1 5 1 | 3,2').output,/I will not reveal the solution/);
});

test('table of values validates direction and bounds',()=>{
  assert.deepEqual(tableOfValues('x^2',-2,2,1),[
    {x:-2,y:4},{x:-1,y:1},{x:0,y:0},{x:1,y:1},{x:2,y:4}
  ]);
  assert.throws(()=>tableOfValues('x',0,1000,1),/101 rows/);
  assert.throws(()=>tableOfValues('x',0,2,-1),/point from start/);
  assert.match(executeMathToolCommand('/table x^2 -2 2 1').output,/2 \| 4/);
});

test('numerical derivative matches polynomial and trig reference values',()=>{
  assert.ok(Math.abs(numericalDerivative('x^3',2)-12)<1e-7);
  assert.ok(Math.abs(numericalDerivative('sin(x)',0)-1)<1e-7);
  assert.match(executeMathToolCommand('/derivative x^2 at 3').output,/≈ 6/);
});

test('Simpson integral matches exact polynomial integral and reversed limits',()=>{
  assert.ok(Math.abs(numericalIntegral('x^2',0,2)-8/3)<1e-10);
  assert.ok(Math.abs(numericalIntegral('x^2',2,0)+8/3)<1e-10);
  assert.equal(numericalIntegral('x',4,4),0);
  assert.match(executeMathToolCommand('/integral x^2 from 0 to 2').output,/≈ 2\.666666667/);
});

test('quadratic solver covers two, repeated and complex roots',()=>{
  assert.deepEqual(solveQuadratic(1,-3,2),{kind:'real',roots:[1,2]});
  assert.deepEqual(solveQuadratic(1,2,1),{kind:'repeated',roots:[-1]});
  assert.equal(solveQuadratic(1,0,1).kind,'complex');
  assert.throws(()=>solveQuadratic(0,1,1),/nonzero/);
});

test('2x2 solver covers unique, dependent and inconsistent systems',()=>{
  assert.deepEqual(solveLinearSystem2x2(2,1,1,-1,5,1),{kind:'unique',x:2,y:1});
  assert.equal(solveLinearSystem2x2(1,2,2,4,3,6).kind,'dependent');
  assert.equal(solveLinearSystem2x2(1,2,2,4,3,7).kind,'inconsistent');
  assert.equal(solveLinearSystem2x2(1,2,2,4,3,7).kind,'inconsistent');
});

test('command parser is safe and rejects unknown commands',()=>{
  assert.equal(executeMathToolCommand('ordinary text').handled,false);
  assert.equal(executeMathToolCommand('/not-a-tool x').handled,false);
  assert.match(executeMathToolCommand('/table x 0 1 0').output,/Tool error/);
  assert.match(executeMathToolCommand('/quadratic 1 0').output,/Tool error/);
  assert.match(executeMathToolCommand('/system 1 2 3').output,/Tool error/);
});
