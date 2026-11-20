"""Asignación explícita de empresas heredadas; nunca fusiona ni borra datos."""

from auth.access_policy import administracion_habilitada
from database.db import conectar
from database.auditoria import registrar_evento_en_conexion


def asignar_empresas(admin_id, asignaciones):
    """Aplicar un mapa empresa->usuario ya revisado en una sola transacción."""
    if not administracion_habilitada():
        raise PermissionError("Operación exclusiva de la administración local.")
    if not asignaciones or any(type(e) is not int or type(u) is not int or e <= 0 or u <= 0
                               for e, u in asignaciones.items()):
        raise ValueError("Se requiere una asignación explícita de identificadores positivos.")
    with conectar() as con:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute("SELECT 1 FROM usuarios WHERE id=? AND rol='admin' AND activo=1", (admin_id,)).fetchone():
            raise PermissionError("Administrador activo requerido.")
        for empresa_id, usuario_id in asignaciones.items():
            if not con.execute("SELECT 1 FROM usuarios WHERE id=? AND activo=1", (usuario_id,)).fetchone():
                raise ValueError("El propietario debe existir y estar activo.")
            empresa = con.execute("SELECT usuario_id FROM empresas WHERE id=?", (empresa_id,)).fetchone()
            if empresa is None or empresa[0] is not None:
                raise ValueError("La empresa no existe o ya tiene propietario; se canceló la operación completa.")
            con.execute("UPDATE empresas SET usuario_id=? WHERE id=? AND usuario_id IS NULL", (usuario_id, empresa_id))
            registrar_evento_en_conexion(con, admin_id, "EMPRESA_ASIGNADA",
                                        f"Empresa {empresa_id}; propietario {usuario_id}")
    return len(asignaciones)
