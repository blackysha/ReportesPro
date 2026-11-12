import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database.backups import crear_respaldo
from services import password_recovery_service as service


class OperacionesTests(unittest.TestCase):
    def test_respaldo_recuperable_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.db"
            dest = Path(folder) / "backup.db"
            c = sqlite3.connect(source)
            c.execute("CREATE TABLE ejemplo (valor TEXT)")
            c.execute("INSERT INTO ejemplo VALUES ('dato temporal')")
            c.commit()
            c.close()
            before = source.read_bytes()
            crear_respaldo(source, dest)
            c = sqlite3.connect(dest)
            self.assertEqual(c.execute("SELECT valor FROM ejemplo").fetchone()[0], "dato temporal")
            self.assertEqual(c.execute("PRAGMA quick_check").fetchone()[0], "ok")
            c.close()
            self.assertEqual(source.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                crear_respaldo(source, dest)
            with self.assertRaises(ValueError):
                crear_respaldo(source, source)

    def test_url_insegura_no_genera_token_ni_envia_correo(self):
        with patch.object(service, "solicitar_recuperacion") as solicitar, patch.object(service, "enviar_correo") as enviar:
            for url in ("http://example.invalid/", "https://user:password@example.invalid", "https://example.invalid/?token=x"):
                with self.assertRaises(ValueError):
                    service.enviar_recuperacion("prueba@example.invalid", url)
            solicitar.assert_not_called()
            enviar.assert_not_called()

    def test_recuperacion_envio_simulado_y_respuesta_generica(self):
        with patch.object(service, "solicitar_recuperacion", return_value=("token-sintetico", "prueba@example.invalid")), patch.object(service, "enviar_correo") as enviar:
            respuesta = service.enviar_recuperacion("prueba@example.invalid", "https://example.invalid/reportes")
            self.assertEqual(respuesta, service.MENSAJE_PUBLICO)
            self.assertNotIn("token-sintetico", respuesta)
            self.assertIn("https://example.invalid/reportes?recovery_token=token-sintetico", enviar.call_args.kwargs["contenido"])
