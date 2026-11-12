# Interfaz web de ReportesPro 3.0

La interfaz incluye acceso con contraseña, modo invitado, empresas privadas,
historial de indicadores, administración de cuentas y análisis de CSV/XLSX/XLS.
Genera PDF, XLSX, CSV y ZIP con PDF/Excel.

Desde PowerShell en la carpeta del proyecto:

```powershell
.\run_reportespro.ps1
```

El lanzador comprueba el entorno y usa .venv. Escucha en 127.0.0.1 para uso local.
No es un despliegue público ni configura HTTPS.

Pruebas aisladas, sin iniciar el servidor:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Consultar [estado y pendientes](ESTADO_PROYECTO.md) y la
[guía de configuración, respaldo y despliegue](docs/OPERACION.md).