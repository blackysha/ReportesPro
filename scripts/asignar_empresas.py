"""Vista previa por defecto; aplicar solo un mapa autorizado con respaldo previo."""

import argparse
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
import sqlite3
import uuid

from database import db
from database.backups import crear_respaldo
from database.ownership import asignar_empresas
from database.usuarios import autenticar_usuario
from auth.access_policy import administracion_habilitada


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asignar', action='append', required=True, metavar='EMPRESA:USUARIO')
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    mapa = {}
    for item in args.asignar:
        try:
            empresa, usuario = map(int, item.split(':'))
        except ValueError:
            parser.error('Formato requerido: EMPRESA:USUARIO con identificadores enteros.')
        if empresa <= 0 or usuario <= 0 or empresa in mapa:
            parser.error('Identificadores positivos y empresas sin repetir.')
        mapa[empresa] = usuario
    if not administracion_habilitada():
        parser.error('Ejecutar exclusivamente en modo local.')
    con = sqlite3.connect(db.DB_PATH.as_uri() + '?mode=ro', uri=True)
    try:
        for empresa, usuario in mapa.items():
            row = con.execute('SELECT usuario_id FROM empresas WHERE id=?', (empresa,)).fetchone()
            if row is None or row[0] is not None:
                parser.error('Empresa inexistente o con propietario; no se modificó nada.')
            if not con.execute('SELECT 1 FROM usuarios WHERE id=? AND activo=1', (usuario,)).fetchone():
                parser.error('Usuario inexistente o inactivo; no se modificó nada.')
            count = con.execute('SELECT COUNT(*) FROM reportes WHERE empresa_id=?', (empresa,)).fetchone()[0]
            print(f'Empresa #{empresa} -> usuario #{usuario}; {count} reportes conservados.')
    finally:
        con.close()
    if not args.aplicar:
        print('Vista previa: no se modificó la base. No une empresas ni modifica reportes.')
        return 0
    correo = input('Correo del administrador local: ')
    admin = autenticar_usuario(correo, getpass('Contraseña administrativa (oculta): '))
    if admin is None or admin['rol'] != 'admin':
        raise PermissionError('No se autenticó al administrador.')
    if input('Escribe ASIGNAR para confirmar el mapa mostrado: ') != 'ASIGNAR':
        print('Cancelado.')
        return 1
    nombre = datetime.now(timezone.utc).strftime('propiedad_%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:8] + '.db'
    crear_respaldo(db.DB_PATH, Path(__file__).resolve().parents[1] / 'backups' / nombre)
    cantidad = asignar_empresas(admin['id'], mapa)
    print(f'Asignación completada: {cantidad} empresas; respaldo previo validado.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, PermissionError, sqlite3.Error) as exc:
        print('Operación no completada. Tipo: ' + type(exc).__name__)
        raise SystemExit(1) from None
