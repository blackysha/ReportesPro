# Interfaz web de ReportesPro 3.0

Para aprender a publicarla y probarla en celulares, seguir
[la guía paso a paso](docs/PUBLICAR_PASO_A_PASO.md). Incluye PowerShell,
HTTPS temporal, dirección permanente y registro de dispositivos.

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

## Cierre semanal de ventas

1. Inicia sesión como usuario y selecciona tu empresa. En **Tipo de análisis**,
   elige **Cierre semanal de ventas** y selecciona el lunes del período.
2. Usa **Descargar plantilla de ventas** para ver los encabezados requeridos.
   Adjunta los CSV, XLSX o XLS de la semana. Cada hoja debe contener
   `fecha`, `producto`, `cantidad` y `precio`. En la columna `moneda`, usa DOP,
   USD o EUR en cada fila. Para hojas sin esa columna, elige su moneda en el panel.
   Usa exportaciones que cubran ventas distintas. El límite conjunto es 10
   archivos, 10 MB y 25 hojas.
3. Si tienes totales independientes para esa semana, introdúcelos por moneda
   y sin separador de miles. Los ingresos se calculan como la suma de cantidad
   por precio de cada moneda y se comparan con su referencia a dos decimales.
   Usa referencias con el mismo criterio de impuestos, descuentos y devoluciones
   que los archivos. Los informes conservan los importes en su moneda de origen.
4. Pulsa **Analizar documento**. Revisa los ingresos por día y las incidencias
   por archivo, hoja y registro. Si hay fechas fuera de la semana u otras
   incidencias, corrige el origen y vuelve a cargarlo. Las descargas durante la
   revisión contienen los resultados calculados con los registros válidos.
5. Guarda el cierre cuando haya ventas válidas y hayas resuelto las incidencias
   y diferencias. En **Cierres semanales de ventas** puedes comparar los ingresos
   guardados por período. Conserva el Excel o PDF descargado si necesitas el informe.

Se detectan archivos idénticos por contenido. Archivos distintos pueden contener
transacciones solapadas. El cierre actual requiere cantidades positivas y calcula
ingresos según los precios exportados. Para el piloto, mide el tiempo total,
compara con el cierre aprobado y observa si el encargado puede repetirlo solo.
