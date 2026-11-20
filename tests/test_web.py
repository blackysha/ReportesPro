from pathlib import Path
from datetime import date
from types import SimpleNamespace
import unittest
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from test_security import BaseDatosTemporal
from database import usuarios, admin
from database import db, auditoria, recovery
from services.password_recovery_service import MENSAJE_PUBLICO


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

    def solicitar_recuperacion_interfaz(self, correo):
        app = self.app()
        next(f for f in app.text_input if f.key == 'correo_recuperacion').set_value(correo)
        next(b for b in app.button if b.label == 'Enviar enlace').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(item.value == MENSAJE_PUBLICO for item in app.info))
        return app

    def app_restauracion(self, token):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'web_app.py'), default_timeout=20)
        app.query_params['recovery_token'] = token
        return app.run()

    def cambiar_password_interfaz(self, app, password, confirmacion=None):
        next(f for f in app.text_input if f.label == 'Nueva contraseña').set_value(password)
        next(f for f in app.text_input if f.label == 'Confirmar contraseña').set_value(password if confirmacion is None else confirmacion)
        next(b for b in app.button if b.label == 'Cambiar contraseña').click().run()
        self.assertEqual(len(app.exception), 0)

    def test_recuperacion_completa_desde_interfaz_y_rechazo_de_reutilizacion(self):
        import re
        from urllib.parse import urlsplit, parse_qs
        with patch.dict(os.environ, {'REPORTESPRO_PUBLIC_URL':'https://example.invalid/'}), \
                patch('services.password_recovery_service.enviar_correo') as enviar:
            self.solicitar_recuperacion_interfaz('prueba@example.invalid')
        enviar.assert_called_once()
        enlace = re.search(r'https://[^\s]+', enviar.call_args.kwargs['contenido']).group(0)
        self.assertEqual(urlsplit(enlace).hostname, 'example.invalid')
        token = parse_qs(urlsplit(enlace).query)['recovery_token'][0]
        nueva = 'NuevaClaveInterfaz2026!'
        app = self.app_restauracion(token)
        self.cambiar_password_interfaz(app, nueva)
        self.assertTrue(any('Contraseña actualizada' in item.value for item in app.success))
        self.assertNotIn('recovery_token', app.query_params)
        self.assertEqual(usuarios.obtener_version_sesion(self.uid), 1)
        self.assertIsNone(usuarios.autenticar_usuario('prueba@example.invalid', self.password))
        self.assertIsNotNone(usuarios.autenticar_usuario('prueba@example.invalid', nueva))
        replay = self.app_restauracion(token)
        self.cambiar_password_interfaz(replay, 'OtraClaveInterfaz2026!')
        self.assertTrue(any('Enlace inválido' in item.value for item in replay.error))
        self.assertIsNotNone(usuarios.autenticar_usuario('prueba@example.invalid', nueva))

    def test_recuperacion_admin_e_inexistente_no_envian_ni_generan_tokens(self):
        with patch('services.password_recovery_service.enviar_correo') as enviar:
            for correo in ('admin@example.invalid','ausente@example.invalid'):
                self.solicitar_recuperacion_interfaz(correo)
            enviar.assert_not_called()
        with db.conectar() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM recuperaciones_password').fetchone()[0], 0)

    def test_recuperacion_error_smtp_mantiene_respuesta_generica(self):
        with patch('services.password_recovery_service.enviar_correo', side_effect=OSError('detalle-privado-sintetico')):
            app = self.solicitar_recuperacion_interfaz('prueba@example.invalid')
        for collection in (app.error, app.info, app.warning):
            self.assertFalse(any('detalle-privado-sintetico' in item.value for item in collection))

    def test_restauracion_no_consume_enlace_con_confirmacion_distinta(self):
        token, _ = recovery.solicitar_recuperacion('prueba@example.invalid')
        app = self.app_restauracion(token)
        self.cambiar_password_interfaz(app, 'NuevaClaveInterfaz2026!', 'DiferenteClave2026!')
        self.assertTrue(any('no coinciden' in item.value for item in app.error))
        self.assertEqual(usuarios.obtener_version_sesion(self.uid), 0)
        self.assertTrue(recovery.restablecer_password(token, 'NuevaClaveInterfaz2026!'))

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

    def test_cierre_semanal_concilia_y_guarda_desde_el_panel(self):
        eid = db.registrar_empresa_usuario(self.uid, "Distribuidora de prueba")
        files = [
            SimpleNamespace(name="sucursal-a.csv", getvalue=lambda: b"fecha,producto,cantidad,precio\n2026-11-09,A,2,10\n"),
            SimpleNamespace(name="sucursal-b.csv", getvalue=lambda: b"fecha,producto,cantidad,precio,moneda\n2026-11-15,B,3,5,EUR\n"),
        ]
        with patch("streamlit.file_uploader", return_value=files):
            app = self.app()
            self.login(app, "prueba@example.invalid")
            app.date_input[0].set_value(date(2026, 11, 9))
            next(select for select in app.selectbox if select.label.startswith("Moneda para")).set_value("USD")
            next(f for f in app.text_input if f.label == "Total de referencia USD").set_value("21")
            next(f for f in app.text_input if f.label == "Total de referencia EUR").set_value("15")
            next(b for b in app.button if "Analizar documento" in b.label).click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("-1.00" in warning.value for warning in app.warning))
            self.assertFalse(any("Guardar análisis" in b.label for b in app.button))
            self.assertEqual(db.listar_reportes_usuario(self.uid, eid), [])

            next(f for f in app.text_input if f.label == "Total de referencia USD").set_value("20,00")
            next(b for b in app.button if "Analizar documento" in b.label).click().run()
            next(b for b in app.button if "Guardar análisis" in b.label).click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("Cierres semanales" in item.value for item in app.subheader))
            history = db.listar_reportes_usuario(self.uid, eid)
            self.assertEqual(len(history), 1)
            cierre = history[0]["indicadores"]["cierre"]
            self.assertEqual(cierre["inicio"], "2026-11-09")
            self.assertEqual(cierre["ingresos_por_moneda"], {"USD": 20, "EUR": 15})
            self.assertEqual(cierre["referencias"]["USD"]["total_referencia"], "20.00")
            self.assertTrue(cierre["referencias"]["USD"]["conciliado"])
            self.assertTrue(cierre["referencias"]["EUR"]["conciliado"])

            db.guardar_reporte_usuario(self.uid, eid, "Cierre anterior", {
                "registros_totales": 1,
                "registros_validos": 1,
                "registros_con_incidencias": 0,
                "perfiles": {"ventas": {"ingresos_totales": 50}},
                "cierre": {"inicio": "2026-11-02", "fin": "2026-11-08", "archivos": 1},
            }, perfil="consolidado")
            app.run()
            self.assertEqual(len(app.exception), 0)
            history_table = next(table.value for table in app.dataframe if "Moneda" in table.value.columns
                                 and "Reporte" in table.value.columns)
            self.assertEqual(dict(zip(history_table["Moneda"], history_table["Ingresos"])),
                             {"USD": 20, "EUR": 15, "Sin especificar": 50})
