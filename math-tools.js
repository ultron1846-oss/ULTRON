import { evaluateExpression, solveLinearEquation } from './math-engine.js?v=20261125-3';
import { compileGraphExpression } from './graph-tool.js?v=20261125-2';

export const MATH_TOOL_COMMANDS = Object.freeze([
  {name:'/calc',description:'Evaluate a supported arithmetic expression.'},
  {name:'/gcd',description:'Greatest common divisor of two integers.'},
  {name:'/lcm',description:'Least common multiple of two integers.'},
  {name:'/factor',description:'Prime factorization of a positive integer.'},
  {name:'/table',description:'Table of values: /table expression start end step.'},
  {name:'/derivative',description:'Numerical derivative: /derivative expression at x.'},
  {name:'/integral',description:'Numerical definite integral: /integral expression from a to b.'},
  {name:'/solve',description:'Solve a supported linear equation.'},
  {name:'/quadratic',description:'Solve ax²+bx+c=0 using /quadratic a b c.'},
  {name:'/system',description:'Solve a 2×2 system: /system a b c d e f means ax+by=e, cx+dy=f.'}
]);

const MAX_SAFE_INPUT = 1e12;
const numeric = value => {
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value)) throw new Error('Expected a valid finite number.');
  const result = Number(value);
  if (!Number.isFinite(result)) throw new Error('Number is outside the supported range.');
  return result;
};
const integer = value => {
  const result = numeric(value);
  if (!Number.isSafeInteger(result) || Math.abs(result) > MAX_SAFE_INPUT) throw new Error('Use a safe integer with absolute value ≤ 1,000,000,000,000.');
  return result;
};
const gcd = (a,b) => {
  a=Math.abs(a);b=Math.abs(b);
  while(b){const r=a%b;a=b;b=r;}
  return a;
};
const format = value => Number.isInteger(value) ? String(value) : Number(value.toPrecision(10)).toString();
const parseFunctionAndX = raw => {
  const match=raw.match(/^([\s\S]+?)\s+at\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$/i);
  if(!match)throw new Error('Usage: /derivative expression at x. Example: /derivative x^2 at 3');
  return {expression:match[1].trim(),x:numeric(match[2])};
};
const parseFunctionAndBounds = raw => {
  const match=raw.match(/^([\s\S]+?)\s+from\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s+to\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$/i);
  if(!match)throw new Error('Usage: /integral expression from a to b. Example: /integral x^2 from 0 to 2');
  return {expression:match[1].trim(),a:numeric(match[2]),b:numeric(match[3])};
};

export function tableOfValues(expression,start,end,step){
  const fn=compileGraphExpression(expression);
  for(const value of [start,end,step])if(!Number.isFinite(value))throw new Error('Table bounds and step must be finite.');
  if(step===0||(end-start)*step<0)throw new Error('Step must be nonzero and point from start toward end.');
  const count=Math.floor((end-start)/step+1e-10)+1;
  if(count<1||count>101)throw new Error('Table is limited to 101 rows; choose a larger step.');
  const rows=[];
  for(let i=0;i<count;i++){
    const x=start+i*step;
    let y;try{y=fn(x);}catch{y=NaN;}
    rows.push({x,y:Number.isFinite(y)?y:null});
  }
  return rows;
}

export function numericalDerivative(expression,x){
  if(!Number.isFinite(x)||Math.abs(x)>1e12)throw new Error('Evaluation point must be finite and within ±1e12.');
  const fn=compileGraphExpression(expression);
  const h=1e-4*Math.max(1,Math.abs(x));
  const values=[fn(x-2*h),fn(x-h),fn(x+h),fn(x+2*h)];
  if(values.some(v=>!Number.isFinite(v)))throw new Error('Function is not finite near the requested point.');
  const result=(values[0]-8*values[1]+8*values[2]-values[3])/(12*h);
  if(!Number.isFinite(result))throw new Error('Derivative estimate is outside the supported range.');
  return result;
}

export function numericalIntegral(expression,a,b,intervals=1000){
  if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a)>1e12||Math.abs(b)>1e12)throw new Error('Integration bounds must be finite and within ±1e12.');
  if(!Number.isInteger(intervals)||intervals<2||intervals>10000)throw new Error('Simpson integration requires 2–10,000 intervals.');
  if(intervals%2)intervals++;
  const fn=compileGraphExpression(expression);
  if(a===b)return 0;
  const direction=b<a?-1:1;
  const left=Math.min(a,b),right=Math.max(a,b),h=(right-left)/intervals;
  let sum=fn(left)+fn(right);
  if(!Number.isFinite(sum))throw new Error('Function is not finite on the integration interval.');
  for(let i=1;i<intervals;i++){
    const value=fn(left+i*h);
    if(!Number.isFinite(value))throw new Error('Function is not finite on the integration interval.');
    sum+=(i%2?4:2)*value;
  }
  const result=direction*sum*h/3;
  if(!Number.isFinite(result))throw new Error('Integral estimate is outside the supported range.');
  return result;
}

export function solveQuadratic(a,b,c){
  if(![a,b,c].every(Number.isFinite))throw new Error('Quadratic coefficients must be finite.');
  if(a===0)throw new Error('Coefficient a must be nonzero for a quadratic.');
  const discriminant=b*b-4*a*c;
  if(!Number.isFinite(discriminant))throw new Error('Discriminant is outside the supported range.');
  if(discriminant<0){const real=-b/(2*a),imag=Math.sqrt(-discriminant)/(2*Math.abs(a));return {kind:'complex',real,imag};}
  if(discriminant===0)return {kind:'repeated',roots:[-b/(2*a)]};
  const root=Math.sqrt(discriminant);
  const q=-0.5*(b+(b>=0?root:-root));
  const roots=q===0?[-b/(2*a),-b/(2*a)]:[q/a,c/q];
  roots.sort((x,y)=>x-y);
  if(roots.some(v=>!Number.isFinite(v)))throw new Error('Roots are outside the supported range.');
  return {kind:'real',roots};
}

export function solveLinearSystem2x2(a,b,c,d,e,f){
  if(![a,b,c,d,e,f].every(Number.isFinite))throw new Error('System coefficients must be finite.');
  const det=a*d-b*c;
  if(det===0){
    const consistent=(a===0&&b===0?e===0:true)&&(c===0&&d===0?f===0:true);
    return {kind:consistent?'dependent':'inconsistent'};
  }
  const x=(e*d-b*f)/det,y=(a*f-e*c)/det;
  if(!Number.isFinite(x)||!Number.isFinite(y))throw new Error('Solution is outside the supported range.');
  return {kind:'unique',x,y};
}

export function executeMathToolCommand(raw){
  if(typeof raw!=='string'||!raw.trim())return {handled:false};
  const text=raw.trim(),match=text.match(/^(\/[-a-z]+)(?:\s+([\s\S]*))?$/i);
  if(!match)return {handled:false};
  const command=match[1].toLowerCase(),args=(match[2]||'').trim();
  if(!MATH_TOOL_COMMANDS.some(item=>item.name===command))return {handled:false};
  try{
    let output,detail='LOCAL DETERMINISTIC MATH TOOL';
    if(command==='/calc'){
      if(!args)throw new Error('Usage: /calc expression');
      output='Result: '+format(evaluateExpression(args));
    }else if(command==='/gcd'||command==='/lcm'){
      const parts=args.split(/\s+/);if(parts.length!==2)throw new Error('Usage: '+command+' integer integer');
      const a=integer(parts[0]),b=integer(parts[1]),g=gcd(a,b);
      if(command==='/gcd')output='GCD: '+g;
      else{const value=g===0?0:Math.abs(a/g*b);if(!Number.isSafeInteger(value))throw new Error('LCM exceeds the safe integer range.');output='LCM: '+value;}
    }else if(command==='/factor'){
      const value=integer(args);if(value<=0)throw new Error('Factorization requires a positive integer.');
      let n=value,factors=[];for(let p=2;p*p<=n;p+=(p===2?1:2)){let exponent=0;while(n%p===0){n/=p;exponent++;}if(exponent)factors.push(exponent===1?String(p):p+'^'+exponent);}
      if(n>1)factors.push(String(n));output=value+' = '+(factors.join(' × ')||'1');
    }else if(command==='/table'){
      const parts=args.split(/\s+/);if(parts.length<4)throw new Error('Usage: /table expression start end step');
      const step=numeric(parts.pop()),end=numeric(parts.pop()),start=numeric(parts.pop()),expression=parts.join(' ');
      const rows=tableOfValues(expression,start,end,step);
      output='x | f(x)\n'+rows.map(row=>format(row.x)+' | '+(row.y===null?'undefined':format(row.y))).join('\n');
    }else if(command==='/derivative'){
      const {expression,x}=parseFunctionAndX(args);output='f′('+format(x)+') ≈ '+format(numericalDerivative(expression,x))+'\nMethod: 5-point central difference; numerical estimate, not symbolic differentiation.';
    }else if(command==='/integral'){
      const {expression,a,b}=parseFunctionAndBounds(args);output='∫['+format(a)+','+format(b)+'] f(x) dx ≈ '+format(numericalIntegral(expression,a,b))+'\nMethod: composite Simpson rule with 1,000 intervals; numerical estimate.';
    }else if(command==='/solve'){
      if(!args.includes('='))throw new Error('Usage: /solve linear equation, e.g. /solve 2x + 3 = 11');
      const result=solveLinearEquation(args);
      output=result.kind==='unique'?'x = '+format(result.value):result.kind==='none'?'No solution.':'All real values of x satisfy the equation.';
    }else if(command==='/quadratic'){
      const p=args.split(/\s+/).map(numeric);if(p.length!==3)throw new Error('Usage: /quadratic a b c for ax²+bx+c=0');
      const result=solveQuadratic(...p);
      output=result.kind==='complex'?'Complex roots: '+format(result.real)+' ± '+format(result.imag)+'i':result.kind==='repeated'?'Repeated root: '+format(result.roots[0]):'Roots: '+result.roots.map(format).join(', ');
    }else if(command==='/system'){
      const p=args.split(/\s+/).map(numeric);if(p.length!==6)throw new Error('Usage: /system a b c d e f (ax+by=e, cx+dy=f)');
      const result=solveLinearSystem2x2(...p);
      output=result.kind==='unique'?'x = '+format(result.x)+', y = '+format(result.y):result.kind==='dependent'?'Dependent system: infinitely many solutions.':'Inconsistent system: no solution.';
    }
    return {handled:true,command,output,detail};
  }catch(error){return {handled:true,command,output:'Tool error: '+(error.message||String(error)),detail:'Check command syntax and supported limits.'};}
}

export function mathToolHelp(){
  return MATH_TOOL_COMMANDS.map(item=>item.name+' — '+item.description).join('\n');
}
