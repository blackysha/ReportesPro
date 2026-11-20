# Publicar ReportesPro 3.0 y probarlo en móviles

Guía preparada el 16/11/2026. Los comandos de publicación de este documento
todavía no se han ejecutado. Leer cada paso antes de usarlo.

## 1. Dónde escribir cada cosa

Las explicaciones y preguntas se escriben en el chat. PowerShell ejecuta comandos;
si se escribe «Hola chat» allí, Windows intenta encontrar un programa llamado Hola.
Ese error por sí solo no modifica ReportesPro. Si la ventana dice CMD, abrir
PowerShell antes de utilizar los ejemplos de esta guía.

En PowerShell, entrar en el proyecto:

```powershell
Set-Location -LiteralPath 'C:\Users\Jhon PC\Documents\sistema_reportes_python'
```

Copiar solo el contenido del bloque, sin las marcas de Markdown ni el prefijo PS>.
No compartir contraseñas, secrets.toml ni la base de datos al pedir ayuda.

## 2. Qué significa publicar esta aplicación

ReportesPro necesita un proceso Python/Streamlit activo y su base SQLite.
Copiar un HTML o subir únicamente el código a GitHub no pone en funcionamiento
el inicio de sesión, el análisis ni el historial.

| Modalidad | Dirección | Disponibilidad | Uso |
|---|---|---|---|
| Local | http://127.0.0.1:8501/ | Solo esta PC | Administración |
| LAN | IP privada y puerto 8502 | Misma red; servidor activo | Prueba interna con certificado de prueba |
| HTTPS temporal | URL generada trycloudflare.com | Internet; esta PC encendida y túnel activo | Demostración |
| Dominio y túnel permanente | Subdominio elegido | Depende de esta PC y del servicio | Acceso estable tras completar preparación |
| Servidor dedicado | Dominio elegido | Independiente de esta PC | Requiere preparar y validar el alojamiento |

127.0.0.1 en el teléfono significa el propio teléfono: no es la PC. Para acceso
por datos móviles se necesita una URL pública. HTTPS cifra el transporte; la
cuenta de ReportesPro sigue siendo necesaria para los datos privados.

## 3. Comprobar antes de publicar

Estos comandos verifican dependencias y funciones con bases temporales; no
inician una publicación ni envían correos:

```powershell
.\.venv\Scripts\python.exe -B -m pip check
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Si fallan, revisar el resultado antes de continuar. Para una demostración sin
datos reales, preparar primero una base independiente y cuentas sintéticas.
REPORTESPRO_DB_PATH debe apuntar a ella; el lanzador temporal hereda esa variable.
No copiar la base real para compartirla ni cambiar su ruta en procesos activos.
La provisión de cuentas de demostración debe revisarse por separado: una base
nueva vacía no incluye automáticamente los cinco usuarios de prueba anteriores.

## 4. Publicación temporal: ejecutar al comenzar la prueba acordada

Archivo: scripts/instalar_conector_https.ps1. Descarga el conector desde la
publicación oficial de Cloudflare y comprueba su SHA256; no publica la web.
Si el archivo ya existe, el instalador no lo sobrescribe ni vuelve a verificarlo.

```powershell
.\scripts\instalar_conector_https.ps1
```

Si Windows bloquea scripts, detenerse y revisar el mensaje o usar los accesos
preparados de ReportesPro; no cambiar globalmente la política de ejecución.

Archivo: run_acceso_seguro.ps1. **Este comando sí expone la entrada de usuarios
por Internet** mientras permanece activo. Inicia Streamlit en 127.0.0.1:8503,
modo lan (rechaza al administrador), crea el túnel y configura la URL pública
para los enlaces de recuperación de ese proceso. No apunta al puerto 8501.

```powershell
.\run_acceso_seguro.ps1
```

Esperar ENLACE PARA PC Y CELULARES. Copiar la URL HTTPS completa y abrirla en el
navegador del teléfono. También se genera el acceso
Accesos ReportesPro/3 - Abrir enlace seguro temporal.url.
Usar cuentas normales y archivos sintéticos. Mantener la PC sin suspensión.
Finalizar con Ctrl+C; el enlace caduca y será diferente en el siguiente inicio.
La recuperación por correo requiere además SMTP funcional: crear un túnel no
comprueba el envío ni la recepción. Los enlaces enviados dejan de servir al
cerrar ese túnel.

Si no se genera una URL, revisar conexión y salida del lanzador. Si aparece
una advertencia de certificado, comprobar que se abrió la URL HTTPS generada,
no la IP privada con certificado autofirmado. No desactivar las protecciones
del navegador. Si se queda cargando, verificar que Streamlit siga activo y que
la red permita WebSocket; conservar CORS y XSRF habilitados.

## 5. Prueba física antes de declarar compatibilidad

No se puede asegurar funcionamiento en todos los dispositivos sin probarlos.
Usar navegadores actualizados y registrar resultados en
[REGISTRO_DISPOSITIVOS.md](REGISTRO_DISPOSITIVOS.md).

1. Android con Chrome o Brave; iPhone/iPad con Safari; computadora con su navegador.
2. Abrir HTTPS sin advertencias, en vertical y horizontal. Revisar pestañas,
   barra lateral, campos, teclado y botones sin solapamientos. Las tablas pueden
   necesitar desplazamiento horizontal dentro de su contenedor.
3. Iniciar sesión con una cuenta sintética, cargar un CSV de examples/csv,
   analizar, descargar PDF/XLSX/CSV, guardar y comprobar historial.
4. Entrar con otra cuenta: no debe ver empresas ni reportes privados de la primera.
5. Comprobar cierre de sesión y rechazo del administrador en el enlace público.
6. Repetir con Wi-Fi desactivado y datos móviles activos. Si solo funciona por
   Wi-Fi, todavía no está verificado el acceso desde Internet.
7. En iPhone, revisar Archivos/Descargas o la vista previa de las descargas.

## 6. Después: dirección permanente

Para conservar esta PC como servidor, el recorrido será:

1. Elegir dominio/subdominio y cuenta propietaria de Cloudflare. Revisar condiciones
   y coste actuales antes de contratar. No se ha comprado ni configurado ninguno.
2. Crear un túnel administrado desde el panel de Cloudflare y conectar esta PC
   siguiendo su guía oficial. El token se guarda de forma privada, fuera de Git.
3. Preparar un proceso persistente separado de Streamlit para usuarios, en
   127.0.0.1:8503 y REPORTESPRO_ACCESS_MODE=lan. El lanzador temporal actual
   no es un servicio permanente y no se reutiliza como tal sin adaptación.
4. Configurar la ruta pública HTTPS del subdominio hacia http://127.0.0.1:8503.
   Mantener 8501 exclusivamente local. Un túnel no requiere abrir ese puerto
   administrativo en el router.
5. Fijar REPORTESPRO_PUBLIC_URL a la dirección definitiva. Mantener estable
   LOGIN_SECURITY_KEY y establecer la ruta SQLite persistente del proceso.
6. Preparar arranque automático, reinicio ante fallo, límites de recursos y
   solicitudes, respaldos externos, monitorización y restauración ensayada.
7. Validar primero con datos sintéticos y completar el registro de dispositivos.
   Después revisar la puesta en marcha real y su ventana de mantenimiento.

Para funcionar con esta PC apagada, elegir un servidor compatible con Python
y disco persistente. Probar primero una instalación separada. Mantener una sola
instancia SQLite; no compartir el archivo por red ni crear réplicas que lo escriban.
La administración y los datos deberán operar en el mismo entorno servidor: una
copia SQLite de esta PC no se sincroniza automáticamente. Ese cambio requiere
definir y autorizar la migración y la forma de administración privada antes de
trasladar datos. El alojamiento Sites del plugin usa Workers y no ejecuta este
proyecto Python/SQLite directamente.

## 7. Revisión final y reversión

Antes de publicar datos reales: resolver propietarios de las cuatro empresas,
comprobar SMTP con el destinatario autorizado, validar restauración y revisar
los pendientes de [OPERACION.md](OPERACION.md). Verificar que el administrador
sigue rechazado desde Internet y que los usuarios solo ven sus propios datos.

Si falla una demostración temporal, Ctrl+C detiene su lanzador y su túnel.
En un despliegue permanente, detener la ruta pública o el servicio de usuarios
según el procedimiento acordado. Una reversión de código no revierte los datos:
no reemplazar SQLite con una copia antigua sin autorización y respaldo previo.

Referencias oficiales consultadas para esta guía:

- [Cloudflare: túneles temporales y límites](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Cloudflare: crear un túnel administrado](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
- [Streamlit: despliegue y proxy para dominio](https://docs.streamlit.io/knowledge-base/deploy/deploy-streamlit-domain-port-80)
