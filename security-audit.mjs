import { readFile } from 'node:fs/promises';

const paths = [
  'index.html',
  'app.js',
  'preferences.js',
  'graph-tool.js',
  'math-engine.js',
  'math-tools.js',
  'memory-store.js',
  'runtime-config.js',
  'runtime-status.js',
  'word-problems.js',
  'provider-directory.js',
  'supabase-integration.js',
  'styles.css'
];
const problems = [];
const sources = new Map();

for (const path of paths) {
  try {
    sources.set(path, await readFile(new URL('./' + path, import.meta.url), 'utf8'));
  } catch (error) {
    problems.push(path + ': could not read required frontend source (' + error.message + ')');
  }
}

const combined = [...sources.entries()]
  .filter(([path]) => path.endsWith('.js') || path.endsWith('.html'))
  .map(([, source]) => source)
  .join('\n');
const secretPatterns = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
  /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
  /\bsb_secret_[A-Za-z0-9_-]{12,}\b/,
  /\bsk-(?:proj|ant)-[A-Za-z0-9_-]{16,}\b/
];
for (const pattern of secretPatterns) {
  if (pattern.test(combined)) problems.push('Frontend source contains a token/private-key pattern matching ' + pattern);
}

for (const [path, source] of sources) {
  if (/\beval\s*\(|\bnew\s+Function\s*\(|\bdocument\.write\s*\(/.test(source)) {
    problems.push(path + ': unsafe dynamic-code or document.write primitive detected');
  }
  if (/\b(?:XMLHttpRequest|WebSocket|EventSource)\b/.test(source)) {
    problems.push(path + ': unreviewed raw network transport detected');
  }
  if (/api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|api\.cohere\.ai|bedrock-runtime\.[a-z0-9-]+\.amazonaws\.com/i.test(source)) {
    problems.push(path + ': external AI API endpoint detected');
  }
}

const html = sources.get('index.html') || '';
const app = sources.get('app.js') || '';
const integration = sources.get('supabase-integration.js') || '';
const css = sources.get('styles.css') || '';
if (/data-page="(?:owner|signup|pairing)"/i.test(html + app)) problems.push('Public frontend contains an owner, signup, or pairing navigation route.');
if (/id="training-(?:start|pause|stop|resume|save)"/i.test(html + app)) problems.push('Public frontend contains a training job mutation control.');
if (/@import\s+url\s*\(\s*['"]?https?:/i.test(css)) problems.push('Stylesheet imports a remote resource; use local/system assets instead.');
if (!/const\s+PUBLISHABLE_KEY\s*=\s*['"]sb_publishable_[^'"]+['"]/.test(integration)) {
  problems.push('Supabase browser integration does not declare a publishable (browser-safe) key.');
}
if (/service_role|sb_secret_/.test(integration)) problems.push('Supabase browser integration contains a server-only key marker.');
const appFetches = app.match(/\bfetch\s*\(/g) || [];
if (appFetches.length !== 1 || !app.includes("fetch('./servers.json'")) {
  problems.push('Unexpected direct fetch surface in app.js; expected only the same-origin servers.json request.');
}
if (!integration.includes('/functions/v1/training-control') || !integration.includes("action: 'public_status'")) {
  problems.push('Supabase browser integration does not match the fixed public_status endpoint contract.');
}
if (problems.length) {
  process.stderr.write('ULTRON focused security audit failed:\n- ' + problems.join('\n- ') + '\n');
  process.exitCode = 1;
} else {
  process.stdout.write('ULTRON focused static security audit passed. This is a heuristic source scan, not a security certification.\n');
}
