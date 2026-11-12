import unittest
from unittest.mock import Mock

from auth.sessions import iniciar_sesion, sesion_expirada, limpiar_sesion, IDLE_SECONDS, MAX_SECONDS


class SesionesTests(unittest.TestCase):
    def setUp(self):
        self.estado = {"datos_privados": "temporal"}
        iniciar_sesion(self.estado, {"id": 1, "version_sesion": 2}, ahora=100)

    def test_inicio_limpia_estado_previo(self):
        self.assertNotIn("datos_privados", self.estado)
        self.assertEqual(self.estado["rp_version_sesion"], 2)

    def test_inactividad(self):
        self.assertTrue(sesion_expirada(self.estado, ahora=100 + IDLE_SECONDS))

    def test_actividad_y_duracion_absoluta(self):
        for ahora in range(101, 100 + MAX_SECONDS, 100):
            self.assertFalse(sesion_expirada(self.estado, ahora=ahora))
        self.assertTrue(sesion_expirada(self.estado, ahora=100 + MAX_SECONDS))

    def test_sesion_antigua_sin_reloj_es_invalida(self):
        self.assertTrue(sesion_expirada({"rp_usuario": {"id": 1}}, ahora=100))

    def test_logout_limpia_aunque_falle_auditoria(self):
        registrar = Mock(side_effect=RuntimeError("fallo simulado"))
        with self.assertLogs("auth.sessions", level="ERROR"):
            limpiar_sesion(self.estado, registrar)
        self.assertEqual(self.estado, {})
        registrar.assert_called_once_with(1, "LOGOUT", "Sesión finalizada")


if __name__ == "__main__":
    unittest.main()
