"""Separación entre consola local y acceso de usuarios desde la LAN."""

import os


def modo_acceso():
    modo = os.environ.get("REPORTESPRO_ACCESS_MODE", "local").strip().lower()
    if modo not in {"local", "lan"}:
        raise RuntimeError("Modo de acceso no reconocido.")
    return modo


def administracion_habilitada():
    return modo_acceso() == "local"


def validar_direccion_servidor(direccion):
    # No usar IP de cliente, cabeceras HTTP ni huella del navegador como identidad.
    # La instancia administrativa debe escuchar exclusivamente en loopback.
    if administracion_habilitada() and direccion not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("La administración requiere un servidor limitado a localhost.")
