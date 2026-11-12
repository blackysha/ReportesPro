import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from openpyxl import load_workbook

import main


class AnalisisTests(unittest.TestCase):
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
