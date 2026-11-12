from pathlib import Path
import unittest
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from test_security import BaseDatosTemporal
from database import usuarios, admin
from database import db, auditoria


class InterfazTests(BaseDatosTemporal, unittest.TestCase):
    # Reutilizar únicamente la preparación aislada, sin repetir pruebas heredadas.
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "web_app.py"), default_timeout=20).run()

    def login(self, app, correo):
        app.text_input[0].set_value(correo)
        app.text_input[1].set_value(self.password)
        next(b for b in app.button if b.label == "Iniciar sesión").click().run()
        self.assertEqual(len(app.exception), 0)

    def test_interfaz_login_logout(self):
        app = self.app()
        self.assertEqual(len(app.exception), 0)
        self.login(app, "prueba@example.invalid")
        self.assertEqual(app.session_state["rp_usuario"]["id"], self.uid)
        next(b for b in app.button if "Cerrar sesión" in b.label).click().run()
        self.assertIsNone(app.session_state["rp_usuario"])
        self.assertEqual(len(app.exception), 0)

    def test_interfaz_rechaza_version_antigua(self):
        app = self.app()
        self.login(app, "prueba@example.invalid")
        admin.cambiar_estado_usuario(self.aid, self.uid, False)
        admin.cambiar_estado_usuario(self.aid, self.uid, True)
        app.run()
        self.assertIsNone(app.session_state["rp_usuario"])
        self.assertEqual(len(app.exception), 0)

    def test_interfaz_admin(self):
        app = self.app()
        self.login(app, "admin@example.invalid")
        self.assertTrue(any("Administración" in h.value for h in app.header))

    def test_interfaz_lan_rechaza_administrador(self):
        with patch.dict(os.environ, {"REPORTESPRO_ACCESS_MODE": "lan"}):
            app = self.app()
            self.login(app, "admin@example.invalid")
            self.assertIsNone(app.session_state["rp_usuario"])
            self.assertFalse(any("Administración" in h.value for h in app.header))
            self.login(app, "prueba@example.invalid")
            self.assertEqual(app.session_state["rp_usuario"]["id"], self.uid)

    def test_interfaz_registro(self):
        app = self.app()
        fields = {field.label: field for field in app.text_input}
        fields["Nombre completo"].set_value("Nueva cuenta temporal")
        # Las etiquetas de correo se repiten entre los formularios.
        next(field for field in app.text_input if field.key == "registro_correo").set_value("nueva@example.invalid")
        next(field for field in app.text_input if field.key == "registro_password").set_value(self.password)
        fields["Confirmar contraseña"].set_value(self.password)
        next(b for b in app.button if b.label == "Crear cuenta").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIsNotNone(usuarios.autenticar_usuario("nueva@example.invalid", self.password))

    def test_interfaz_invitado(self):
        app = self.app()
        next(b for b in app.button if "Continuar como invitado" in b.label).click().run()
        self.assertTrue(app.session_state["rp_invitado"])
        self.assertEqual(len(app.exception), 0)

    def test_interfaz_expira_por_inactividad(self):
        app = self.app()
        self.login(app, "prueba@example.invalid")
        app.session_state["rp_actividad"] -= 1801
        app.run()
        self.assertIsNone(app.session_state["rp_usuario"])

    def test_interfaz_logout_con_auditoria_indisponible(self):
        app = self.app()
        self.login(app, "prueba@example.invalid")
        with patch.object(auditoria, "registrar_evento", side_effect=RuntimeError("simulado")):
            next(b for b in app.button if "Cerrar sesión" in b.label).click().run()
        self.assertIsNone(app.session_state["rp_usuario"])
        self.assertEqual(len(app.exception), 0)

    def test_interfaz_resultados_csv_y_guardado(self):
        import ast
        tree = ast.parse((Path(__file__).resolve().parents[1] / "web_app.py").read_text(encoding="utf-8"))
        functions = "\n\n".join(ast.unparse(node) for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ("mostrar_resultados", "nombre_seguro", "crear_zip"))
        eid = db.registrar_empresa_usuario(self.uid, "Empresa de prueba")
        # Ejecutar las funciones reales de resultados con datos sintéticos en memoria.
        source = '''import streamlit as st
import pandas as pd
import io, zipfile
from main import analyze, make_excel, make_pdf, make_csv, LABELS
from database.db import guardar_reporte_usuario
''' + functions + f'''
st.session_state.rp_version_sesion = 0
if "actual" not in st.session_state:
    r = analyze("prueba.csv", b"producto,stock,costo\\nProducto,2,3\\n")
    totals = dict(registros_totales=1, registros_validos=1, registros_con_incidencias=0, hojas_procesadas=1, perfiles=r["indicators"])
    st.session_state.actual = dict(resultado=r, totales=totals, pdf=make_pdf(r,"Empresa"), excel=make_excel(r), guardado=False)
mostrar_resultados(st.session_state.actual, {{"id": {eid}, "nombre": "Empresa"}}, {{"id": {self.uid}}}, False, "prueba.csv")
'''
        app = AppTest.from_string(source, default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        next(r for r in app.radio if r.label == "Selecciona el formato de descarga").set_value("CSV").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("download_button")), 1)
        next(b for b in app.button if "Guardar análisis" in b.label).click().run()
        self.assertEqual(len(app.exception), 0)
        history = db.listar_reportes_usuario(self.uid, eid)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["indicadores"]["perfiles"]["inventario"]["valor_inventario"], 6)
