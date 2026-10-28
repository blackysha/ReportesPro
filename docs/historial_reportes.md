# Historial de reportes — ReportesPro

## Objetivo

Registrar automáticamente cada análisis generado y permitir consultar su historial por empresa.

## Funcionalidades

- Guardar el identificador de la empresa.
- Registrar el nombre del archivo procesado.
- Almacenar el número de registros totales, válidos y con incidencias.
- Registrar la fecha de generación.
- Consultar el historial de cada empresa desde la interfaz web.

## Tecnologías

Python, SQLite y Streamlit.

## Archivos modificados

- `database/db.py`
- `web_app.py`

## Limitaciones actuales

- El historial almacena metadatos, no el contenido completo del PDF.
- No existe autenticación.
- No se pueden eliminar ni editar reportes desde la interfaz.
- El almacenamiento es local.
- El campo de registros inválidos utiliza temporalmente el indicador de registros con incidencias.

## Próximas mejoras

Incorporar filtros por fecha, búsqueda de reportes, indicadores configurables por empresa y pruebas automatizadas.