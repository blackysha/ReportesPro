
"""Protección contra fuerza bruta para ReportesPro 3.0."""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from database.db import conectar
from database.auditoria import registrar_evento_en_conexion
from auth.access_policy import administracion_habilitada


MAX_INTENTOS = 5
VENTANA_MINUTOS = 15
BLOQUEO_MINUTOS = 15


def _clave_seguridad():
    """Obtiene la clave privada de seguridad."""

    clave = os.environ.get("LOGIN_SECURITY_KEY")

    if not clave:
        try:
            import streamlit as st
            clave = st.secrets.get("LOGIN_SECURITY_KEY")
        except (FileNotFoundError, KeyError):
            clave = None

    if not isinstance(clave, str) or len(clave) < 32:
        raise RuntimeError(
            "Configura LOGIN_SECURITY_KEY con una clave "
            "aleatoria de al menos 32 caracteres."
        )

    return clave.encode("utf-8")


def _identificador(correo):
    """Genera un identificador HMAC del correo."""

    correo = correo.strip().lower()

    if not administracion_habilitada():
        correo = "lan:" + correo

    return hmac.new(
        _clave_seguridad(),
        correo.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _ahora():
    return datetime.now(timezone.utc)


def _leer_fecha(valor):
    return datetime.fromisoformat(valor) if valor else None


def preparar_seguridad_login():
    """Prepara la tabla de intentos de autenticación."""

    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS intentos_login (
                identificador TEXT PRIMARY KEY,
                intentos INTEGER NOT NULL DEFAULT 0,
                inicio_ventana TEXT NOT NULL,
                bloqueado_hasta TEXT
            )
            """
        )


def consultar_bloqueo(correo):
    """Devuelve los segundos restantes de bloqueo."""

    identificador = _identificador(correo)
    ahora = _ahora()

    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT bloqueado_hasta
            FROM intentos_login
            WHERE identificador = ?
            """,
            (identificador,),
        ).fetchone()

    if not fila or not fila[0]:
        return 0

    hasta = _leer_fecha(fila[0])

    return max(
        0,
        int((hasta - ahora).total_seconds()) + 1,
    )


def autenticar_con_proteccion(correo, password, verificar_password):
    """
    Autentica usuarios y controla los intentos fallidos
    dentro de una transacción SQLite.
    """

    correo = correo.strip().lower()
    identificador = _identificador(correo)

    # Argon2 no debe mantener bloqueadas las escrituras de todas las cuentas.
    # La transacción posterior vuelve a verificar bloqueo, hash y versión.
    with conectar() as lectura:
        lectura.row_factory = sqlite3.Row
        estado_previo = lectura.execute(
            "SELECT bloqueado_hasta FROM intentos_login WHERE identificador = ?",
            (identificador,),
        ).fetchone()
        bloqueado = bool(estado_previo and estado_previo[0] and _leer_fecha(estado_previo[0]) > _ahora())
        previo = lectura.execute(
            "SELECT id, password_hash, activo, version_sesion, rol FROM usuarios WHERE correo = ?",
            (correo,),
        ).fetchone()
    credenciales_validas = (
        not bloqueado and previo is not None and previo["activo"] == 1
        and (administracion_habilitada() or previo["rol"] != "admin")
        and verificar_password(password, previo["password_hash"])
    )

    with conectar() as conexion:
        conexion.execute("PRAGMA busy_timeout = 10000")
        conexion.execute("BEGIN IMMEDIATE")
        conexion.row_factory = sqlite3.Row

        ahora = _ahora()

        estado = conexion.execute(
            """
            SELECT intentos, inicio_ventana, bloqueado_hasta
            FROM intentos_login
            WHERE identificador = ?
            """,
            (identificador,),
        ).fetchone()

        # Comprobar si existe un bloqueo activo.
        if estado and estado["bloqueado_hasta"]:
            hasta = _leer_fecha(estado["bloqueado_hasta"])

            if hasta > ahora:
                registrar_evento_en_conexion(conexion, None, "LOGIN_BLOQUEADO")
                return None

            # CORRECCIÓN:
            # El bloqueo expiró. Eliminar los intentos
            # anteriores para comenzar una nueva ventana.
            conexion.execute(
                """
                DELETE FROM intentos_login
                WHERE identificador = ?
                """,
                (identificador,),
            )

            estado = None

        # Buscar al usuario sin modificar sus datos.
        usuario = conexion.execute(
            """
            SELECT
                id,
                nombre,
                correo,
                password_hash,
                activo,
                version_sesion,
                rol
            FROM usuarios
            WHERE correo = ?
            """,
            (correo,),
        ).fetchone()

        valido = (
            credenciales_validas
            and usuario is not None
            and usuario["activo"] == 1
            and (administracion_habilitada() or usuario["rol"] != "admin")
            and usuario["id"] == previo["id"]
            and usuario["password_hash"] == previo["password_hash"]
            and usuario["version_sesion"] == previo["version_sesion"]
        )

        # Si las credenciales son correctas,
        # limpiar los intentos fallidos.
        if valido:
            conexion.execute(
                """
                DELETE FROM intentos_login
                WHERE identificador = ?
                """,
                (identificador,),
            )

            registrar_evento_en_conexion(conexion, usuario["id"], "LOGIN_EXITOSO")
            return {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "correo": usuario["correo"],
                "version_sesion": usuario["version_sesion"],
            }

        # Registrar un intento fallido.
        intentos = 0
        inicio = ahora

        if estado:
            inicio_anterior = _leer_fecha(
                estado["inicio_ventana"]
            )

            if (
                ahora - inicio_anterior
                < timedelta(minutes=VENTANA_MINUTOS)
            ):
                intentos = estado["intentos"]
                inicio = inicio_anterior

        intentos += 1
        bloqueado_hasta = None

        # Activar bloqueo al quinto intento.
        if intentos >= MAX_INTENTOS:
            bloqueado_hasta = (
                ahora + timedelta(minutes=BLOQUEO_MINUTOS)
            ).isoformat()

        conexion.execute(
            """
            INSERT INTO intentos_login (
                identificador,
                intentos,
                inicio_ventana,
                bloqueado_hasta
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(identificador) DO UPDATE SET
                intentos = excluded.intentos,
                inicio_ventana = excluded.inicio_ventana,
                bloqueado_hasta = excluded.bloqueado_hasta
            """,
            (
                identificador,
                intentos,
                inicio.isoformat(),
                bloqueado_hasta,
            ),
        )

        registrar_evento_en_conexion(
            conexion, None,
            "LOGIN_BLOQUEADO" if bloqueado_hasta else "LOGIN_FALLIDO",
        )
        return None
