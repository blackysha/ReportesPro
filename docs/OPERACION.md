# Operación y preparación de ReportesPro 3.0

## Entorno comprobado

Windows, Python 3.14.7 y dependencias directas fijadas en requirements.txt.
Las versiones se eligieron a partir del entorno probado; no representan una auditoría
de vulnerabilidades publicadas. No hay dependencias nuevas de ejecución.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m pip check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

No ejecutar unittest sin `discover -s tests`: hay scripts heredados en la raíz que
no son pruebas seguras para la base real. Las pruebas no envían correos.

Argon2 estaba instalado en el Python base, pero faltaba en .venv. Se incorporaron
localmente las mismas bibliotecas y sus metadatos compatibles con CPython 3.14
para evitar la descarga bloqueada. Hash/verificación reales y pip check pasaron.
Para instalaciones nuevas, usar pip y requirements.txt normalmente.

## Ejecución local

El lanzador utiliza siempre el Python del proyecto y comprueba primero el esquema
y la presencia del secreto sin mostrar su valor:

```powershell
.\run_reportespro.ps1
```

```powershell
.\.venv\Scripts\python.exe -m streamlit run web_app.py --server.address 127.0.0.1
```

Este comando inicia la aplicación real: ejecutarlo solo al realizar la puesta en
marcha acordada. No se inició ni reinició el servidor real durante las pruebas.

La comprobación independiente, que no inicia servidor ni modifica datos, es:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.diagnostico --security-config
```

.streamlit/config.example.toml es una referencia para revisión; no reemplaza ni
modifica la configuración activa. No desactivar CORS o XSRF para resolver errores.

Para una demostración independiente, establecer REPORTESPRO_DB_PATH con la ruta
absoluta de una base nueva dentro de una carpeta privada existente. El primer
arranque crea el esquema completo. Una base existente se comprueba y nunca se
migra automáticamente. No cambiar esta variable en un proceso de producción
sin revisar el destino: una ruta equivocada puede mostrar una aplicación vacía.

## Configuración privada

No incluir valores reales en repositorios, capturas ni conversaciones.

- LOGIN_SECURITY_KEY: secreto aleatorio de al menos 32 caracteres, desde el
  entorno o .streamlit/secrets.toml. Mantenerlo estable; cambiarlo altera los
  identificadores de protección contra intentos de acceso.
- REPORTESPRO_DB_PATH: ruta absoluta de SQLite; por defecto database/reportespro.db.
- REPORTESPRO_PUBLIC_URL: URL de la aplicación, desde entorno o Streamlit Secrets.
  Admite HTTP únicamente para localhost y loopback. Para uso externo requiere HTTPS.
  El valor por defecto sigue siendo http://localhost:8501/ para uso local.
- Sección `email` de Streamlit Secrets: sender, app_password, smtp_host, smtp_port.
  SMTP_SSL verifica certificados. No se envió correo durante las pruebas.

La recuperación administrativa permanece bloqueada; el segundo factor mencionado
en el código original no está implementado. No dar por existente un flujo TOTP.
Planificar un procedimiento administrativo de recuperación autorizado antes de
abrir la aplicación a usuarios externos.

## Sesiones

- Inactividad: 30 minutos. Duración máxima: 8 horas.
- Los límites se comprueban cuando Streamlit procesa una interacción; no borran
  retroactivamente contenido ya visible o archivos que el usuario ya descargó.
- Desactivar/reactivar incrementa la versión y evita revivir sesiones anteriores.
- Restablecer contraseña incrementa la versión en la misma transacción.
- Las sesiones previas a esta actualización, sin tiempos de inicio/actividad,
  requieren iniciar sesión nuevamente cuando vuelvan a interactuar.
- No se programó un reinicio de procesos reales. Aplicar la versión en una ventana
  acordada si hay usuarios conectados.

## Archivos y exportaciones

Límites propios: 10 MB de entrada, 25 hojas, 100.000 filas por hoja, 200.000 filas
totales, 256 columnas y 2 millones de celdas. XLSX descomprimido: 100 MB y 2.000
entradas ZIP. Se rechazan nombres de columnas reservados y números no finitos.
Los desbordamientos de cálculos se rechazan. Fórmulas y textos potencialmente
interpretables como fórmulas se neutralizan al exportar XLSX/CSV.

Estos límites reducen el consumo; los parsers no se ejecutan en un proceso aislado.
Antes de aceptar archivos de Internet, añadir límites de memoria/CPU y de
solicitudes en el servidor o proxy. PDF y Excel se mantienen en memoria.

El historial guarda indicadores y, para análisis nuevos, su desglose por perfil.
No almacena los archivos originales ni permite reconstruir los PDF/XLSX anteriores.
Los reportes históricos conservan su estructura anterior sin migraciones.

## Respaldos y restauración

Crear una copia coherente con la API de SQLite, sin modificar el origen:

```powershell
.\.venv\Scripts\python.exe -B -m database.backups
```

La herramienta verifica integridad y nunca sobrescribe un destino. Se puede indicar
`--source` y `--output`. Guarda las copias fuera del equipo y con permisos restringidos;
SQLite contiene información sensible. backups/ está excluido de Git.

Antes de restaurar: obtener autorización, detener escrituras durante una ventana
acordada y respaldar la situación actual. Probar la copia en otra ruta privada,
comprobar integridad y funcionalidades. Solo después reemplazar el origen mediante
un procedimiento revisado. No existe restauración automática sobre una base real.
La restauración se validó leyendo una copia de una base sintética.

## Migraciones y datos heredados

La base real inspeccionada contiene las columnas requeridas. Cuatro empresas
antiguas no tienen propietario: no se asignaron a nadie. Se necesita identificar
su propietario autorizado antes de realizar una migración de datos.

Si una instalación antigua tiene un esquema incompleto, la aplicación se detiene
con un mensaje genérico. Revisar diferencias sobre una copia y preparar una
migración específica. No ejecutar indiscriminadamente módulos heredados ni
asignar empresas a una cuenta por defecto.

## Despliegue externo pendiente de decisión

1. Elegir equipo/servidor, dominio, responsables y volumen de usuarios.
2. Probar en un entorno independiente con SQLite sintético y configuración propia.
3. Configurar HTTPS con renovación de certificados y WebSocket detrás del proxy.
4. Mantener CORS y XSRF habilitados. Limitar tamaño, velocidad y frecuencia de
   solicitudes; el bloqueo de login actual es por cuenta, no global ni por IP.
5. Ejecutar una sola instancia con SQLite en disco local persistente y permisos
   restringidos. No compartir el archivo por una unidad de red ni entre réplicas.
6. Programar respaldos externos, retención de auditoría, monitorización de errores
   y ensayos de restauración. Los logs técnicos actuales evitan secretos y datos
   de excepciones; deben recogerse desde la salida del proceso.
7. Revisar vulnerabilidades de dependencias desde un entorno con acceso a sus
   fuentes oficiales. La red de esta sesión no permitió descargar desde PyPI.
8. Validar envío SMTP real solo después de autorización para enviar el mensaje.
9. Confirmar la puesta en marcha y posibles efectos sobre usuarios conectados.

Para varias réplicas o muchas escrituras concurrentes, planificar una migración
probada a PostgreSQL. Esta versión sigue usando SQLite; no declara escalabilidad
horizontal ni disponibilidad empresarial automática.
