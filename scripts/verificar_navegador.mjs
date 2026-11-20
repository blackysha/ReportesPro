// Prueba visual local: solo datos sintéticos y loopback. No publica la aplicación.
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, rm, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const temp = await mkdtemp(path.join(tmpdir(), 'reportespro-browser-'));
const output = path.join(root, 'backups', `navegador_${Date.now()}`);
await mkdir(output, { recursive: true });
const env = { ...process.env, REPORTESPRO_DB_PATH: path.join(temp, 'sintetica.db'),
  REPORTESPRO_ACCESS_MODE: 'lan', LOGIN_SECURITY_KEY: 'solo-prueba-aislada-de-navegador-2026-000000' };
const children = [];
let socket;
async function freePort() {
  const server = net.createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { const result = await fn(); if (result) return result; } catch {} await pause(200); }
  throw new Error('Tiempo de espera agotado');
}
try {
  const port = await freePort(), debugPort = await freePort();
  const app = spawn(path.join(root, '.venv/Scripts/python.exe'), ['-B', '-m', 'streamlit', 'run', 'web_app.py',
    '--server.address', '127.0.0.1', '--server.port', String(port), '--server.headless', 'true',
    '--browser.gatherUsageStats', 'false'], { cwd: root, env, windowsHide: true, stdio: 'ignore' });
  children.push(app);
  await until(async () => (await fetch(`http://127.0.0.1:${port}/_stcore/health`)).ok);
  const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new',
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(temp, 'chrome')}`,
    '--no-first-run', '--disable-background-networking', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  children.push(chrome);
  const tabs = await until(async () => (await fetch(`http://127.0.0.1:${debugPort}/json/list`)).json());
  socket = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    const entry = pending.get(message.id);
    if (entry) { pending.delete(message.id); clearTimeout(entry.timer); message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result); }
  };
  function cdp(method, params = {}) {
    return new Promise((resolve, reject) => {
      const request = ++id;
      const timer = setTimeout(() => { pending.delete(request); reject(new Error(`CDP timeout: ${method}`)); }, 15000);
      pending.set(request, { resolve, reject, timer });
      socket.send(JSON.stringify({ id: request, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true });
    if (result.exceptionDetails) throw new Error('Error al evaluar el navegador');
    return result.result.value;
  }
  await cdp('Page.enable');
  await cdp('Page.navigate', { url: `http://127.0.0.1:${port}/` });
  await until(() => evaluate(`document.body.innerText.includes('Iniciar sesión')`));
  const results = [];
  for (const width of [360, 390, 640, 1366]) {
    await cdp('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 641 });
    await pause(500);
    const metrics = await evaluate(`(() => {
      const tabs = [...document.querySelectorAll('[role="tab"]')].map(e => { const r=e.getBoundingClientRect(); return { label:e.innerText, x:r.x, right:r.right, height:r.height }; });
      const inputs = [...document.querySelectorAll('input')].filter(e=>e.getBoundingClientRect().width).map(e=>parseFloat(getComputedStyle(e).fontSize));
      const errors = [...document.querySelectorAll('[data-testid="stException"]')].length;
      const horizontalOverflow = document.documentElement.scrollWidth > innerWidth + 1;
      return { tabs, inputs, errors, horizontalOverflow, viewport:innerWidth };
    })()`);
    const success = metrics.errors === 0 && !metrics.horizontalOverflow && metrics.tabs.length >= 4
      && metrics.tabs.every(t => t.x >= -1 && t.right <= metrics.viewport + 1 && (width > 640 || t.height >= 44))
      && (width > 640 || metrics.inputs.every(size => size >= 16));
    const shot = await cdp('Page.captureScreenshot', { format: 'png' });
    await writeFile(path.join(output, `acceso_${width}.png`), Buffer.from(shot.data, 'base64'));
    results.push({ width, success, ...metrics });
  }
  await evaluate(`([...document.querySelectorAll('button')].find(e=>e.innerText.includes('Continuar como invitado'))).click()`);
  await until(() => evaluate(`!document.body.innerText.includes('Continuar como invitado')`));
  const guest = await evaluate(`({ errors:document.querySelectorAll('[data-testid="stException"]').length, uploader:!!document.querySelector('[data-testid="stFileUploader"]') })`);
  const report = { syntheticDatabase: true, loopbackOnly: true, viewports: results, guest,
    passed: results.every(r => r.success) && guest.errors === 0 && guest.uploader,
    limits: 'Chrome con emulación de tamaños; no sustituye Android/iPhone ni cinco PC físicas.' };
  await writeFile(path.join(output, 'resultado.json'), JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify({ passed:report.passed, viewports:results.map(r=>({width:r.width,success:r.success})), guest, artifacts:output }));
  if (!report.passed) process.exitCode = 1;
} catch (error) {
  await writeFile(path.join(output, 'resultado.json'), JSON.stringify({ passed:false, error:error.message,
    limits:'No se obtuvo una validación visual; revisar permisos y disponibilidad de Chrome.' }, null, 2));
  console.error('Prueba visual no completada: ' + error.message);
  process.exitCode = 1;
} finally {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({id:999999,method:'Browser.close'}));
    await pause(300);
    socket.close();
  }
  for (const child of children.reverse()) { if (child.exitCode === null) child.kill(); }
  await pause(1000);
  const resolvedTemp = path.resolve(temp);
  if (path.dirname(resolvedTemp) !== path.resolve(tmpdir()) || !path.basename(resolvedTemp).startsWith('reportespro-browser-')) {
    throw new Error('Ruta temporal inesperada: se conserva para revisión');
  }
  await rm(resolvedTemp, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 });
}
