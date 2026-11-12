
"""Servicio de correo electrónico de ReportesPro."""

import smtplib
import ssl
from email.message import EmailMessage

import streamlit as st


def enviar_correo(destinatario, asunto, contenido):
    """
    Envía un correo mediante Gmail SMTP.

    Las credenciales se obtienen de Streamlit Secrets.
    """

    configuracion = st.secrets["email"]

    remitente = configuracion["sender"]
    password = configuracion["app_password"]
    servidor = configuracion["smtp_host"]
    puerto = int(configuracion["smtp_port"])

    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    mensaje.set_content(contenido)

    contexto_ssl = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        servidor,
        puerto,
        context=contexto_ssl,
        timeout=20,
    ) as smtp:
        smtp.login(remitente, password)
        smtp.send_message(mensaje)

    return True


def enviar_correo_prueba(destinatario):
    asunto = "ReportesPro 3.0 - Prueba de correo"

    contenido = """
Hola:

Este mensaje confirma que la configuración
SMTP de ReportesPro 3.0 funciona correctamente.

Próximamente podrás recuperar tu contraseña
mediante un enlace seguro enviado a tu correo.

Equipo de ReportesPro.
"""

    return enviar_correo(
        destinatario=destinatario,
        asunto=asunto,
        contenido=contenido,
    )
