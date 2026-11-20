
"""Registro de eventos de seguridad de ReportesPro 3.0."""

import sqlite3
from datetime import datetime, timezone

from database.db import conectar



EVENTOS_PERMITIDOS = {
    "EMPRESA_ASIGNADA",
    "LOGIN_EXITOSO",
    "LOGIN_FALLIDO",
    "LOGIN_BLOQUEADO",
    "LOGOUT",
    "RECUPERACION_SOLICITADA",
    "PASSWORD_RESTABLECIDA",
    "CUENTA_ACTIVADA",
    "CUENTA_DESACTIVADA",
    "SESION_INVALIDADA",
    "ADMINISTRADOR_UNICO_CONFIGURADO",
    "ROL_ACTUALIZADO",
    "PASSWORD_CAMBIADA_LOCAL",
    "CUENTA_PRUEBA_CREADA",
}



def fecha_actual():
    return datetime.now(timezone.utc).isoformat()


def preparar_auditoria():
    """Crea la tabla de auditoría sin modificar otras tablas."""

    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria_seguridad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                evento TEXT NOT NULL,
                detalle TEXT,
                fecha TEXT NOT NULL,
                FOREIGN KEY (usuario_id)
                    REFERENCES usuarios(id)
            )
            """
        )

        conexion.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_auditoria_usuario_fecha
            ON auditoria_seguridad (
                usuario_id,
                fecha
            )
            """
        )


def registrar_evento(usuario_id, evento, detalle=None):
    """
    Registra un evento de seguridad.

    No almacenar contraseñas, tokens,
    enlaces de recuperación ni secretos TOTP.
    """

    with conectar() as conexion:
        registrar_evento_en_conexion(conexion, usuario_id, evento, detalle)


def registrar_evento_en_conexion(conexion, usuario_id, evento, detalle=None):
    """Permite confirmar el evento y la operación en la misma transacción."""
    if evento not in EVENTOS_PERMITIDOS:
        raise ValueError("Tipo de evento no permitido.")
    conexion.execute(
        """INSERT INTO auditoria_seguridad (usuario_id, evento, detalle, fecha)
           VALUES (?, ?, ?, ?)""",
        (usuario_id, evento, detalle, fecha_actual()),
    )


def listar_eventos(usuario_id=None, limite=100):
    """Consulta los eventos de auditoría."""

    limite = max(1, min(int(limite), 500))

    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row

        if usuario_id is None:
            filas = conexion.execute(
                """
                SELECT id, usuario_id, evento, detalle, fecha
                FROM auditoria_seguridad
                ORDER BY id DESC
                LIMIT ?
                """,
                (limite,),
            ).fetchall()
        else:
            filas = conexion.execute(
                """
                SELECT id, usuario_id, evento, detalle, fecha
                FROM auditoria_seguridad
                WHERE usuario_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (usuario_id, limite),
            ).fetchall()

    return [dict(fila) for fila in filas]
