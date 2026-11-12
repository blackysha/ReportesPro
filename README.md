# ReportesPro 3.0

Aplicación empresarial en Python, Streamlit y SQLite para analizar CSV/Excel,
consolidar hojas y generar informes. Se continúa el proyecto existente y se
conservan los datos históricos.

## Funcionalidades

- Registro e inicio de sesión con Argon2 y bloqueo temporal por cuenta.
- Empresas privadas e historial con comprobación de propietario.
- Análisis de ventas, inventario, clientes y datos generales.
- Validación de registros, incidencias y consolidación entre hojas.
- Exportaciones PDF, XLSX y CSV; ZIP de PDF y Excel.
- Administración de activación/desactivación de cuentas y roles existentes.
- Recuperación por correo para cuentas normales; tokens de un solo uso.
- Invalidación de sesiones, límites de duración e inactividad y auditoría.
- Límites de archivos y neutralización de fórmulas al exportar.
- Respaldos coherentes y diagnóstico de solo lectura.

El historial conserva indicadores, no los documentos originales. Los indicadores
por perfil se guardan en análisis nuevos; no se modificaron registros antiguos.

## Instalación y ejecución local

Se verificó con Python 3.14.7 en Windows. Crear .venv solo si aún no existe:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m pip check
```

Configurar los secretos siguiendo [OPERACION.md](docs/OPERACION.md). Nunca
incorporar secretos o bases reales al repositorio.

```powershell
.\run_reportespro.ps1
```

Si PowerShell impide ejecutar scripts, usar directamente:

```powershell
.\.venv\Scripts\python.exe -m streamlit run web_app.py --server.address 127.0.0.1 --server.maxUploadSize 10
```

## Verificación segura

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -m scripts.diagnostico --security-config
```

Las pruebas usan bases temporales y correo simulado. No ejecutar los scripts
heredados de login o correo contra cuentas reales como pruebas de regresión.

## Documentación

- [Estado, pruebas y pendientes](ESTADO_PROYECTO.md).
- [Operación, configuración, respaldos y producción](docs/OPERACION.md).
- [Instrucciones permanentes para Codex](AGENTS.md).
- [Administración local y prueba con cinco laptops](docs/PRUEBA_LAN.md).
- [Estructura del repositorio](docs/ESTRUCTURA.md).

Abrir `ReportesPro.code-workspace` para usar el intérprete, tareas y pruebas de
VS Code. El administrador se limita a localhost:8501. Para usuarios de la LAN,
`run_pruebas_red.ps1` usa HTTPS y rechaza administradores; no iniciar esa instancia
hasta preparar la red y verificar el certificado en cada laptop.

## Alcance de la entrega

Versión local con mejoras verificadas. No se ha desplegado en Internet. Antes de
producción externa faltan decisiones de alojamiento, HTTPS, controles del proxy,
validación SMTP real autorizada y recuperación administrativa reforzada.
SQLite requiere disco persistente y una sola instancia; no ofrece escalabilidad
horizontal automática. Consultar las limitaciones y pendientes documentados.
