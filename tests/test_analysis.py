import io
import unittest
from datetime import date
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from openpyxl import load_workbook

import main


class AnalisisTests(unittest.TestCase):
    def test_cierre_semanal_consolida_y_ubica_incidencias(self):
        first = b"fecha,producto,cantidad,precio\n2026-11-09,A,2,10\n08/11/2026,A,1,90\n"
        second = b"fecha,producto,cantidad,precio\n15/11/2026,B,3,5\n"
        result = main.analyze_weekly_sales([("a.csv", first), ("b.csv", second)], date(2026, 11, 9), "EUR")
        self.assertEqual(result["cierre"], {
            "inicio": "2026-11-09", "fin": "2026-11-15", "archivos": 2, "ingresos_por_moneda": {"EUR": 35},
        })
        self.assertEqual(result["indicators"]["ventas"]["ingresos_EUR"], 35)
        self.assertEqual(result["breakdowns"]["ventas"]["Periodo"].tolist(), ["2026-11-09", "2026-11-15"])
        self.assertEqual(result["issues"][["hoja", "fila"]].values.tolist(), [["1. a.csv / CSV", 3]])
        self.assertTrue(main.make_pdf(result, "Distribuidora de prueba").startswith(b"%PDF"))
        with io.BytesIO(main.make_excel(result)) as output:
            workbook = load_workbook(output)
            self.assertIn("Ventas_por_dia", workbook.sheetnames)
            self.assertIn("Cierre_semanal", workbook.sheetnames)
            workbook.close()

    def test_cierre_separa_monedas_y_rechaza_codigos_vacios_o_invalidos(self):
        data = (
            b"fecha,producto,cantidad,precio,moneda\n"
            b"2026-11-09,A,2,10,usd\n2026-11-09,B,3,5,EUR\n"
            b"2026-11-09,C,1,5,DOP\n2026-11-09,D,5,90,\n2026-11-09,E,1,10,XXX\n"
        )
        result = main.analyze_weekly_sales([("ventas.csv", data)], date(2026, 11, 9), "DOP")
        self.assertEqual(result["cierre"]["ingresos_por_moneda"], {"USD": 20, "EUR": 15, "DOP": 5})
        self.assertNotIn("ingresos_totales", result["indicators"]["ventas"])
        self.assertEqual(result["issues"]["campo"].tolist(), ["moneda", "moneda"])
        self.assertEqual(result["breakdowns"]["ventas"].set_index("Moneda")["Ingresos"].to_dict(),
                         {"USD": 20, "EUR": 15, "DOP": 5})
        workbook = load_workbook(io.BytesIO(main.make_excel(result)))
        self.assertEqual(list(workbook["Totales_por_moneda"].values)[1][0:2], ("DOP", 5))
        workbook.close()

    def test_cierre_rechaza_copias_exactas_y_plantillas_incorrectas(self):
        data = b"fecha,producto,cantidad,precio\n2026-11-09,A,2,10\n"
        monday = date(2026, 11, 9)
        with self.assertRaisesRegex(ValueError, "mismo contenido"):
            main.analyze_weekly_sales([("a.csv", data), ("b.csv", data)], monday)
        with self.assertRaisesRegex(ValueError, "faltan columnas"):
            main.analyze_weekly_sales([("a.csv", b"producto,stock,costo\nA,1,2\n")], monday)
        with self.assertRaisesRegex(ValueError, "lunes"):
            main.analyze_weekly_sales([("a.csv", data)], date(2026, 11, 10))

    def test_ventas_pdf_excel_csv(self):
        result = main.analyze("ventas.csv", b"fecha,producto,cantidad,precio\n2026-01-01,Producto,2,3\n")
        self.assertEqual(result["indicators"]["ventas"]["ingresos_totales"], 6)
        self.assertTrue(main.make_pdf(result, "Empresa <temporal>").startswith(b"%PDF"))
        workbook = load_workbook(io.BytesIO(main.make_excel(result)))
        self.assertIn("Ventas_unificado", workbook.sheetnames)
        workbook.close()
        csv = pd.read_csv(io.BytesIO(main.make_csv(result)))
        self.assertEqual(csv["importe"].iloc[0], 6)

    def test_formulas_se_neutralizan_en_todas_las_hojas(self):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"producto": ["=1+1", " +SUM(1)", "@SUM(1)"], "stock": [2, 3, 4], "costo": [3, 4, 5]}).to_excel(writer, sheet_name="Inventario", index=False)
            pd.DataFrame({"=cabecera": ["=1+1"]}).to_excel(writer, sheet_name="=hoja", index=False)
            # Simular texto no confiable, sin convertirlo en fórmula al crear la entrada.
            for sheet in writer.book:
                for row in sheet:
                    for cell in row:
                        if cell.data_type == "f":
                            cell.data_type = "s"
        result = main.analyze("prueba.xlsx", buffer.getvalue())
        workbook = load_workbook(io.BytesIO(main.make_excel(result)))
        for sheet in workbook:
            for row in sheet:
                for cell in row:
                    self.assertNotEqual(cell.data_type, "f", (sheet.title, cell.coordinate))
        workbook.close()
        csv = main.make_csv(result).decode("utf-8-sig")
        self.assertIn("'=1+1", csv)

    def test_infinitos_se_excluyen(self):
        result = main.analyze("prueba.csv", b"producto,stock,costo\nProducto,inf,3\nOtro,2,3\n")
        self.assertEqual(result["indicators"]["inventario"]["valor_inventario"], 6)
        self.assertEqual(result["indicators"]["inventario"]["registros_con_incidencias"], 1)

    def test_desbordamiento_se_rechaza(self):
        with self.assertRaises(ValueError):
            main.analyze("prueba.csv", b"producto,stock,costo\nProducto,1e308,1e308\n")

    def test_tamano_y_filas_se_limitan(self):
        with patch.object(main, "MAX_FILE_BYTES", 4), self.assertRaises(ValueError):
            main.read_sheets("prueba.csv", b"a,b\n1,2\n")
        with patch.object(main, "MAX_ROWS", 1), self.assertRaises(ValueError):
            main.read_sheets("prueba.csv", b"a,b\n1,2\n3,4\n")

    def test_xlsx_descomprimido_limitado(self):
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as z:
            z.writestr("grande.xml", "x" * 10000)
        with patch.object(main, "MAX_UNCOMPRESSED_BYTES", 100), self.assertRaises(ValueError):
            main.read_sheets("prueba.xlsx", buffer.getvalue())

    def test_encabezados_duplicados_y_archivo_vacio(self):
        with self.assertRaises(ValueError):
            main.normalize_columns(pd.DataFrame(columns=["email", "correo"]))
        with self.assertRaises(ValueError):
            main.read_sheets("vacio.csv", b"")

    def test_perfiles_multiples_y_duplicados_entre_hojas(self):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"nombre": ["Cliente"], "correo": ["cliente@example.invalid"], "fecha_registro": ["2026-01-01"]}).to_excel(writer, sheet_name="Clientes1", index=False)
            pd.DataFrame({"nombre": ["Cliente"], "correo": ["cliente@example.invalid"], "fecha_registro": ["2026-01-01"]}).to_excel(writer, sheet_name="Clientes2", index=False)
            pd.DataFrame({"nombre": ["Persona"], "correo": ["persona@example.invalid"], "edad": [20], "monto": [100]}).to_excel(writer, sheet_name="General", index=False)
        result = main.analyze("prueba.xlsx", buffer.getvalue())
        self.assertEqual(result["indicators"]["clientes"]["registros_validos"], 1)
        self.assertEqual(result["indicators"]["clientes"]["registros_con_incidencias"], 1)
        self.assertEqual(result["indicators"]["general"]["monto_total_valido"], 100)

    def test_documento_sin_filas_validas_se_exporta(self):
        result = main.analyze("prueba.csv", b"fecha,producto,cantidad,precio\nincorrecta,Producto,-1,3\n")
        self.assertEqual(result["indicators"]["ventas"]["registros_validos"], 0)
        self.assertTrue(main.make_pdf(result, "Empresa").startswith(b"%PDF"))
        self.assertTrue(main.make_excel(result).startswith(b"PK"))

    def test_columnas_y_hojas_limitadas(self):
        with patch.object(main, "MAX_COLUMNS", 1), self.assertRaises(ValueError):
            main.read_sheets("prueba.csv", b"a,b\n1,2\n")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name="Una", index=False)
            pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name="Otra", index=False)
        with patch.object(main, "MAX_SHEETS", 1), self.assertRaises(ValueError):
            main.read_sheets("prueba.xlsx", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
