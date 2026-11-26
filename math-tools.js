import { evaluateExpression, solveLinearEquation } from './math-engine.js?v=20261125-3';
import { compileGraphExpression } from './graph-tool.js?v=20261125-2';

export const MATH_TOOL_COMMANDS = Object.freeze([
  {name:'/help',description:'Show the complete command directory.'},
  {name:'/menu',description:'Open the command directory.'},
  {name:'/commands',description:'List registered commands.'},
  {name:'/tools',description:'List registered mathematics tools.'},
  {name:'/topics',description:'List mathematics topic commands.'},
  {name:'/status',description:'Show deterministic Math Agent capabilities.'},
  {name:'/graph',description:'Plot a supported function locally.'},
  {name:'/calc',description:'Check your attempted calculation: /calc expression = your_answer.'},
  {name:'/gcd',description:'Greatest common divisor of two integers.'},
  {name:'/lcm',description:'Least common multiple of two integers.'},
  {name:'/factor',description:'Prime factorization of a positive integer.'},
  {name:'/table',description:'Table of values: /table expression start end step.'},
  {name:'/derivative',description:'Numerical derivative: /derivative expression at x.'},
  {name:'/integral',description:'Numerical definite integral: /integral expression from a to b.'},
  {name:'/solve',description:'Get a first-step hint or check your attempt: /solve equation | x=value.'},
  {name:'/quadratic',description:'Get a discriminant hint or check roots: /quadratic a b c | r1,r2.'},
  {name:'/system',description:'Get an elimination hint or check your attempt: /system a b c d e f | x,y.'}
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
    const consistent=(a*f-c*e===0)&&(b*f-d*e===0);
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
  if(['/help','/menu','/commands','/tools','/topics','/status','/graph'].includes(command))return {handled:false};
  try{
    let output,detail='LOCAL DETERMINISTIC MATH TOOL';
    if(command==='/calc'){
      if(!args)throw new Error('Usage: /calc expression = your_answer');
      const match=args.match(/^([\s\S]+?)\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$/);
      if(!match)throw new Error('Try the calculation first, then enter it as /calc expression = your_answer. The tool checks your attempt without revealing the result.');
      const expected=evaluateExpression(match[1].trim()),submitted=numeric(match[2]);
      const tolerance=1e-10*Math.max(1,Math.abs(expected),Math.abs(submitted));
      output=Math.abs(expected-submitted)<=tolerance?'Your calculation is correct.':'Not quite. Check the order of operations and try again.';
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
      const parts=args.split('|'),equation=parts[0].trim();
      if(!equation.includes('='))throw new Error('Usage: /solve equation | x=value');
      if(parts.length<2){output='First step: simplify both sides and collect the x-terms on one side. Tell me the equation you get; I will check that step.';}
      else{
        const attempt=parts[1].trim().match(/^x\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$/i);
        if(!attempt)throw new Error('Enter your attempted value after |, for example: /solve 2x + 3 = 11 | x=4');
        const submitted=numeric(attempt[1]),result=solveLinearEquation(equation);
        output=result.kind==='unique'&&Math.abs(result.value-submitted)<=1e-10*Math.max(1,Math.abs(result.value),Math.abs(submitted))?'Your value satisfies the equation.':'Not yet. Check your inverse operations and substitution; I will not reveal the solution.';
      }
    }else if(command==='/quadratic'){
      const parts=args.split('|'),coefficients=parts[0].trim().split(/\s+/).map(numeric);
      if(coefficients.length!==3)throw new Error('Usage: /quadratic a b c | r1,r2');
      const [a,b,c]=coefficients;
      if(parts.length<2){output='First step: calculate the discriminant D = b² − 4ac using your coefficients. Send me D and I will check it.';}
      else{
        const roots=parts[1].split(',').map(numeric);
        if(roots.length!==2)throw new Error('Enter your two attempted roots after |, separated by a comma.');
        const result=solveQuadratic(a,b,c);
        const correct=result.kind==='real'&&result.roots.every((value,index)=>Math.abs(value-roots.slice().sort((x,y)=>x-y)[index])<=1e-10*Math.max(1,Math.abs(value)));
        output=correct?'Both roots are correct.':'Not yet. Check the discriminant and quadratic formula; I will not reveal the roots.';
      }
    }else if(command==='/system'){
      const parts=args.split('|'),coefficients=parts[0].trim().split(/\s+/).map(numeric);
      if(coefficients.length!==6)throw new Error('Usage: /system a b c d e f | x,y');
      if(parts.length<2){output='First step: choose x or y to eliminate. Multiply one or both equations so the chosen coefficients match or are opposites, then subtract. Send me the resulting equation.';}
      else{
        const attempt=parts[1].split(',').map(numeric);
        if(attempt.length!==2)throw new Error('Enter your attempted values after | as x,y.');
        const result=solveLinearSystem2x2(...coefficients);
        const correct=result.kind==='unique'&&Math.abs(result.x-attempt[0])<=1e-10*Math.max(1,Math.abs(result.x))&&Math.abs(result.y-attempt[1])<=1e-10*Math.max(1,Math.abs(result.y));
        output=correct?'Your pair satisfies the system.':'Not yet. Check elimination and substitute both values into the original equations; I will not reveal the solution.';
      }
    }
    return {handled:true,command,output,detail};
  }catch(error){return {handled:true,command,output:'Tool error: '+(error.message||String(error)),detail:'Check command syntax and supported limits.'};}
}

export function mathToolHelp(){
  return MATH_TOOL_COMMANDS.map(item=>item.name+' — '+item.description).join('\n');
}
