"""Configuración local explícita. Nunca se invoca al iniciar la aplicación."""

import secrets
from datetime import datetime, timezone

from auth.security import crear_hash_password
from database.db import conectar
from database.auditoria import registrar_evento_en_conexion
from database.login_security import _identificador


def nueva_password():
    return "Rp!" + secrets.token_urlsafe(24)


def preparar_accesos(propietario, restablecer_existentes=False, cantidad_pruebas=5, entregar=None):
    """Transacción autorizada de roles y credenciales; devuelve claves solo en memoria."""
    propietario = propietario.strip().lower()
    nueva_clave = nueva_password()
    owner_hash = crear_hash_password(nueva_clave)
    cuentas_nuevas = []
    if not restablecer_existentes:
        for numero in range(1, cantidad_pruebas + 1):
            clave = nueva_password()
            cuentas_nuevas.append({
                "nombre": f"Prueba laptop {numero:02d}",
                "correo": f"prueba{numero:02d}@reportespro.invalid",
                "password": clave,
                "hash": crear_hash_password(clave),
            })
    con_claves = []
    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        filas = conexion.execute(
            "SELECT id, nombre, correo, rol, activo FROM usuarios ORDER BY id"
        ).fetchall()
        owner = next((f for f in filas if f[2].lower() == propietario), None)
        if owner is None or owner[4] != 1:
            raise ValueError("La cuenta propietaria debe existir y estar activa.")
        if any(any(f[2].lower() == c["correo"] for f in filas) for c in cuentas_nuevas):
            raise ValueError("Ya existen cuentas de prueba: no se sobrescribieron sus claves.")

        for uid, _, _, rol, _ in filas:
            if uid != owner[0] and rol == "admin":
                conexion.execute(
                    "UPDATE usuarios SET rol='usuario', version_sesion=version_sesion+1 WHERE id=?", (uid,)
                )
                registrar_evento_en_conexion(conexion, uid, "ROL_ACTUALIZADO", "Administración reservada al propietario autorizado")

        conexion.execute(
            "UPDATE usuarios SET rol='admin', password_hash=?, version_sesion=version_sesion+1 WHERE id=?",
            (owner_hash, owner[0]),
        )
        con_claves.append({"id": owner[0], "nombre": owner[1], "correo": owner[2], "rol": "admin", "activo": owner[4], "password": nueva_clave})
        registrar_evento_en_conexion(conexion, owner[0], "ADMINISTRADOR_UNICO_CONFIGURADO", "Cambio solicitado desde la configuración local")
        registrar_evento_en_conexion(conexion, owner[0], "PASSWORD_CAMBIADA_LOCAL", "Credencial del propietario renovada e invalidación de sesiones")

        if restablecer_existentes:
            for uid, nombre, correo, _, activo in filas:
                if uid == owner[0]:
                    continue
                clave = nueva_password()
                conexion.execute(
                    "UPDATE usuarios SET password_hash=?, version_sesion=version_sesion+1 WHERE id=?",
                    (crear_hash_password(clave), uid),
                )
                con_claves.append({"id": uid, "nombre": nombre, "correo": correo, "rol": "usuario", "activo": activo, "password": clave})
                registrar_evento_en_conexion(conexion, uid, "PASSWORD_CAMBIADA_LOCAL", "Restablecimiento local autorizado")
            # El propietario usa solo la consola local; la LAN necesita cinco usuarios normales.
            faltan = cantidad_pruebas - sum(c["activo"] == 1 and c["rol"] == "usuario" for c in con_claves)
            existentes = {f[2].lower() for f in filas}
            numero = 1
            while faltan > 0:
                correo = f"prueba{numero:02d}@reportespro.invalid"
                numero += 1
                if correo in existentes:
                    continue
                clave = nueva_password()
                cursor = conexion.execute(
                    "INSERT INTO usuarios(nombre,correo,password_hash) VALUES (?,?,?)",
                    (f"Prueba laptop {numero - 1:02d}", correo, crear_hash_password(clave)),
                )
                con_claves.append({"id": cursor.lastrowid, "nombre": f"Prueba laptop {numero - 1:02d}", "correo": correo, "rol": "usuario", "activo": 1, "password": clave})
                registrar_evento_en_conexion(conexion, cursor.lastrowid, "CUENTA_PRUEBA_CREADA", "Cuenta sintética adicional para prueba de laptops")
                faltan -= 1
        else:
            for c in cuentas_nuevas:
                cursor = conexion.execute(
                    "INSERT INTO usuarios(nombre,correo,password_hash) VALUES (?,?,?)",
                    (c["nombre"], c["correo"], c["hash"]),
                )
                uid = cursor.lastrowid
                con_claves.append({"id": uid, "nombre": c["nombre"], "correo": c["correo"], "rol": "usuario", "activo": 1, "password": c["password"]})
                registrar_evento_en_conexion(conexion, uid, "CUENTA_PRUEBA_CREADA", "Cuenta sintética para prueba de laptops")

        ahora = datetime.now(timezone.utc).isoformat()
        for cuenta in con_claves:
            conexion.execute("DELETE FROM intentos_login WHERE identificador=?", (_identificador(cuenta["correo"]),))
            conexion.execute(
                "UPDATE recuperaciones_password SET fecha_utilizacion=? WHERE usuario_id=? AND fecha_utilizacion IS NULL",
                (ahora, cuenta["id"]),
            )
        # Regla de datos además de la regla de interfaz: solo puede existir un admin.
        conexion.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unico_administrador ON usuarios(rol) WHERE rol='admin'")
        cuentas = [dict(zip(("id", "nombre", "correo", "rol", "activo"), row)) for row in conexion.execute(
            "SELECT id,nombre,correo,rol,activo FROM usuarios ORDER BY id"
        )]
        if entregar is not None:
            entregar(con_claves, cuentas)
        return con_claves, cuentas
