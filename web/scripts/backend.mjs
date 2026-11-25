// Local API and authentication fixture only. Never used by the production Worker.
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { createServer as createTcpServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

process.chdir(fileURLToPath(new URL('..', import.meta.url)));
const require = createRequire(import.meta.url);
const wrangler = resolve(dirname(require.resolve('wrangler/package.json')), 'bin/wrangler.js');
const children = [];
let stopping = false;
async function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode !== null) continue;
    if (process.platform === 'win32') {
      await new Promise(done => spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' }).on('close', done));
    } else child.kill('SIGTERM');
  }
  process.exit(code);
}
process.on('SIGINT', () => void stop());
process.on('SIGTERM', () => void stop());
function launch(config, port) {
  const child = spawn(process.execPath, [wrangler, 'dev', '--config', config, '--ip', '127.0.0.1', '--port', String(port)], { stdio: 'inherit', windowsHide: true });
  children.push(child);
  child.on('error', error => { console.error(error.message); void stop(1); });
  child.on('exit', code => { if (!stopping) { console.error(`Local backend stopped (${code}).`); void stop(1); } });
}
async function freePort(port) {
  await new Promise((done, reject) => {
    const socket = createTcpServer();
    socket.once('error', () => reject(new Error(`Port ${port} is in use. Stop the previous dev/preview process, then retry npm run dev:backend.`)));
    socket.listen(port, '127.0.0.1', () => socket.close(done));
  });
}
async function ready(url, status, headers = {}) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    try { const response = await fetch(url, { headers, signal: AbortSignal.timeout(1500) }); await response.body?.cancel(); if (response.status === status) return; } catch {}
    await delay(300);
  }
  throw new Error(`Local backend did not become ready: ${url}`);
}
try {
  await Promise.all([8787, 8790].map(freePort));
  console.log('Starting the API and local test identity service…');
  launch('tests/auth-fixture.jsonc', 8790);
  await ready('http://127.0.0.1:8790/api/auth/me', 401);
  launch('wrangler.local.jsonc', 8787);
  await ready('http://127.0.0.1:8787/capitol-lens/api/session', 200, { Cookie: 'admin_token=local-preview-only' });
  console.log('\nBackend ready on http://127.0.0.1:8787\nStart the frontend separately: npm run dev\nPress Ctrl+C to stop the backend and local authentication fixture.\n');
} catch (error) {
  console.error(error.message);
  await stop(1);
}
