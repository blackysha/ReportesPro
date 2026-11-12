import csv
from pathlib import Path
import unittest
from unittest.mock import patch

from database import db
from scripts import preparar_entrega as entrega
from test_security import BaseDatosTemporal


class EntregaTests(BaseDatosTemporal, unittest.TestCase):
    def test_entrega_privada_y_veinte_csv_validos(self):
        raiz = Path(self.temp.name)
        destino = raiz / "privado"
        with patch.object(entrega, "PROJECT_ROOT", raiz / "repo"):
            entrega.crear_entrega("prueba@example.invalid", destino, "10.0.0.10")
        self.assertTrue((destino / "04_ADMIN_SOLO_ESTA_PC.txt").is_file())
        self.assertIn("APLICADO", (destino / "00_LEEME.txt").read_text(encoding="utf-8-sig"))
        with (destino / "accesos_5_laptops.csv").open(encoding="utf-8-sig", newline="") as f:
            filas = list(csv.DictReader(f))
        self.assertEqual(len(filas), 5)
        self.assertTrue(all(c["rol"] == "usuario" for c in filas))
        self.assertEqual(len(list((destino / "csv_pruebas").glob("laptop_*.csv"))), 20)
        with (destino / "inventario_usuarios.csv").open(encoding="utf-8-sig", newline="") as f:
            inventario = list(csv.DictReader(f))
        antigua = next(c for c in inventario if c["correo"] == "admin@example.invalid")
        self.assertIn("NO RECUPERABLE", antigua["password"])
        with patch.object(entrega, "PROJECT_ROOT", raiz / "repo"), self.assertRaises(FileExistsError):
            entrega.crear_entrega("prueba@example.invalid", destino, "10.0.0.10")

    def test_no_guarda_secretos_dentro_del_repo(self):
        with self.assertRaises(ValueError):
            entrega.carpeta_privada(entrega.PROJECT_ROOT / "credenciales")
