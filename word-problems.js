const SMALL = {
 zero:0, one:1, two:2, three:3, four:4, five:5, six:6, seven:7, eight:8, nine:9,
 ten:10, eleven:11, twelve:12, thirteen:13, fourteen:14, fifteen:15, sixteen:16,
 seventeen:17, eighteen:18, nineteen:19
};
const TENS = { twenty:20, thirty:30, forty:40, fifty:50, sixty:60, seventy:70, eighty:80, ninety:90 };
const NUMBER_WORDS = [...Object.keys(SMALL), ...Object.keys(TENS), 'hundred'];
const WORD_NUMBER_PATTERN = NUMBER_WORDS.join('|');
const QUANTITY_PATTERN = '(?:\\d+(?:\\.\\d+)?|(?:'+WORD_NUMBER_PATTERN+')(?:[- ](?:'+WORD_NUMBER_PATTERN+'))*)';

function wordsToNumber(source) {
 const words=source.toLowerCase().replace(/-/g,' ').trim().split(/\s+/);
 let current=0;
 for(const word of words){
  if(/^\d+(?:\.\d+)?$/.test(word)){current+=Number(word);continue;}
  if(Object.hasOwn(SMALL,word)){current+=SMALL[word];continue;}
  if(Object.hasOwn(TENS,word)){current+=TENS[word];continue;}
  if(word==='hundred'){current=Math.max(1,current)*100;continue;}
  return null;
 }
 return Number.isFinite(current)?current:null;
}
function quantitiesIn(text){
 const re=new RegExp('\\b'+QUANTITY_PATTERN+'\\b','gi');
 const out=[];
 for(const match of text.matchAll(re)){
  const value=wordsToNumber(match[0]);
  if(value!==null)out.push({value,raw:match[0],index:match.index});
 }
 return out;
}
export function parseWordProblem(input){
 if(typeof input!=='string'||!input.trim())return {kind:'unsupported',reason:'Enter a word problem.'};
 if(input.length>600)return {kind:'unsupported',reason:'Word problems are limited to 600 characters.'};
 const text=input.toLowerCase().replace(/[’']/g,"'").replace(/\s+/g,' ').trim();
 const quantities=quantitiesIn(text);
 if(quantities.length<2)return {kind:'unsupported',reason:'I need at least two clearly stated quantities to solve this word-problem pattern.'};
 const values=quantities.map(q=>q.value);
 const directOps=[
  {pattern:/\b(?:plus|added to|add)\b/,operation:'addition'},
  {pattern:/\b(?:minus|subtract(?:ed)? from)\b/,operation:'subtraction'},
  {pattern:/\b(?:times|multiplied by)\b/,operation:'multiplication'},
  {pattern:/\b(?:divided by)\b/,operation:'division'}
 ];
 for(const item of directOps)if(item.pattern.test(text))return solve(item.operation,values[0],values[1],quantities.slice(0,2));
 if(/\b(?:shared equally|divided equally|split equally|equally among|per person|each person|how many each)\b/.test(text))return solve('division',values[0],values[1],quantities.slice(0,2));
 if(/\b(?:each|every|per|groups? of|rows? of|boxes? of)\b/.test(text))return solve('multiplication',values[0],values[1],quantities.slice(0,2));
 if(/\b(?:left|remain(?:s|ed)?|remaining|gave away|given away|sold|lost|used|difference|how many more|how many fewer|how many less)\b/.test(text))return solve('subtraction',values[0],values[1],quantities.slice(0,2));
 if(/\b(?:altogether|in total|total|combined|sum|all together)\b/.test(text))return solve('addition',values[0],values[1],quantities.slice(0,2));
 return {kind:'unsupported',reason:'I found quantities but no clear operation clue. Add wording such as altogether, left, each, or shared equally so I do not guess.'};
}
function solve(operation,a,b,sourceQuantities){
 let result,symbol,explanation;
 switch(operation){
  case 'addition':result=a+b;symbol='+';explanation='Combine the two quantities by addition.';break;
  case 'subtraction':result=a-b;symbol='−';explanation='Find the difference by subtracting the second quantity from the first.';break;
  case 'multiplication':result=a*b;symbol='×';explanation='Find the total across equal groups by multiplying the quantities.';break;
  case 'division':
   if(b===0)return {kind:'unsupported',reason:'A quantity cannot be divided into zero groups.'};
   result=a/b;symbol='÷';explanation='Share the total equally by dividing by the number of groups.';break;
  default:return {kind:'unsupported',reason:'That operation is not supported.'};
 }
 if(!Number.isFinite(result))return {kind:'unsupported',reason:'The computed result is outside the supported numeric range.'};
 return {kind:'solved',operation,expression:String(a)+' '+symbol+' '+String(b),result,explanation,quantities:sourceQuantities.map(q=>({value:q.value,word:q.raw})),confidence:'template-based'};
}
