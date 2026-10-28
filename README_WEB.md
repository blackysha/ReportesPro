# ReportesPro — interfaz web inicial

Esta interfaz utiliza las funciones existentes de `main.py` para importar CSV/Excel, validar datos, calcular indicadores y generar PDF.

## Instalación en Windows

Copia `web_app.py` a la misma carpeta donde están `main.py` y `datos_ejemplo.csv`.

En la terminal de VS Code, dentro de esa carpeta:

```powershell
.\.venv\Scripts\python.exe -m pip install streamlit xlrd
.\.venv\Scripts\python.exe -m streamlit run web_app.py
```

Abre la dirección local que muestre Streamlit (normalmente http://localhost:8501).

## Alcance actual

- Sí: CSV, Excel, validación básica, indicadores, descarga PDF y CSV.
- No: enviar correos, autenticación, conexión directa a MySQL/MariaDB, reglas configurables por empresa, auditoría persistente o ejecución programada.
- El nombre de empresa y correo son metadatos del informe; no cambian las reglas de validación.

## Próximos pasos

1. Separar las funciones de `main.py` en módulos.
2. Incorporar SQLAlchemy y SQLite para guardar historial de ejecuciones.
3. Crear configuraciones de empresa e indicadores personalizables.
4. Incorporar autenticación y permisos antes de desplegar en red.
5. Añadir pruebas automatizadas y documentación técnica.
