"""Certificado de pruebas local; la clave privada permanece fuera de Git."""

import argparse
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import shutil
import ssl
import subprocess

from scripts.preparar_entrega import carpeta_privada

ROOT = Path(__file__).resolve().parents[1]


def preparar_tls(server_ip, private_directory):
    ip = ipaddress.ip_address(server_ip)
    privadas = tuple(ipaddress.ip_network(red) for red in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
    if ip.version != 4 or not any(ip in red for red in privadas):
        raise ValueError("Se requiere una IPv4 privada de la red local.")
    openssl = shutil.which("openssl")
    if openssl is None:
        candidato = Path("C:/Program Files/Git/usr/bin/openssl.exe")
        if candidato.is_file():
            openssl = str(candidato)
    if openssl is None:
        raise RuntimeError("OpenSSL no está disponible.")
    privado = carpeta_privada(private_directory)
    tls = privado / "_tls"
    tls.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    key = tls / ("servidor_" + stamp + ".key")
    cert = tls / ("servidor_" + stamp + ".crt")
    subprocess.run([
        openssl, "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-days", "30",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=ReportesPro prueba LAN",
        "-addext", f"subjectAltName=IP:{ip},IP:127.0.0.1,DNS:localhost",
        "-addext", "extendedKeyUsage=serverAuth",
        "-addext", "basicConstraints=critical,CA:FALSE",
        "-addext", "keyUsage=critical,digitalSignature,keyEncipherment",
    ], capture_output=True, check=True)
    subprocess.run([openssl, "verify", "-CAfile", str(cert), "-verify_ip", str(ip), str(cert)], capture_output=True, check=True)
    # Validar que Python/Streamlit puedan cargar el par sin mostrar la clave.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert, keyfile=key)
    fingerprint = subprocess.run([openssl, "x509", "-in", str(cert), "-noout", "-fingerprint", "-sha256", "-dates"], capture_output=True, check=True).stdout.decode("utf-8")
    identity = privado / "06_CERTIFICADO_RED.txt"
    identity.write_text(
        f"CERTIFICADO PÚBLICO DE PRUEBA LAN\nURL: https://{ip}:8502/\n{fingerprint}\n"
        "Comparar esta huella en cada laptop antes de confiar en el certificado autofirmado.\n"
        "El certificado caduca a los treinta días. No es un certificado público de producción.\n"
        "Se puede distribuir servidor_publico.crt; nunca distribuir _tls/ ni archivos .key.\n",
        encoding="utf-8-sig",
    )
    shutil.copyfile(cert, privado / "servidor_publico.crt")
    settings = ROOT / ".local"
    settings.mkdir(exist_ok=True)
    (settings / "red.json").write_text(json.dumps({"server_ip": str(ip), "certificate": str(cert), "private_key": str(key)}, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Preparar HTTPS local sin iniciar el servidor")
    parser.add_argument("--server-ip", required=True)
    parser.add_argument("--private-directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        preparar_tls(args.server_ip, args.private_directory)
    except Exception as exc:
        print("No se completó TLS. Tipo de error: " + type(exc).__name__)
        raise SystemExit(1) from None
    print("TLS de pruebas preparado y verificado. Clave privada fuera del repositorio.")


if __name__ == "__main__":
    main()
