
"""Migración de empresas a ReportesPro 3.0."""

from database.db import conectar


def migrar_empresas():
    with conectar() as conexion:
        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(empresas)"
            ).fetchall()
        }

        if "usuario_id" not in columnas:
            conexion.execute("""
                ALTER TABLE empresas
                ADD COLUMN usuario_id INTEGER
                REFERENCES usuarios(id)
            """)

        conexion.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_empresas_usuario
            ON empresas(usuario_id)
        """)

    print("Migración de empresas completada.")


if __name__ == "__main__":
    migrar_empresas()
