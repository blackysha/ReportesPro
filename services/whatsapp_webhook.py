"""Webhook de prueba para WhatsApp Cloud API. Ejecutar como módulo."""

import hashlib
import hmac
import json
import logging
import os
import re
import time
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

import requests

from services.whatsapp import _almacen, responder

logger = logging.getLogger(__name__)
RUTA = "/webhooks/whatsapp"
VIGENCIA = 24 * 60 * 60


class Meta:
    def __init__(self, version, numero_id, token):
        if not re.fullmatch(r"v[0-9]+\.[0-9]+", version) or not numero_id.isdecimal():
            raise ValueError("Revisa la versión Graph y el ID del número de prueba.")
        self.base = f"https://graph.facebook.com/{version}/{numero_id}"
        self.headers = {"Authorization": f"Bearer {token}"}

    def _post(self, ruta, **datos):
        respuesta = requests.post(
            f"{self.base}/{ruta}", headers=self.headers, timeout=(4, 12),
            allow_redirects=False, **datos,
        )
        if not 200 <= respuesta.status_code < 300:
            raise RuntimeError("Meta rechazó la solicitud.")
        return respuesta.json()

    def enviar(self, numero, texto, pdf):
        mensaje = {"messaging_product": "whatsapp", "to": numero}
        if pdf is None:
            mensaje.update(type="text", text={"body": texto})
        else:
            archivo = self._post(
                "media", data={"messaging_product": "whatsapp"},
                files={"file": ("ReportePro.pdf", pdf, "application/pdf")},
            )
            mensaje.update(type="document", document={
                "id": archivo["id"], "filename": "ReportePro.pdf", "caption": texto,
            })
        self._post("messages", json=mensaje)


def _mensajes(evento, numero_id):
    if evento.get("object") != "whatsapp_business_account":
        return
    for entrada in evento.get("entry", []):
        for cambio in entrada.get("changes", []):
            if cambio.get("field") != "messages":
                continue
            datos = cambio["value"]
            if datos.get("metadata", {}).get("phone_number_id") != numero_id:
                continue
            for mensaje in datos.get("messages", []):
                if mensaje.get("type") == "text":
                    yield mensaje


def _atender(evento, numero_id, enviar):
    mensajes = list(_mensajes(evento, numero_id))
    if not mensajes:
        return
    with _almacen() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_recibidos (
                id TEXT PRIMARY KEY, caduca INTEGER NOT NULL
            )
        """)
        ahora = int(time.time())
        conexion.execute("DELETE FROM whatsapp_recibidos WHERE caduca <= ?", (ahora,))
        conexion.commit()
        for mensaje in mensajes:
            enviado = int(mensaje["timestamp"])
            if not ahora - VIGENCIA < enviado <= ahora + 300:
                continue
            id_mensaje = mensaje["id"]
            if conexion.execute(
                "SELECT 1 FROM whatsapp_recibidos WHERE id = ?", (id_mensaje,)
            ).fetchone():
                continue
            numero = mensaje["from"]
            texto, pdf = responder(numero, mensaje["text"]["body"])
            enviar(numero, texto, pdf)
            conexion.execute(
                "INSERT INTO whatsapp_recibidos VALUES (?, ?)", (id_mensaje, enviado + VIGENCIA)
            )
            conexion.commit()


def crear_webhook(secreto, verificar, numero_id, enviar):
    def webhook(entorno, iniciar):
        def contestar(estado, cuerpo=b""):
            iniciar(estado, [("Content-Type", "text/plain; charset=utf-8"),
                             ("Content-Length", str(len(cuerpo)))])
            return [cuerpo]

        if entorno["PATH_INFO"] != RUTA:
            return contestar("404 Not Found")
        if entorno["REQUEST_METHOD"] == "GET":
            consulta = parse_qs(entorno["QUERY_STRING"])
            candidato = consulta.get("hub.verify_token", [""])[0]
            modo = consulta.get("hub.mode", [""])[0]
            reto = consulta.get("hub.challenge", [""])[0]
            if modo == "subscribe" and reto and hmac.compare_digest(
                candidato.encode("utf8"), verificar.encode("utf8")
            ):
                return contestar("200 OK", reto.encode("utf8"))
            return contestar("403 Forbidden")
        if entorno["REQUEST_METHOD"] != "POST":
            return contestar("405 Method Not Allowed")

        try:
            longitud = int(entorno.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return contestar("400 Bad Request")
        if not 0 < longitud <= 1024 * 1024:
            return contestar("413 Content Too Large")
        cuerpo = entorno["wsgi.input"].read(longitud)
        firma = entorno.get("HTTP_X_HUB_SIGNATURE_256", "").encode("utf8")
        esperada = b"sha256=" + hmac.new(secreto.encode("utf8"), cuerpo, hashlib.sha256).hexdigest().encode("ascii")
        if not hmac.compare_digest(firma, esperada):
            return contestar("403 Forbidden")

        try:
            _atender(json.loads(cuerpo), numero_id, enviar)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            logger.warning("Evento de WhatsApp inválido (%s)", type(exc).__name__)
            return contestar("400 Bad Request")
        except Exception as exc:
            logger.warning("No se pudo procesar WhatsApp (%s)", type(exc).__name__)
            return contestar("503 Service Unavailable")
        return contestar("200 OK")

    return webhook


class SinRegistroDeSolicitudes(WSGIRequestHandler):
    def log_message(self, format, *args):
        # La URL de verificación contiene el token.
        pass


def main():
    variables = (
        "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_GRAPH_VERSION", "WHATSAPP_ACCESS_TOKEN",
    )
    if faltantes := [nombre for nombre in variables if not os.environ.get(nombre)]:
        raise SystemExit("Falta configurar " + ", ".join(faltantes))
    secreto, verificar, numero_id, version, token = (os.environ[nombre] for nombre in variables)
    os.environ["REPORTESPRO_ACCESS_MODE"] = "lan"
    api = Meta(version, numero_id, token)
    webhook = crear_webhook(secreto, verificar, numero_id, api.enviar)
    with make_server("127.0.0.1", 8503, webhook, handler_class=SinRegistroDeSolicitudes) as servidor:
        print(f"Webhook de prueba disponible localmente en {RUTA}", flush=True)
        servidor.serve_forever()


if __name__ == "__main__":
    main()
