import { execFileSync } from 'node:child_process';
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const auth=await readFile(new URL('../owner-auth.js',import.meta.url),'utf8');
const app=await readFile(new URL('../app.js',import.meta.url),'utf8');
const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
test('owner auth supports password sign-in, token refresh and sign-out',()=>{assert.ok(auth.includes('grant_type=password'));assert.ok(auth.includes('grant_type=refresh_token'));assert.ok(auth.includes('/auth/v1/logout'));assert.ok(auth.includes(\"action:'health'\"));});
test('owner access is checked by the protected Edge Function',()=>{assert.ok(auth.includes('/functions/v1/training-control'));assert.ok(auth.includes('status===403'));assert.ok(!auth.includes('ULTRON_OWNER_USER_ID'));assert.ok(!auth.includes('service_role'));});
test('public pages remain available and registration is not exposed',()=>{assert.ok(html.includes('data-page=') && html.includes('owner'));assert.ok(app.includes('signInOwner'));assert.ok(!app.includes('signUp('));assert.ok(!html.includes('data-page=signup'));});

test('owner auth and app modules pass JavaScript syntax validation',()=>{execFileSync(process.execPath,['--check',new URL('../owner-auth.js',import.meta.url).pathname]);execFileSync(process.execPath,['--check',new URL('../app.js',import.meta.url).pathname]);});
