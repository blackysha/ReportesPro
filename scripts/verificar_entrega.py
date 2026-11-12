"""Cinco accesos concurrentes en una copia temporal, sin escribir en la base real."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
from unittest.mock import patch

from database import db, usuarios
from database.backups import crear_respaldo
from main import analyze, make_excel, make_pdf, make_csv


def verificar_entrega(carpeta):
    carpeta = Path(carpeta)
    with (carpeta / "accesos_5_laptops.csv").open(encoding="utf-8-sig", newline="") as f:
        accesos = list(csv.DictReader(f))
    with (carpeta / "admin_local.csv").open(encoding="utf-8-sig", newline="") as f:
        admin = next(csv.DictReader(f))
    if len(accesos) != 5 or len({a["correo"] for a in accesos}) != 5:
        raise ValueError("Se necesitan cinco cuentas distintas.")
    origen = db.DB_PATH
    with tempfile.TemporaryDirectory() as folder:
        copia = Path(folder) / "copia_pruebas.db"
        crear_respaldo(origen, copia)
        with patch.object(db, "DB_PATH", copia), patch.dict(os.environ, {"LOGIN_SECURITY_KEY": secrets.token_hex(32), "REPORTESPRO_ACCESS_MODE": "local"}):
            u = usuarios.autenticar_usuario(admin["correo"], admin["password"])
            if u is None:
                raise RuntimeError("La credencial administrativa entregada no coincide.")
            con = sqlite3.connect(copia)
            try:
                if con.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin'").fetchone()[0] != 1:
                    raise RuntimeError("No hay un único administrador.")
            finally:
                con.close()
            with patch.dict(os.environ, {"REPORTESPRO_ACCESS_MODE": "lan"}):
                if usuarios.autenticar_usuario(admin["correo"], admin["password"]) is not None:
                    raise RuntimeError("La LAN permitió una cuenta administradora.")

                def trabajar(acceso):
                    inicio = time.perf_counter()
                    user = usuarios.autenticar_usuario(acceso["correo"], acceso["password"])
                    if user is None:
                        raise RuntimeError("Una credencial de prueba no coincide.")
                    n = int(acceso["laptop"])
                    eid = db.registrar_empresa_usuario(user["id"], f"Empresa temporal laptop {n}", version_sesion=user["version_sesion"])
                    for perfil in ("ventas", "inventario", "clientes", "general"):
                        nombre = f"laptop_{n:02d}_{perfil}.csv"
                        result = analyze(nombre, (carpeta / "csv_pruebas" / nombre).read_bytes())
                        if not make_pdf(result, "Empresa sintética").startswith(b"%PDF") or not make_excel(result).startswith(b"PK") or not make_csv(result):
                            raise RuntimeError("No se completó una exportación.")
                        m = result["indicators"][perfil]
                        db.guardar_reporte_usuario(user["id"], eid, nombre, m, perfil, version_sesion=user["version_sesion"])
                    if len(db.listar_reportes_usuario(user["id"], eid)) != 4:
                        raise RuntimeError("Historial de prueba incompleto.")
                    return round(time.perf_counter() - inicio, 3)

                inicio = time.perf_counter()
                with ThreadPoolExecutor(max_workers=5) as pool:
                    tiempos = list(pool.map(trabajar, accesos))
                total = round(time.perf_counter() - inicio, 3)
                # Verificar aislamiento entre las cinco cuentas una vez terminada la ronda.
                for a in accesos:
                    u = usuarios.autenticar_usuario(a["correo"], a["password"])
                    propias = [e for e in db.listar_empresas_usuario(u["id"]) if e["nombre"].startswith("Empresa temporal laptop")]
                    if len(propias) != 1:
                        raise RuntimeError("No se verificó el aislamiento de empresas.")
    return {"usuarios_concurrentes": 5, "analisis": 20, "reportes_guardados_solo_en_copia": 20, "administrador_rechazado_en_lan": True, "segundos_por_usuario": tiempos, "segundos_totales": total, "base_real_modificada": False}


def main():
    parser = argparse.ArgumentParser(description="Verificar la entrega usando SQLite temporal")
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        resultado = verificar_entrega(args.private_directory)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    except Exception as exc:
        print("No se completó la verificación aislada. Tipo: " + type(exc).__name__)
        raise SystemExit(1) from None
    print(json.dumps(resultado))


if __name__ == "__main__":
    main()
