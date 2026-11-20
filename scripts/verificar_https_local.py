"""HTTPS y WebSocket reales en loopback, usando exclusivamente SQLite temporal."""

import asyncio
import json
from pathlib import Path
import os
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from websockets.asyncio.client import connect
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg


async def comprobar_websocket(url, context):
    ws = await connect(url, ssl=context, origin=url.replace('wss:', 'https:').split('/_stcore')[0],
                       subprotocols=['streamlit'], open_timeout=10, proxy=None, max_size=10*1024*1024)
    try:
        back = BackMsg()
        back.rerun_script.query_string = ''
        await ws.send(back.SerializeToString())
        deltas = 0
        for _ in range(200):
            raw = await asyncio.wait_for(ws.recv(), timeout=15)
            if raw is None:
                raise RuntimeError('WebSocket cerrado antes de renderizar.')
            forward = ForwardMsg()
            forward.ParseFromString(raw)
            if forward.HasField('delta'):
                deltas += 1
                if forward.delta.HasField('new_element') and forward.delta.new_element.HasField('exception'):
                    raise RuntimeError('La interfaz devolvió una excepción.')
            if forward.HasField('script_finished'):
                if not deltas:
                    raise RuntimeError('La interfaz no produjo elementos.')
                return deltas
        raise RuntimeError('No se completó el renderizado.')
    finally:
        await ws.close()


def main():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root/'.local/red.json').read_text(encoding='utf-8-sig'))
    context = ssl.create_default_context(cafile=config['certificate'])
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='reportespro-tls-') as directory:
        env = {**os.environ, 'REPORTESPRO_DB_PATH':str(Path(directory)/'sintetica.db'),
               'REPORTESPRO_ACCESS_MODE':'lan', 'LOGIN_SECURITY_KEY':secrets.token_hex(32)}
        command = [sys.executable, '-B', '-m', 'streamlit', 'run', 'web_app.py',
                   '--server.address','127.0.0.1', '--server.port',str(port), '--server.headless','true',
                   '--browser.gatherUsageStats','false', '--server.sslCertFile',config['certificate'],
                   '--server.sslKeyFile',config['private_key']]
        with open(os.devnull, 'w') as silent:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=silent, stderr=silent,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                base = f'https://127.0.0.1:{port}'
                deadline = time.monotonic()+25
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('Servidor temporal no disponible.')
                    try:
                        with urlopen(base+'/_stcore/health', context=context, timeout=2) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Servidor temporal no respondió.')
                        time.sleep(.2)
                deltas = asyncio.run(comprobar_websocket(base.replace('https:', 'wss:')+'/_stcore/stream',context))
                print(json.dumps({'https':True,'certificado_y_hostname_verificados':True,
                                  'websocket':True,'elementos_interfaz':deltas,
                                  'base_sintetica':True,'solo_loopback':True}))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Prueba HTTPS/WebSocket no completada. Tipo: ' + type(exc).__name__)
        raise SystemExit(1) from None
