## Registro de empresas

**Funcionalidad:** registrar empresas en la base de datos SQLite.

**Archivo responsable:** `database/db.py`

**Función:** `registrar_empresa(nombre, correo)`

**Comportamiento:**
- Recibe el nombre y el correo de una empresa.
- Comprueba que el nombre no esté vacío.
- Inserta la información en la tabla `empresas`.
- Devuelve el identificador del registro creado.

**Limitaciones actuales:**
- Todavía no existe una comprobación completa del formato del correo.
- No se impiden empresas duplicadas.
- No existe autenticación ni control de permisos.
- El registro todavía no está conectado a la interfaz web.

**Prueba manual:** ejecutar la función desde Python y comprobar mediante una consulta SQL que el registro aparece en la tabla.