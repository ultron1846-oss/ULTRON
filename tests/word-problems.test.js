import test from 'node:test';
import assert from 'node:assert/strict';
import { parseWordProblem } from '../word-problems.js';

test('understands addition word problems with number words',()=>{
 const result=parseWordProblem('Mia has three apples and gets five more. How many apples does she have altogether?');
 assert.equal(result.kind,'solved');assert.equal(result.operation,'addition');assert.equal(result.result,8);
});
test('understands subtraction and remaining quantities',()=>{
 const result=parseWordProblem('There were 15 cookies. Sam ate 4 cookies. How many cookies are left?');
 assert.equal(result.operation,'subtraction');assert.equal(result.result,11);
});
test('understands equal groups as multiplication',()=>{
 const result=parseWordProblem('There are 6 boxes with 4 pencils in each box. How many pencils in total?');
 assert.equal(result.operation,'multiplication');assert.equal(result.result,24);
});
test('understands equal sharing as division',()=>{
 const result=parseWordProblem('24 stickers are shared equally among 6 children. How many stickers does each child get?');
 assert.equal(result.operation,'division');assert.equal(result.result,4);
});
test('supports direct operation phrases and rejects ambiguous text',()=>{
 assert.equal(parseWordProblem('What is 12 plus 7?').result,19);
 assert.equal(parseWordProblem('A story mentions 12 apples and 7 oranges.').kind,'unsupported');
 assert.equal(parseWordProblem('10 items shared equally among zero people').kind,'unsupported');
});
test('supports compound number words and safely rejects malformed input',()=>{
 assert.equal(parseWordProblem('Twenty-one books and nineteen books are combined. What is the total?').result,40);
 assert.equal(parseWordProblem('').kind,'unsupported');
 assert.equal(parseWordProblem('x'.repeat(601)).kind,'unsupported');
});
