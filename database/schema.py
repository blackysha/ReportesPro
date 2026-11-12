"""Inicialización nueva y comprobación de esquema sin migraciones implícitas."""

from database import db

REQUERIDAS = {
    "usuarios": {"id", "nombre", "correo", "password_hash", "activo", "rol", "version_sesion"},
    "empresas": {"id", "nombre", "correo", "usuario_id"},
    "reportes": {"id", "empresa_id", "archivo", "perfil", "indicadores_json", "registros_totales", "registros_validos", "registros_invalidos", "fecha_generacion"},
    "intentos_login": {"identificador", "intentos", "inicio_ventana", "bloqueado_hasta"},
    "auditoria_seguridad": {"id", "usuario_id", "evento", "detalle", "fecha"},
    "recuperaciones_password": {"id", "usuario_id", "token_hash", "fecha_creacion", "fecha_expiracion", "fecha_utilizacion"},
}


def preparar_base_datos():
    """Solo una base que aún no existe puede inicializarse automáticamente."""
    if not db.DB_PATH.exists():
        from database.usuarios import crear_tabla_usuarios, preparar_estado_cuentas, preparar_version_sesiones
        from database.admin import preparar_roles
        from database.migracion_v3 import migrar_empresas
        from database.auditoria import preparar_auditoria
        from database.recovery import preparar_recuperacion
        from database.login_security import preparar_seguridad_login

        crear_tabla_usuarios()
        preparar_estado_cuentas()
        preparar_version_sesiones()
        preparar_roles()
        db.crear_tablas()
        migrar_empresas()
        preparar_auditoria()
        preparar_recuperacion()
        preparar_seguridad_login()
    comprobar_esquema()


def comprobar_esquema():
    with db.conectar() as conexion:
        for tabla, necesarias in REQUERIDAS.items():
            # Los identificadores proceden exclusivamente de la constante local.
            actuales = {fila[1] for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
            if not necesarias <= actuales:
                raise RuntimeError("Esquema incompleto. Requiere una migración revisada y un respaldo previo.")
