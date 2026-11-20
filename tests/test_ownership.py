import os
import unittest
from unittest.mock import patch

from database import db, ownership
from test_security import BaseDatosTemporal


class PropiedadTests(BaseDatosTemporal, unittest.TestCase):
    def empresa(self):
        with db.conectar() as con:
            return con.execute("INSERT INTO empresas(nombre) VALUES ('Empresa sintética')").lastrowid

    def test_asigna_conservando_reporte_y_aislamiento(self):
        eid = self.empresa()
        with db.conectar() as con:
            con.execute("INSERT INTO reportes(empresa_id,archivo) VALUES (?, 'sintetico.csv')", (eid,))
            antes = con.execute('SELECT * FROM reportes').fetchall()
        self.assertEqual(ownership.asignar_empresas(self.aid, {eid:self.uid}), 1)
        with db.conectar() as con:
            self.assertEqual(con.execute('SELECT * FROM reportes').fetchall(), antes)
        self.assertEqual(len(db.listar_reportes_usuario(self.uid, eid)), 1)
        with self.assertRaises(PermissionError):
            db.listar_reportes_usuario(self.aid, eid)

    def test_segunda_asignacion_fallida_revierte_todo(self):
        e1, e2 = self.empresa(), self.empresa()
        with self.assertRaises(ValueError):
            ownership.asignar_empresas(self.aid, {e1:self.uid,e2:99999})
        with db.conectar() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM empresas WHERE usuario_id IS NOT NULL').fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM auditoria_seguridad WHERE evento='EMPRESA_ASIGNADA'").fetchone()[0], 0)

    def test_auditoria_fallida_revierte(self):
        eid = self.empresa()
        with patch.object(ownership, 'registrar_evento_en_conexion', side_effect=RuntimeError('simulado')):
            with self.assertRaises(RuntimeError):
                ownership.asignar_empresas(self.aid, {eid:self.uid})
        with db.conectar() as con:
            self.assertIsNone(con.execute('SELECT usuario_id FROM empresas WHERE id=?', (eid,)).fetchone()[0])

    def test_rechaza_lan_usuario_y_empresa_con_propietario(self):
        eid = self.empresa()
        with self.assertRaises(PermissionError):
            ownership.asignar_empresas(self.uid, {eid:self.uid})
        with patch.dict(os.environ, {'REPORTESPRO_ACCESS_MODE':'lan'}):
            with self.assertRaises(PermissionError):
                ownership.asignar_empresas(self.aid, {eid:self.uid})
        ownership.asignar_empresas(self.aid, {eid:self.uid})
        with self.assertRaises(ValueError):
            ownership.asignar_empresas(self.aid, {eid:self.aid})
