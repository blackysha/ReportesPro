
"""Servicio de recuperación de contraseñas de ReportesPro."""

import os
from urllib.parse import urlencode, urlsplit

from database.recovery import solicitar_recuperacion
from services.email_service import enviar_correo


MENSAJE_PUBLICO = (
    "Si existe una cuenta elegible asociada a ese correo, "
    "recibirás instrucciones para recuperar tu contraseña."
)


def enviar_recuperacion(correo, url_base=None):
    """
    Solicita un token y envía el enlace por Gmail.

    No devuelve el token al usuario.
    No revela si el correo está registrado.
    """

    if url_base is None:
        import streamlit as st
        url_base = os.environ.get("REPORTESPRO_PUBLIC_URL")
        if not url_base:
            url_base = st.secrets.get("REPORTESPRO_PUBLIC_URL", "http://localhost:8501/")
    parsed = urlsplit(url_base)
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.scheme not in ("https", "http") or (parsed.scheme == "http" and not local)):
        raise ValueError("Configura una URL pública HTTPS válida para recuperación.")
    resultado = solicitar_recuperacion(correo)

    if resultado is None:
        return MENSAJE_PUBLICO

    token, destinatario = resultado

    parametros = urlencode({
        "recovery_token": token
    })

    enlace = (
        f"{url_base.rstrip('/')}?{parametros}"
    )

    asunto = "ReportesPro - Recuperación de contraseña"

    contenido = f"""
Hola:

Hemos recibido una solicitud para recuperar
la contraseña de tu cuenta de ReportesPro.

Abre este enlace para establecer una nueva contraseña:

{enlace}

El enlace caduca en 15 minutos y solo puede utilizarse una vez.

Si no solicitaste este cambio, ignora este mensaje.

Equipo de ReportesPro.
"""

    enviar_correo(
        destinatario=destinatario,
        asunto=asunto,
        contenido=contenido,
    )

    return MENSAJE_PUBLICO
