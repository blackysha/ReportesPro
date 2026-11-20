import hashlib
import hmac
import io
import json
import time
import unittest
from unittest.mock import Mock, patch

from database import db
from database.usuarios import obtener_version_sesion
from services.whatsapp import desvincular, generar_codigo, responder
from services.whatsapp_webhook import Meta, crear_webhook
from test_security import BaseDatosTemporal


class WhatsAppTests(BaseDatosTemporal, unittest.TestCase):
    numero = "18095550100"
    conteos = {
        "registros_totales": 1, "registros_validos": 1,
        "registros_invalidos": 0, "registros_con_incidencias": 0,
    }

    def setUp(self):
        super().setUp()
        self.version = obtener_version_sesion(self.uid)
        self.empresa = db.registrar_empresa_usuario(self.uid, "Empresa de prueba")
        self.privada = db.registrar_empresa_usuario(self.aid, "Otra empresa")
        self.reporte = db.guardar_reporte_usuario(
            self.uid, self.empresa, "ventas.csv", {**self.conteos, "ingresos": 240.50}
        )

    def test_vinculo_resumen_pdf_y_aislamiento(self):
        codigo = generar_codigo(self.uid, self.version, self.numero)
        self.assertIn("inválido", responder("18095550101", codigo)[0])
        self.assertIn("vinculado", responder(self.numero, codigo)[0])
        self.assertIn("inválido", responder(self.numero, codigo)[0])
        resumen, pdf = responder(self.numero, "Último reporte")
        self.assertIn("Ingresos: 240.50", resumen)
        self.assertIsNone(pdf)
        self.assertIn(f"PDF {self.empresa} {self.reporte}", resumen)
        self.assertIn("no está disponible", responder(self.numero, f"PDF {self.privada}")[0])
        db.guardar_reporte_usuario(self.uid, self.empresa, "posterior.csv", {
            **self.conteos, "perfiles": {"ventas": {"ingresos": 321.60}},
        })
        resumen, _ = responder(self.numero, "Último reporte")
        self.assertIn("posterior.csv", resumen)
        self.assertIn("Ventas · Ingresos: 321.60", resumen)
        self.assertTrue(responder(self.numero, f"PDF {self.empresa} {self.reporte}")[1].startswith(b"%PDF"))
        db.registrar_empresa_usuario(self.uid, "Segunda empresa")
        self.assertIn("Elige una empresa", responder(self.numero, "Último reporte")[0])
        desvincular(self.uid, self.version)
        self.assertIn("Vincula tu número", responder(self.numero, "Último reporte")[0])

    def test_expiracion_y_version(self):
        codigo = generar_codigo(self.uid, self.version, self.numero)
        with patch("services.whatsapp.time.time", return_value=time.time() + 601):
            self.assertIn("vencido", responder(self.numero, codigo)[0])
        codigo = generar_codigo(self.uid, self.version, self.numero)
        responder(self.numero, codigo)
        with db.conectar() as conexion:
            conexion.execute("UPDATE usuarios SET version_sesion = version_sesion + 1 WHERE id = ?", (self.uid,))
        self.assertIn("Vincula tu número", responder(self.numero, "Último reporte")[0])

    def test_webhook_verifica_firma_y_deduplica(self):
        enviar = Mock()
        webhook = crear_webhook("firma-sintetica", "token-sintetico", "123", enviar)
        iniciar = Mock()
        entorno = {
            "PATH_INFO": "/webhooks/whatsapp",
            "REQUEST_METHOD": "GET",
            "QUERY_STRING": "hub.mode=subscribe&hub.verify_token=token-sintetico&hub.challenge=12345",
        }
        self.assertEqual(webhook(entorno, iniciar), [b"12345"])
        evento = {"object": "whatsapp_business_account", "entry": [{"changes": [{
            "field": "messages", "value": {"metadata": {"phone_number_id": "123"}, "messages": [{
                "type": "text", "timestamp": str(int(time.time())), "from": self.numero,
                "id": "mensaje-de-prueba", "text": {"body": "Último reporte"},
            }]},
        }]}]}
        cuerpo = json.dumps(evento).encode()
        entorno.update(REQUEST_METHOD="POST", CONTENT_LENGTH=str(len(cuerpo)))
        entorno["wsgi.input"] = io.BytesIO(cuerpo)
        webhook(entorno, iniciar)
        self.assertEqual(iniciar.call_args.args[0], "403 Forbidden")
        enviar.assert_not_called()

        entorno["HTTP_X_HUB_SIGNATURE_256"] = "sha256=" + hmac.new(
            b"firma-sintetica", cuerpo, hashlib.sha256
        ).hexdigest()
        for _ in range(2):
            entorno["wsgi.input"] = io.BytesIO(cuerpo)
            webhook(entorno, iniciar)
            self.assertEqual(iniciar.call_args.args[0], "200 OK")
        enviar.assert_called_once()

    def test_envio_pdf_subido_por_id(self):
        meta = Meta("v99.0", "123", "token-sintetico")
        with patch.object(meta, "_post", side_effect=[{"id": "archivo"}, {}]) as post:
            meta.enviar(self.numero, "Resumen", b"%PDF")
        self.assertEqual(post.call_args_list[0].args, ("media",))
        self.assertEqual(post.call_args.kwargs["json"]["document"]["id"], "archivo")
