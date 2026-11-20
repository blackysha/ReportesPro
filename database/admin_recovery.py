"""Recuperación fuera de la web, para el operador con acceso al archivo SQLite."""

from datetime import datetime, timezone

from auth.access_policy import administracion_habilitada
from auth.security import crear_hash_password
from database.db import conectar
from database.auditoria import registrar_evento_en_conexion
from database.login_security import _identificador


def recuperar_admin_local(admin_id, version_esperada, nueva_password):
    """No expuesto por HTTP. Requiere un procedimiento local autorizado."""
    if not administracion_habilitada():
        raise PermissionError("La recuperación administrativa solo se ejecuta localmente.")
    nuevo_hash = crear_hash_password(nueva_password)
    with conectar() as con:
        con.execute('BEGIN IMMEDIATE')
        admins = con.execute("SELECT id,correo,activo,version_sesion FROM usuarios WHERE rol='admin'").fetchall()
        if len(admins) != 1 or admins[0][0] != admin_id or admins[0][2] != 1 or admins[0][3] != version_esperada:
            raise ValueError('Administrador o versión inesperados; no se cambió ninguna cuenta.')
        con.execute('UPDATE usuarios SET password_hash=?,version_sesion=version_sesion+1 WHERE id=?', (nuevo_hash, admin_id))
        con.execute('UPDATE recuperaciones_password SET fecha_utilizacion=? WHERE usuario_id=? AND fecha_utilizacion IS NULL',
                    (datetime.now(timezone.utc).isoformat(), admin_id))
        con.execute('DELETE FROM intentos_login WHERE identificador=?', (_identificador(admins[0][1]),))
        registrar_evento_en_conexion(con, admin_id, 'PASSWORD_CAMBIADA_LOCAL',
                                    'Recuperación administrativa local; sesiones y enlaces anteriores invalidados')
