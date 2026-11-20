import json
import sqlite3
import os
from contextlib import nullcontext
from pathlib import Path


# =========================================
# CONFIGURACIÓN DE LA BASE DE DATOS
# =========================================

DB_PATH = Path(os.environ.get("REPORTESPRO_DB_PATH", Path(__file__).resolve().parent / "reportespro.db")).resolve()


class Conexion(sqlite3.Connection):
    """Conserva commit/rollback de SQLite y cierra al salir del contexto."""

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

PERFILES_VALIDOS = (
    "general",
    "ventas",
    "inventario",
    "clientes",
    "consolidado"
)


def conectar():
    """Establece una conexión con SQLite."""

    conexion = sqlite3.connect(DB_PATH, timeout=10, factory=Conexion)

    conexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conexion


# =========================================
# CREACIÓN Y MIGRACIÓN DE TABLAS
# =========================================

def crear_tablas():
    """
    Crea las tablas si no existen.

    Si la tabla de reportes ya existe,
    añade las columnas nuevas sin eliminar
    los datos anteriores.
    """

    with conectar() as conexion:

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS reportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                archivo TEXT NOT NULL,
                registros_totales INTEGER NOT NULL DEFAULT 0,
                registros_validos INTEGER NOT NULL DEFAULT 0,
                registros_invalidos INTEGER NOT NULL DEFAULT 0,
                fecha_generacion TEXT DEFAULT CURRENT_TIMESTAMP,
                perfil TEXT NOT NULL DEFAULT 'general',
                indicadores_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (empresa_id)
                    REFERENCES empresas(id)
            )
            """
        )

        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(reportes)"
            ).fetchall()
        }

        # Migración de bases de datos anteriores

        if "perfil" not in columnas:

            conexion.execute(
                """
                ALTER TABLE reportes
                ADD COLUMN perfil TEXT NOT NULL
                DEFAULT 'general'
                """
            )

        if "indicadores_json" not in columnas:

            conexion.execute(
                """
                ALTER TABLE reportes
                ADD COLUMN indicadores_json TEXT NOT NULL
                DEFAULT '{}'
                """
            )

        conexion.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_reportes_empresa_perfil
            ON reportes (empresa_id, perfil)
            """
        )


# =========================================
# GESTIÓN DE EMPRESAS
# =========================================

def registrar_empresa(nombre, correo):
    """Registra una empresa y devuelve su ID."""

    nombre = nombre.strip()
    correo = (correo or "").strip()

    if not nombre:

        raise ValueError(
            "El nombre de la empresa es obligatorio."
        )

    with conectar() as conexion:

        cursor = conexion.execute(
            """
            INSERT INTO empresas (nombre, correo)
            VALUES (?, ?)
            """,
            (nombre, correo)
        )

        return cursor.lastrowid


def listar_empresas():
    """Devuelve las empresas registradas."""

    conexion = conectar()

    try:

        conexion.row_factory = sqlite3.Row

        filas = conexion.execute(
            """
            SELECT id, nombre, correo
            FROM empresas
            ORDER BY nombre, id
            """
        ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    finally:

        conexion.close()


def buscar_empresa(empresa_id):
    """Busca una empresa por su ID."""

    conexion = conectar()

    try:

        conexion.row_factory = sqlite3.Row

        fila = conexion.execute(
            """
            SELECT id, nombre, correo
            FROM empresas
            WHERE id = ?
            """,
            (empresa_id,)
        ).fetchone()

        return dict(fila) if fila else None

    finally:

        conexion.close()


# =========================================
# GUARDAR REPORTES
# =========================================

def guardar_reporte(
    empresa_id,
    archivo,
    indicadores,
    perfil="general",
    _conexion=None,
):
    """
    Guarda un reporte junto con su perfil
    y todos sus indicadores.

    El perfil general se utiliza por defecto
    para mantener compatibilidad.
    """

    if perfil not in PERFILES_VALIDOS:

        raise ValueError(
            f"Perfil de análisis no válido: {perfil}"
        )

    indicadores_json = json.dumps(
        indicadores,
        ensure_ascii=False,
        allow_nan=False
    )

    with (nullcontext(_conexion) if _conexion is not None else conectar()) as conexion:

        cursor = conexion.execute(
            """
            INSERT INTO reportes (
                empresa_id,
                archivo,
                registros_totales,
                registros_validos,
                registros_invalidos,
                perfil,
                indicadores_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                archivo,
                int(indicadores["registros_totales"]),
                int(indicadores["registros_validos"]),
                int(
                    indicadores["registros_con_incidencias"]
                ),
                perfil,
                indicadores_json
            )
        )

        return cursor.lastrowid


# =========================================
# CONSULTAR HISTORIAL
# =========================================

def listar_reportes(empresa_id, perfil=None, _conexion=None, *, limite=None, reporte_id=None):
    """
    Devuelve los reportes de una empresa.

    Permite filtrar por perfil cuando
    se especifica uno.
    """

    if perfil is not None and perfil not in PERFILES_VALIDOS:

        raise ValueError(
            f"Perfil no válido: {perfil}"
        )

    conexion = _conexion if _conexion is not None else conectar()

    try:

        conexion.row_factory = sqlite3.Row

        consulta = """
            SELECT
                id,
                archivo,
                perfil,
                registros_totales,
                registros_validos,
                registros_invalidos,
                indicadores_json,
                fecha_generacion
            FROM reportes
            WHERE empresa_id = ?
        """

        parametros = [empresa_id]

        if perfil is not None:

            consulta += " AND perfil = ?"
            parametros.append(perfil)

        if reporte_id is not None:
            consulta += " AND id = ?"
            parametros.append(reporte_id)
        consulta += " ORDER BY id DESC"
        if limite is not None:
            consulta += " LIMIT ?"
            parametros.append(limite)

        filas = conexion.execute(
            consulta,
            parametros
        ).fetchall()

        resultados = []

        for fila in filas:

            reporte = dict(fila)

            try:

                reporte["indicadores"] = json.loads(
                    reporte["indicadores_json"]
                )

            except (ValueError, TypeError):

                reporte["indicadores"] = {}

            resultados.append(reporte)

        return resultados

    finally:

        if _conexion is None:
            conexion.close()


def obtener_reporte(reporte_id):
    """Consulta un reporte específico por ID."""

    conexion = conectar()

    try:

        conexion.row_factory = sqlite3.Row

        fila = conexion.execute(
            """
            SELECT *
            FROM reportes
            WHERE id = ?
            """,
            (reporte_id,)
        ).fetchone()

        if fila is None:
            return None

        reporte = dict(fila)

        try:

            reporte["indicadores"] = json.loads(
                reporte["indicadores_json"]
            )

        except (ValueError, TypeError):

            reporte["indicadores"] = {}

        return reporte

    finally:

        conexion.close()


# =========================================
# ESTADÍSTICAS POR EMPRESA
# =========================================

def obtener_estadisticas_empresa(
    empresa_id,
    perfil=None
):
    """
    Calcula estadísticas acumuladas.

    Si se indica un perfil, calcula
    únicamente sus estadísticas.
    """

    if perfil is not None and perfil not in PERFILES_VALIDOS:

        raise ValueError(
            f"Perfil no válido: {perfil}"
        )

    conexion = conectar()

    try:

        conexion.row_factory = sqlite3.Row

        consulta = """
            SELECT
                COUNT(*) AS total_reportes,

                COALESCE(
                    SUM(registros_totales), 0
                ) AS total_registros,

                COALESCE(
                    SUM(registros_validos), 0
                ) AS total_validos,

                COALESCE(
                    SUM(registros_invalidos), 0
                ) AS total_incidencias

            FROM reportes
            WHERE empresa_id = ?
        """

        parametros = [empresa_id]

        if perfil is not None:

            consulta += " AND perfil = ?"
            parametros.append(perfil)

        fila = conexion.execute(
            consulta,
            parametros
        ).fetchone()

        return dict(fila)

    finally:

        conexion.close()


# =========================================
# EVOLUCIÓN DE REPORTES
# =========================================

def obtener_evolucion_empresa(
    empresa_id,
    perfil=None
):
    """
    Consulta la evolución diaria.

    Permite consultar todos los perfiles
    o uno específico.
    """

    if perfil is not None and perfil not in PERFILES_VALIDOS:

        raise ValueError(
            f"Perfil no válido: {perfil}"
        )

    conexion = conectar()

    try:

        conexion.row_factory = sqlite3.Row

        consulta = """
            SELECT
                DATE(fecha_generacion) AS fecha,

                COUNT(*) AS reportes,

                COALESCE(
                    SUM(registros_totales), 0
                ) AS registros,

                COALESCE(
                    SUM(registros_validos), 0
                ) AS validos,

                COALESCE(
                    SUM(registros_invalidos), 0
                ) AS incidencias

            FROM reportes
            WHERE empresa_id = ?
        """

        parametros = [empresa_id]

        if perfil is not None:

            consulta += " AND perfil = ?"
            parametros.append(perfil)

        consulta += """
            GROUP BY DATE(fecha_generacion)
            ORDER BY fecha ASC
        """

        filas = conexion.execute(
            consulta,
            parametros
        ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    finally:

        conexion.close()


# =========================================
# ACCESO PRIVADO - REPORTESPRO 3.0
# =========================================

def registrar_empresa_usuario(usuario_id, nombre, correo="", version_sesion=None):
    """Registra una empresa asociada a su propietario."""
    nombre = nombre.strip()
    correo = (correo or "").strip()

    if not nombre:
        raise ValueError("El nombre de la empresa es obligatorio.")

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        usuario = conexion.execute(
            "SELECT version_sesion FROM usuarios WHERE id = ? AND activo = 1",
            (usuario_id,)
        ).fetchone()

        if usuario is None or (version_sesion is not None and usuario[0] != version_sesion):
            raise PermissionError("La cuenta o la sesión no están disponibles.")

        cursor = conexion.execute(
            """
            INSERT INTO empresas (nombre, correo, usuario_id)
            VALUES (?, ?, ?)
            """,
            (nombre, correo, usuario_id)
        )

        return cursor.lastrowid


def listar_empresas_usuario(usuario_id):
    """Lista solamente las empresas del usuario."""
    with conectar() as conexion:
        conexion.row_factory = sqlite3.Row

        filas = conexion.execute(
            """
            SELECT e.id, e.nombre, e.correo
            FROM empresas e
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE e.usuario_id = ? AND u.activo = 1
            ORDER BY e.nombre, e.id
            """,
            (usuario_id,)
        ).fetchall()

        return [dict(fila) for fila in filas]


def usuario_es_propietario(usuario_id, empresa_id):
    """Comprueba que la empresa pertenece al usuario."""
    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT 1
            FROM empresas
            JOIN usuarios ON usuarios.id = empresas.usuario_id
            WHERE empresas.id = ? AND usuario_id = ? AND usuarios.activo = 1
            """,
            (empresa_id, usuario_id)
        ).fetchone()

        return fila is not None


def guardar_reporte_usuario(
    usuario_id,
    empresa_id,
    archivo,
    indicadores,
    perfil="consolidado",
    version_sesion=None,
):
    """Guarda un reporte solo si el usuario es propietario."""
    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        _verificar_acceso(conexion, usuario_id, empresa_id, version_sesion)
        return guardar_reporte(empresa_id, archivo, indicadores, perfil, _conexion=conexion)


def listar_reportes_usuario(
    usuario_id, empresa_id, version_sesion=None, *, limite=None, reporte_id=None
):
    """Consulta el historial solo si pertenece al usuario."""
    with conectar() as conexion:
        conexion.execute("BEGIN")
        _verificar_acceso(conexion, usuario_id, empresa_id, version_sesion)
        return listar_reportes(
            empresa_id, _conexion=conexion, limite=limite, reporte_id=reporte_id
        )


def _verificar_acceso(conexion, usuario_id, empresa_id, version_sesion=None):
    usuario = conexion.execute(
        """SELECT u.version_sesion FROM empresas e
           JOIN usuarios u ON u.id = e.usuario_id
           WHERE e.id = ? AND u.id = ? AND u.activo = 1""",
        (empresa_id, usuario_id),
    ).fetchone()
    if usuario is None or (version_sesion is not None and usuario[0] != version_sesion):
        raise PermissionError("No tienes permiso o tu sesión ya no es válida.")


# =========================================
# EJECUCIÓN DIRECTA
# =========================================

if __name__ == "__main__":

    crear_tablas()

    print(
        "Base de datos actualizada correctamente."
    )

    print(
        f"Ubicación: {DB_PATH}"
    )

    print(
        "Perfiles disponibles: "
        + ", ".join(PERFILES_VALIDOS)
    )


def eliminar_empresa_usuario(usuario_id, empresa_id):
    """
    Elimina una empresa propiedad del usuario
    y los reportes asociados a esa empresa.
    """

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        _verificar_acceso(conexion, usuario_id, empresa_id)
        # Comprobar que la empresa pertenece al usuario.
        propietario = conexion.execute(
            """
            SELECT id
            FROM empresas
            WHERE id = ? AND usuario_id = ?
            """,
            (empresa_id, usuario_id),
        ).fetchone()

        if propietario is None:
            raise PermissionError(
                "No tienes permiso para eliminar esta empresa."
            )

        # Eliminar primero sus reportes.
        conexion.execute(
            "DELETE FROM reportes WHERE empresa_id = ?",
            (empresa_id,),
        )

        # Eliminar la empresa.
        conexion.execute(
            """
            DELETE FROM empresas
            WHERE id = ? AND usuario_id = ?
            """,
            (empresa_id, usuario_id),
        )

    return True
