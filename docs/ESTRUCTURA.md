# Estructura del repositorio

```text
ReportesPro.code-workspace   Workspace de VS Code
.vscode/                    Configuración compartible, tareas y depuración
.streamlit/config.toml      Servidor local, CORS/XSRF y límites
auth/                       Contraseñas, sesiones y política local/LAN
database/                   Persistencia, autorización, auditoría y respaldo
services/                   Correo y recuperación
scripts/                    Diagnóstico y preparación explícita de entrega/TLS
scripts/manual/             Herramientas manuales heredadas
tests/                      Pruebas automatizadas aisladas
examples/csv/               Ejemplos sintéticos para análisis
docs/                       Operación, estructura y prueba LAN
web_app.py                  Interfaz de la aplicación
main.py                     Motor de análisis y exportación
run_reportespro.ps1          Instancia local para administración
run_pruebas_red.ps1          Instancia HTTPS LAN sin administración
```

No versionados: .venv/, .local/, .streamlit/secrets.toml, bases SQLite, backups/,
exports/, claves privadas y credenciales. Las credenciales solicitadas están fuera
del proyecto, en Documentos/contraseñas.

Los respaldos duplicados de código, la interfaz antigua login_test.py y las bases
de respaldo anteriores se conservaron en backups/archivo_legacy_20261111/.
Los reportes y CSV generados anteriores se conservaron en exports/legacy/.
No se movió ni eliminó database/reportespro.db.

No ejecutar scripts de provisión como parte del arranque: cambian roles o claves.
Usar únicamente los lanzadores y las tareas de VS Code para iniciar la aplicación.
