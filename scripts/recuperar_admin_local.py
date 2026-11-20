"""Recuperación administrativa desde consola privada. Vista previa por defecto."""

import argparse
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
import sqlite3
import uuid

from auth.access_policy import administracion_habilitada
from database import db
from database.admin_recovery import recuperar_admin_local
from database.backups import crear_respaldo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    if not administracion_habilitada():
        parser.error('Solo se permite desde el entorno local de administración.')
    con = sqlite3.connect(db.DB_PATH.as_uri() + '?mode=ro', uri=True)
    try:
        admins = con.execute("SELECT id,version_sesion,activo FROM usuarios WHERE rol='admin'").fetchall()
    finally:
        con.close()
    if len(admins) != 1 or admins[0][2] != 1:
        raise ValueError('Se requiere un único administrador activo; revisar manualmente.')
    uid, version, _ = admins[0]
    print(f'Administrador #{uid}. Se conservarán roles, cuentas, empresas y reportes.')
    print('Al aplicar se cambiará únicamente su contraseña y se invalidarán sus sesiones y enlaces.')
    if not args.aplicar:
        print('Vista previa: ninguna modificación. Requiere autorización del propietario antes de aplicar.')
        return 0
    if input(f'Operación autorizada: escribe RECUPERAR {uid} para continuar: ') != f'RECUPERAR {uid}':
        print('Cancelado.')
        return 1
    password = getpass('Nueva contraseña, mínimo 12 caracteres (oculta): ')
    if password != getpass('Repetir contraseña (oculta): '):
        raise ValueError('Las contraseñas no coinciden.')
    if not 12 <= len(password) <= 1024:
        raise ValueError('Longitud no admitida.')
    nombre = datetime.now(timezone.utc).strftime('recuperacion_admin_%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8] + '.db'
    crear_respaldo(db.DB_PATH, Path(__file__).resolve().parents[1] / 'backups' / nombre)
    recuperar_admin_local(uid, version, password)
    print('Recuperación completada y auditada. Iniciar sesión desde localhost:8501 con la nueva contraseña.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, PermissionError, sqlite3.Error) as exc:
        print('No se completó la recuperación. Tipo: ' + type(exc).__name__)
        raise SystemExit(1) from None
