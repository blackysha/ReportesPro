import os
import sqlite3
import unittest
from unittest.mock import patch

from auth.access_policy import validar_direccion_servidor, modo_acceso
from auth.security import verificar_password
from database import usuarios, admin, db, provisioning, login_security
from test_security import BaseDatosTemporal


class PoliticaAccesoTests(BaseDatosTemporal, unittest.TestCase):
    def test_admin_no_puede_entrar_por_instancia_lan(self):
        with patch.dict(os.environ, {"REPORTESPRO_ACCESS_MODE": "lan"}):
            self.assertIsNone(usuarios.autenticar_usuario("admin@example.invalid", self.password))
            self.assertIsNone(usuarios.obtener_version_sesion(self.aid))
            self.assertFalse(admin.es_administrador(self.aid))
            with self.assertRaises(PermissionError):
                admin.cambiar_estado_usuario(self.aid, self.uid, False)
            self.assertIsNotNone(usuarios.autenticar_usuario("prueba@example.invalid", self.password))
        self.assertIsNotNone(usuarios.autenticar_usuario("admin@example.invalid", self.password))

    def test_bloqueos_lan_no_bloquean_consola_local(self):
        with patch.dict(os.environ, {"REPORTESPRO_ACCESS_MODE": "lan"}):
            for _ in range(5):
                usuarios.autenticar_usuario("admin@example.invalid", self.password)
            self.assertGreater(login_security.consultar_bloqueo("admin@example.invalid"), 0)
        self.assertEqual(login_security.consultar_bloqueo("admin@example.invalid"), 0)

    def test_local_requiere_loopback(self):
        validar_direccion_servidor("127.0.0.1")
        for address in ("0.0.0.0", "10.0.0.10", None):
            with self.assertRaises(RuntimeError):
                validar_direccion_servidor(address)
        with patch.dict(os.environ, {"REPORTESPRO_ACCESS_MODE": "otro"}):
            with self.assertRaises(RuntimeError):
                modo_acceso()

    def test_propietario_unico_y_otras_claves_preservadas(self):
        claves, cuentas = provisioning.preparar_accesos("prueba@example.invalid")
        self.assertEqual(len([c for c in cuentas if c["rol"] == "admin"]), 1)
        self.assertTrue(admin.es_administrador(self.uid))
        self.assertFalse(admin.es_administrador(self.aid))
        self.assertEqual(len([c for c in claves if c["rol"] == "usuario"]), 5)
        self.assertIsNotNone(usuarios.autenticar_usuario("admin@example.invalid", self.password))
        self.assertIsNone(usuarios.autenticar_usuario("prueba@example.invalid", self.password))
        with db.conectar() as c:
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE usuarios SET rol='admin' WHERE id=?", (self.aid,))

    def test_fallo_entrega_revierte_cambios(self):
        def falla(*_):
            raise OSError("error simulado al escribir TXT")
        with self.assertRaises(OSError):
            provisioning.preparar_accesos("prueba@example.invalid", entregar=falla)
        self.assertTrue(admin.es_administrador(self.aid))
        self.assertEqual(usuarios.obtener_version_sesion(self.uid), 0)
        with db.conectar() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0], 2)

    def test_reset_explicito_deja_cinco_usuarios_normales(self):
        claves, _ = provisioning.preparar_accesos("prueba@example.invalid", restablecer_existentes=True)
        self.assertEqual(len([c for c in claves if c["rol"] == "usuario" and c["activo"]]), 5)
