import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from database import db, usuarios, admin, recovery, auditoria, login_security
from database.migracion_v3 import migrar_empresas


class BaseDatosTemporal:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch_db = patch.object(db, "DB_PATH", Path(self.temp.name) / "prueba.db")
        self.patch_db.start()
        self.addCleanup(self.patch_db.stop)
        self.patch_key = patch.dict(os.environ, {"LOGIN_SECURITY_KEY": "clave-exclusiva-para-pruebas-aisladas-0000", "REPORTESPRO_ACCESS_MODE": "local"})
        self.patch_key.start()
        self.addCleanup(self.patch_key.stop)
        usuarios.crear_tabla_usuarios()
        usuarios.preparar_estado_cuentas()
        usuarios.preparar_version_sesiones()
        admin.preparar_roles()
        db.crear_tablas()
        migrar_empresas()
        auditoria.preparar_auditoria()
        recovery.preparar_recuperacion()
        login_security.preparar_seguridad_login()
        self.password = "PruebaTemporalSegura2026!"
        self.uid = usuarios.registrar_usuario("Prueba", "prueba@example.invalid", self.password)
        self.aid = usuarios.registrar_usuario("Admin", "admin@example.invalid", self.password)
        with db.conectar() as c:
            c.execute("UPDATE usuarios SET rol = 'admin' WHERE id = ?", (self.aid,))


class SeguridadTests(BaseDatosTemporal, unittest.TestCase):
    def test_conexion_cierra_al_salir(self):
        with db.conectar() as c:
            c.execute("SELECT 1")
        with self.assertRaises(sqlite3.ProgrammingError):
            c.execute("SELECT 1")

    def test_login_devuelve_version_y_audita(self):
        u = usuarios.autenticar_usuario("PRUEBA@example.invalid", self.password)
        self.assertEqual(u["version_sesion"], 0)
        self.assertNotIn("password_hash", u)
        self.assertEqual(auditoria.listar_eventos(self.uid)[0]["evento"], "LOGIN_EXITOSO")

    def test_cambio_password_durante_verificacion_no_crea_sesion(self):
        def verificar(*_):
            with db.conectar() as c:
                c.execute("UPDATE usuarios SET version_sesion = version_sesion + 1 WHERE id = ?", (self.uid,))
            return True
        self.assertIsNone(login_security.autenticar_con_proteccion("prueba@example.invalid", self.password, verificar))

    def test_fallo_auditoria_revierte_desactivacion(self):
        with patch.object(admin, "registrar_evento_en_conexion", side_effect=RuntimeError("simulado")):
            with self.assertRaises(RuntimeError):
                admin.cambiar_estado_usuario(self.aid, self.uid, False)
        self.assertEqual(usuarios.obtener_version_sesion(self.uid), 0)

    def test_inicializacion_y_verificacion_no_migran_base_existente(self):
        from database.schema import preparar_base_datos
        with db.conectar() as c:
            c.execute("DROP TABLE intentos_login")
        with self.assertRaises(RuntimeError):
            preparar_base_datos()
        with db.conectar() as c:
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='intentos_login'").fetchone())

    def test_base_nueva_se_inicializa_completa(self):
        from database.schema import preparar_base_datos
        with patch.object(db, "DB_PATH", Path(self.temp.name) / "nueva.db"):
            preparar_base_datos()
            self.assertEqual(db.listar_empresas_usuario(1), [])

    def test_bloqueo_y_expiracion(self):
        correo = "prueba@example.invalid"
        now = login_security._ahora()
        with patch.object(login_security, "_ahora", return_value=now):
            for _ in range(5):
                self.assertIsNone(usuarios.autenticar_usuario(correo, "incorrecta"))
            self.assertIsNone(usuarios.autenticar_usuario(correo, self.password))
            self.assertGreater(login_security.consultar_bloqueo(correo), 0)
        with patch.object(login_security, "_ahora", return_value=now + timedelta(minutes=16)):
            self.assertIsNotNone(usuarios.autenticar_usuario(correo, self.password))
        events = [x["evento"] for x in auditoria.listar_eventos()]
        self.assertIn("LOGIN_BLOQUEADO", events)
        self.assertEqual(events.count("LOGIN_FALLIDO"), 4)

    def test_concurrencia_no_pierde_intentos(self):
        def intentar(_):
            return login_security.autenticar_con_proteccion(
                "prueba@example.invalid", "incorrecta", lambda *_: False
            )
        with ThreadPoolExecutor(max_workers=10) as pool:
            self.assertEqual(list(pool.map(intentar, range(10))), [None] * 10)
        with db.conectar() as c:
            self.assertEqual(c.execute("SELECT intentos FROM intentos_login").fetchone()[0], 5)

    def test_reactivar_no_revive_sesion(self):
        version = usuarios.obtener_version_sesion(self.uid)
        admin.cambiar_estado_usuario(self.aid, self.uid, False)
        self.assertIsNone(usuarios.obtener_version_sesion(self.uid))
        admin.cambiar_estado_usuario(self.aid, self.uid, True)
        self.assertGreater(usuarios.obtener_version_sesion(self.uid), version)
        eventos = [x["evento"] for x in auditoria.listar_eventos(self.uid)]
        self.assertIn("CUENTA_ACTIVADA", eventos)
        self.assertIn("CUENTA_DESACTIVADA", eventos)

    def test_ultimo_admin_no_puede_desactivarse(self):
        with self.assertRaises(ValueError):
            usuarios.desactivar_mi_cuenta(self.aid, self.password)
        self.assertTrue(admin.es_administrador(self.aid))

    def test_desactivacion_propia_invalida(self):
        usuarios.desactivar_mi_cuenta(self.uid, self.password)
        admin.cambiar_estado_usuario(self.aid, self.uid, True)
        self.assertGreater(usuarios.obtener_version_sesion(self.uid), 0)

    def test_usuario_no_admin_no_puede_cambiar_cuentas(self):
        with self.assertRaises(PermissionError):
            admin.cambiar_estado_usuario(self.uid, self.aid, False)

    def test_recuperacion_unica_invalida_sesiones(self):
        token, _ = recovery.solicitar_recuperacion("prueba@example.invalid")
        self.assertTrue(recovery.restablecer_password(token, "NuevaPasswordTemporal2026!"))
        self.assertFalse(recovery.restablecer_password(token, "OtraPasswordTemporal2026!"))
        self.assertEqual(usuarios.obtener_version_sesion(self.uid), 1)
        self.assertIsNone(usuarios.autenticar_usuario("prueba@example.invalid", self.password))
        self.assertIsNotNone(usuarios.autenticar_usuario("prueba@example.invalid", "NuevaPasswordTemporal2026!"))

    def test_recuperacion_caducada_y_limite(self):
        token, _ = recovery.solicitar_recuperacion("prueba@example.invalid")
        with patch.object(recovery, "fecha_actual", return_value=recovery.fecha_actual() + timedelta(minutes=16)):
            self.assertFalse(recovery.restablecer_password(token, self.password))
        self.assertIsNotNone(recovery.solicitar_recuperacion("prueba@example.invalid"))
        self.assertIsNotNone(recovery.solicitar_recuperacion("prueba@example.invalid"))
        self.assertIsNone(recovery.solicitar_recuperacion("prueba@example.invalid"))
        self.assertIsNone(recovery.solicitar_recuperacion("admin@example.invalid"))

    def test_aislamiento_empresas_y_reportes(self):
        eid = db.registrar_empresa_usuario(self.uid, "Empresa de prueba")
        indicadores = dict(registros_totales=1, registros_validos=1, registros_con_incidencias=0)
        db.guardar_reporte_usuario(self.uid, eid, "prueba.csv", indicadores)
        self.assertEqual(len(db.listar_reportes_usuario(self.uid, eid)), 1)
        self.assertEqual(db.listar_empresas_usuario(self.aid), [])
        with self.assertRaises(PermissionError):
            db.listar_reportes_usuario(self.aid, eid)
        with self.assertRaises(PermissionError):
            db.guardar_reporte_usuario(self.aid, eid, "prueba.csv", indicadores)
        with self.assertRaises(PermissionError):
            db.eliminar_empresa_usuario(self.aid, eid)

    def test_version_obsoleta_no_guarda_ni_consulta(self):
        eid = db.registrar_empresa_usuario(self.uid, "Empresa de prueba")
        indicadores = dict(registros_totales=1, registros_validos=1, registros_con_incidencias=0)
        admin.cambiar_estado_usuario(self.aid, self.uid, False)
        self.assertEqual(db.listar_empresas_usuario(self.uid), [])
        admin.cambiar_estado_usuario(self.aid, self.uid, True)
        with self.assertRaises(PermissionError):
            db.guardar_reporte_usuario(self.uid, eid, "prueba.csv", indicadores, version_sesion=0)
        with self.assertRaises(PermissionError):
            db.listar_reportes_usuario(self.uid, eid, version_sesion=0)
        with self.assertRaises(PermissionError):
            db.registrar_empresa_usuario(self.uid, "Otra empresa", version_sesion=0)


if __name__ == "__main__":
    unittest.main()
