import os
import unittest
from unittest.mock import patch

from auth.security import verificar_password
from database import db, admin_recovery, recovery
from test_security import BaseDatosTemporal


class RecuperacionLocalTests(BaseDatosTemporal, unittest.TestCase):
    def test_recupera_solo_admin_invalida_sesiones_y_preserva_otras_cuentas(self):
        with db.conectar() as con:
            before = con.execute('SELECT * FROM usuarios WHERE id=?', (self.uid,)).fetchone()
            old = con.execute('SELECT password_hash FROM usuarios WHERE id=?', (self.aid,)).fetchone()[0]
        password = 'NuevaClaveSintetica2026!'
        admin_recovery.recuperar_admin_local(self.aid, 0, password)
        with db.conectar() as con:
            new_hash, version = con.execute('SELECT password_hash,version_sesion FROM usuarios WHERE id=?', (self.aid,)).fetchone()
            self.assertEqual(before, con.execute('SELECT * FROM usuarios WHERE id=?', (self.uid,)).fetchone())
        self.assertEqual(version, 1)
        self.assertNotEqual(new_hash, old)
        self.assertTrue(verificar_password(password, new_hash))
        self.assertIsNone(recovery.solicitar_recuperacion('admin@example.invalid'))

    def test_rechaza_lan_usuario_version_antigua_y_password_corta(self):
        with patch.dict(os.environ, {'REPORTESPRO_ACCESS_MODE':'lan'}):
            with self.assertRaises(PermissionError):
                admin_recovery.recuperar_admin_local(self.aid, 0, self.password)
        for uid, version, password in [(self.uid,0,self.password),(self.aid,99,self.password),(self.aid,0,'corta')]:
            with self.assertRaises(ValueError):
                admin_recovery.recuperar_admin_local(uid, version, password)

    def test_fallo_auditoria_revierte_password_y_version(self):
        with db.conectar() as con:
            before = con.execute('SELECT * FROM usuarios').fetchall()
        with patch.object(admin_recovery, 'registrar_evento_en_conexion', side_effect=RuntimeError('simulado')):
            with self.assertRaises(RuntimeError):
                admin_recovery.recuperar_admin_local(self.aid, 0, 'NuevaClaveSintetica2026!')
        with db.conectar() as con:
            self.assertEqual(before, con.execute('SELECT * FROM usuarios').fetchall())
