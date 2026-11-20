# ReportesPro 3.0 — instrucciones permanentes

## Alcance

Continuar Python, Streamlit, Pandas y SQLite existentes. Priorizar seguridad,
preservación de datos y cambios pequeños. No reiniciar ni reescribir el proyecto.
Consultar ESTADO_PROYECTO.md y docs/OPERACION.md antes de continuar.

## Datos y secretos

- No borrar ni reiniciar database/reportespro.db.
- No modificar usuarios, contraseñas, roles, empresas o reportes reales para probar.
- Toda prueba que escriba utiliza SQLite temporal y datos sintéticos.
- No imprimir secretos, hashes de contraseñas, tokens o correos reales en logs.
- Los archivos de credenciales solicitados por el propietario están en
  Documentos/contraseñas, fuera del repositorio. No leerlos con herramientas que
  impriman su contenido ni incorporarlos a Git. Solo procesarlos sin mostrar claves.
- No incorporar secretos, archivos de clientes, bases reales ni respaldos a Git.
- No ejecutar login_test.py, probar_login.py, probar_correo.py, bootstrap_admin.py
  o migraciones contra la base real como parte de verificaciones automáticas.
- Usar REPORTESPRO_DB_PATH para separar entornos y bases nuevas de demostración.

## Cambios

- Al terminar y verificar una tarea solicitada por el propietario, actualizar
  `docs/avances.html` con la fecha, el resultado y las comprobaciones relevantes.
  El registro se comparte en la red local. Conservar fuera de él datos de clientes,
  nombres de cuentas, secretos, rutas privadas y detalles innecesarios.

- Crear respaldo en backups/ antes de modificar archivos importantes.
- Conservar cambios previos del usuario. No descartar ni sobrescribir trabajo ajeno.
- Se pueden editar y probar correcciones reversibles dentro del alcance autorizado.
- Solicitar confirmación antes de operaciones destructivas, migraciones de datos
  reales, cambios de credenciales, despliegues o interrupciones del acceso.
- No se requiere confirmación adicional para leer código o ejecutar pruebas aisladas.
- El propietario autorizó en la sesión del 11/11/2026 cambiar su contraseña,
  reservarle el único rol admin y preparar cinco cuentas nuevas de prueba.
  No volver a ejecutar la provisión ni rotar esas claves sin una nueva instrucción.
- Mantener la administración en localhost:8501; la instancia LAN:8502 debe
  rechazar administradores. No debilitar esta separación para resolver problemas.

## Verificación

Desde la raíz del proyecto en PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -m pip check
```

Las pruebas parchean DB_PATH y utilizan exclusivamente TemporaryDirectory.
No importar web_app.py desde un script normal: ejecuta la interfaz. Usar AppTest
con base temporal. No iniciar servidores contra la base real para verificar cambios.
No declarar una función terminada sin evidencia; actualizar ESTADO_PROYECTO.md
con resultados y limitaciones. Describir archivos modificados, motivo y comprobación.

Los scripts heredados de prueba/manual están en scripts/manual/. La interfaz
login_test.py y respaldos de código se archivaron en backups/archivo_legacy_20261111/.
Los ejemplos CSV están en examples/csv/. Ver docs/ESTRUCTURA.md y docs/PRUEBA_LAN.md.
