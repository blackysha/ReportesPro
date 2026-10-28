# ReportesPro

Sistema de análisis de datos y generación de reportes empresariales desarrollado con Python.

## Descripción

ReportesPro permite procesar archivos CSV y Excel, validar información, calcular indicadores y generar reportes PDF. También permite registrar empresas y consultar el historial de los análisis realizados.

## Funcionalidades

- Gestión y selección de empresas.
- Carga de archivos CSV, XLSX y XLS.
- Análisis general, ventas, inventario y clientes.
- Validación de registros e identificación de incidencias.
- Cálculo automático de indicadores.
- Generación y descarga de informes PDF.
- Exportación de resultados a CSV.
- Historial de reportes almacenado en SQLite.
- Filtros por empresa, perfil, archivo y fechas.
- Visualización de estadísticas y gráficos.

## Tecnologías utilizadas

- Python
- Streamlit
- pandas
- ReportLab
- SQLite
- openpyxl y xlrd para formatos Excel

## Instalación

Clonar el repositorio:

```bash
git clone https://github.com/TU_USUARIO/ReportesPro.git
cd ReportesPro
```

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activarlo en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Ejecutar la aplicación:

```bash
python -m streamlit run web_app.py
```

Abrir en el navegador:

`http://localhost:8501`

## Estructura principal

- `web_app.py`: interfaz web.
- `main.py`: procesamiento y análisis de datos.
- `database/db.py`: gestión de la base de datos SQLite.
- `datos_ejemplo.csv`: archivo de demostración.
- `requirements.txt`: dependencias.

## Estado del proyecto

Prototipo funcional en desarrollo. No dispone todavía de autenticación, permisos de acceso por empresa ni configuración de producción.

## Próximas mejoras

- Autenticación y roles.
- Pruebas automatizadas.
- Integración con bases de datos de servidor.
- Automatización de reportes.
- Despliegue web seguro.

## Autor

Proyecto de portafolio desarrollado para demostrar conocimientos de Python, análisis de datos, bases de datos y desarrollo de aplicaciones.