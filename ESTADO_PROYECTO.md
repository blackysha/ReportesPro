# Estado de ReportesPro 3.0

Fecha de trabajo: 11 de noviembre de 2026, America/Santo_Domingo.

## Actualización: entrega local y prueba de cinco laptops

Esta sección sustituye las decisiones pendientes sobre destino y credenciales
descritas en el diagnóstico histórico de más abajo.

El propietario indicó que esta PC será la administradora y autorizó cambiar su
contraseña y reservarle el único rol admin. Se aplicó la operación con respaldo
previo: el administrador anterior pasó a usuario y se invalidaron sus sesiones.
No se desactivaron cuentas, borraron usuarios ni alteraron empresas/reportes.
Las otras contraseñas existentes se conservaron: Argon2 no permite recuperarlas.
Se añadieron cinco cuentas sintéticas de usuario para las laptops.

La entrega de TXT/CSV está en Documentos/contraseñas, fuera del repositorio.
No registrar aquí valores de contraseñas ni repetir la provisión. La contraseña
del propietario y los accesos de prueba solo están en sus archivos privados.
Hay inventario, manual, cinco accesos, clave administrativa aparte, plan de prueba,
identidad pública TLS, veinte CSV de datos sintéticos y sus resultados esperados.

La ACL de esa carpeta no pudo restringirse desde el entorno administrado. Se
conservan permisos heredados y se entregó PROTEGER_CARPETA.ps1 para que el
propietario aplique permisos privados desde su sesión real de Windows.

Se implementaron dos instancias: local:8501 para administrar, y LAN HTTPS:8502
sin acceso administrativo. Modo local exige loopback; modo LAN rechaza admin en
login, sesiones y funciones administrativas. Un índice único SQLite impide dos
cuentas con rol admin en la base real preparada. Se invalidaron tokens y bloqueos
locales anteriores de las cuentas cuyas claves se generaron.

TLS de prueba se verificó con OpenSSL y Python SSL: certificado autofirmado,
treinta días, clave privada fuera del repositorio y huella pública distribuible.
La IP privada inicial es 10.0.0.10; revisar ipconfig mañana y regenerar si cambia.
No se inició servidor LAN ni se modificó el firewall; hay scripts y guía para
hacerlo explícitamente en Windows. No hubo despliegue en Internet.

VS Code: ReportesPro.code-workspace, intérprete .venv, tareas de prueba/diagnóstico,
administración local y LAN, y depuración local. Se organizaron ejemplos en
examples/csv/, herramientas manuales en scripts/manual/, duplicados y bases de
respaldo antiguas en backups/archivo_legacy_20261111/ y exportaciones antiguas
en exports/legacy/. Se conservaron todos los archivos y la base real en su ruta.

Verificación de entrega sobre copia temporal de SQLite: cinco usuarios concurrentes,
veinte análisis, veinte reportes guardados solo en la copia, exportaciones PDF/XLSX/CSV
y administrador rechazado en LAN. Tiempo de esa ronda: 2,834 segundos en este equipo.
No equivale a una prueba de cinco laptops físicas. Resultado en el respaldo privado
preparacion_local_20261111_223055/prueba_5_usuarios.json.

Validación final: **51 pruebas aprobadas, 0 fallos**, en 17,733 segundos. Incluye
rechazo del administrador desde la interfaz LAN y acceso normal desde esa misma
instancia. Sintaxis de 39 archivos Python activos, JSON de VS Code, TOML y los
cinco scripts PowerShell comprobados; pip check y diagnóstico de configuración OK.

Comparación contra respaldo previo: las siete empresas y los doce reportes se
conservaron sin cambios; los cinco usuarios anteriores conservaron id, nombre,
correo y estado, y las cuatro contraseñas ajenas al propietario no se modificaron.
Total tras añadir cuentas de prueba: diez usuarios, con un único administrador.
Cambios de código y organización guardados localmente en la rama
desarrollo-reportespro-3 (commit de funcionalidad 955f430 y normalización posterior
de archivos de texto). No se ejecutó push ni se publicaron datos en GitHub.
Consultar docs/PRUEBA_LAN.md y docs/ESTRUCTURA.md antes de continuar.

## Alcance

Se continuó el código existente. No se reinició el proyecto, no se ejecutaron
migraciones sobre datos reales ni se cambiaron contraseñas, roles o estados reales.
No se publicó en GitHub ni se inició/reinició un servidor de producción.
La versión local quedó preparada para revisión; el despliegue depende del destino
que indique el propietario. No declarar terminada la preparación de producción.

## Respaldos y conservación

- Código original de los archivos modificados: backups/mejoras_20261111_220055/.
- SQLite coherente e íntegro: dentro de ese respaldo, reportespro_pre_entrega.db.
- Se registró una huella privada a mitad de la sesión y se verificó que las pruebas
  posteriores no cambiaron la base. Todas las pruebas anteriores también usaron
  rutas temporales parcheadas; no hay huella previa a la sesión completa.
- Base inspeccionada: integridad OK y sin inconsistencias de claves foráneas.
- Cuatro empresas siguen sin propietario. Se conservaron sin reasignarlas.
- Los cambios locales anteriores del usuario siguen presentes y sin commit.

## Correcciones implementadas

| Archivos | Cambio y motivo |
|---|---|
| auth/sessions.py, web_app.py | Limpieza de sesión aun con auditoría indisponible; inactividad de 30 minutos y duración de 8 horas. |
| database/usuarios.py, database/admin.py | Incrementar versión al desactivar/reactivar; auditoría transaccional; proteger al último administrador activo. |
| database/login_security.py, database/auditoria.py | Devolver versión junto con autenticación; registrar login y bloqueo en la transacción; comprobar credenciales fuera del bloqueo de escritura y revalidar hash/versión dentro. |
| database/db.py | Cierre explícito de conexiones; separación por REPORTESPRO_DB_PATH; acceso privado con cuenta activa, versión y comprobación transaccional al guardar. |
| database/schema.py, web_app.py | Inicialización completa de bases nuevas; comprobar bases existentes sin migrarlas automáticamente. |
| main.py | Límites de archivos/hojas/filas/columnas/celdas y XLSX descomprimido; rechazar infinitos, desbordamientos y columnas reservadas; exportación XLSX/CSV protegida contra fórmulas. |
| web_app.py | Descarga CSV y almacenamiento del desglose de indicadores por perfil para análisis nuevos; errores técnicos fuera de mensajes públicos. |
| auth/security.py, database/usuarios.py, database/recovery.py | Acotar longitud de contraseñas y tokens, mejorar validación de registro. |
| services/password_recovery_service.py | URL pública configurable; exigir HTTPS fuera de loopback y validar URL antes de generar token. |
| database/backups.py | Copia SQLite coherente, validada y sin sobrescribir destinos. |
| scripts/diagnostico.py, run_reportespro.ps1 | Diagnóstico de solo lectura y lanzador local que utiliza el entorno correcto. |
| requirements.txt | Fijar versiones directas del entorno probado. |
| .gitignore | Excluir archivos auxiliares SQLite, logs, respaldos heredados, uploads y exports. |
| AGENTS.md, README.md, README_WEB.md, docs/OPERACION.md | Instrucciones permanentes, alcance real y operación documentada. |

## Entorno

Python 3.14.7. Streamlit 1.66.1, Pandas 3.1.0, ReportLab 5.1.0,
OpenPyXL 3.1.5, xlrd 2.0.2 y argon2-cffi 25.1.0.

Argon2 faltaba en .venv y se incorporó desde la instalación compatible del Python
base, con sus dependencias y metadatos. No se descargó nada debido al bloqueo de
red. Se comprobó hash/verificación real, importación y pip check satisfactorio.

La clave LOGIN_SECURITY_KEY existente pasó validación de presencia y longitud;
su valor no se imprimió ni se cambió. SMTP real no se verificó ni se envió correo.

## Pruebas

Suite en tests/ con unittest y Streamlit AppTest. Todas las escrituras usan
TemporaryDirectory y DB_PATH parcheado; los correos se simulan.

Cobertura funcional comprobada: bloqueo/expiración/concurrencia, recuperación
caducada y de uso único, invalidación por contraseña y estado, autorización entre
propietarios, rechazo de versiones antiguas al guardar/consultar, rollback si falla
auditoría, último administrador, conexiones cerradas, esquema nuevo/incompleto,
respaldos recuperables y no sobrescribibles, validación de URL, cuatro perfiles de
análisis, duplicados, exportaciones, fórmulas, límites e infinitos.

AppTest comprueba login/logout, invitado, administrador, expiración por inactividad,
logout con auditoría caída, rechazo de sesión anterior y CSV/guardado con indicadores.
La prueba nueva de registro tenía una clave de widget equivocada; se corrigió para
usar las claves reales. Resultado final: **42 pruebas aprobadas, 0 fallos**, en
11,661 segundos. Incluye registro completo desde la interfaz.

Verificaciones adicionales aprobadas: pip check sin dependencias incompatibles,
sintaxis de 40 archivos Python, sintaxis del lanzador PowerShell, TOML de ejemplo,
git diff --check y exclusión de secretos/base/respaldos mediante git check-ignore.
Los avisos de Streamlit sobre ScriptRunContext corresponden al modo AppTest;
la prueba de auditoría caída produce intencionalmente un mensaje de error genérico.

Los scripts heredados prueba_login_seguridad.py y prueba_concurrencia_login.py
se adaptaron al esquema actual y pasaron con clave sintética en memoria y SQLite
temporal. No se ejecutaron probar_login.py, login_test.py, probar_correo.py ni
bootstrap_admin.py contra datos reales.

Comandos:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -m pip check
.\.venv\Scripts\python.exe -B -m scripts.diagnostico --security-config
```

## Pendientes y límites explícitos

1. Confirmar destino: PC local, red interna o Internet. El lanzador actual escucha
   solamente en 127.0.0.1. No se realizó despliegue.
2. Revisar propiedad de cuatro empresas antiguas antes de proponer una migración
   autorizada. No asignar automáticamente.
3. Para uso externo: dominio, HTTPS, proxy con límites globales y por IP, recursos
   de proceso, almacenamiento persistente, copias externas y monitorización.
4. Verificar SMTP con un destinatario autorizado y URL definitiva. No se cambió la
   configuración privada; el valor por defecto de URL es localhost.
5. Implementar recuperación administrativa reforzada: TOTP no está implementado y
   el flujo público sigue rechazando administradores deliberadamente.
6. Auditar vulnerabilidades publicadas desde un entorno con acceso a sus fuentes;
   fijar versiones directas no sustituye esa auditoría ni bloquea transitivas.
7. Definir retención de auditoría e intentos y ensayar cargas reales. Las pruebas
   de concurrencia no representan una prueba de carga empresarial.
8. SQLite se mantiene para una sola instancia y disco local. Varias réplicas
   requieren una arquitectura y migración distintas.
9. El historial conserva indicadores; no recupera documentos originales. Los
   archivos XLS se admiten mediante xlrd, pero no se probó una muestra XLS real.
10. El código conserva funciones generales de base de datos para uso interno;
    cualquier nueva pantalla debe usar las funciones privadas por propietario.
11. La expiración se aplica al interactuar con Streamlit; no revoca documentos ya
    descargados ni borra contenido previamente mostrado en una pestaña inactiva.
12. Al aplicar esta versión, las sesiones antiguas sin temporizadores necesitarán
    iniciar sesión de nuevo. Acordar ventana si hay usuarios conectados.

## Siguiente sesión

Leer AGENTS.md, este archivo y docs/OPERACION.md. Revisar git status y conservar
cambios previos. Continuar desde la decisión de destino y los pendientes; no
repetir el diagnóstico ni crear otra aplicación desde cero.

## Actualización 12/11/2026: accesos para prueba física

IP Wi-Fi comprobada con ipconfig: 192.168.1.86. Se respaldaron red.json,
identidad pública, certificado público y este estado antes de regenerar TLS.
Certificado y configuración regenerados para https://192.168.1.86:8502/.
Los accesos privados de ayer conservan la URL antigua; usar la nueva URL.
Se añadió Accesos ReportesPro/ con lanzador CMD, acceso web URL y guía de cinco
PC. Se intentó crear un acceso a esa carpeta en el escritorio; consultar resultado
de la sesión. No se cambiaron cuentas, claves ni datos de la base real.
51 pruebas aisladas aprobadas (19,373 s); pip check sin incompatibilidades.
El servidor LAN no se inició y el firewall no se modificó. Pendiente iniciar
manualmente y comprobar confianza TLS y conectividad desde las cinco PC reales.
No se publicó un enlace de Internet; requiere la misma red local.

## Actualización 12/11/2026: preparación de HTTPS para celulares

El aviso de Brave se debe al certificado autofirmado de la entrada LAN. No se
desactivaron verificaciones de certificados ni se sustituyó HTTPS por HTTP en
la red. La IP anterior conserva su certificado y seguirá mostrando el aviso.

Se añadió CSS estático en web_app.py para pestañas que se distribuyen en varias
filas, controles táctiles y campos de 16px en pantallas de hasta 640px. Se respaldó
web_app.py y este estado antes de editar, en backups/https_movil_*/.

Se prepararon run_acceso_seguro.ps1, scripts/instalar_conector_https.ps1 y dos
accesos CMD. El instalador descarga el ejecutable oficial y valida SHA256 con
el digest de GitHub. El lanzador prepara un Quick Tunnel de pruebas con URL
HTTPS temporal, backend exclusivo en loopback:8503 y modo lan que rechaza admin.
Conserva CORS/XSRF; publica únicamente al ejecutarlo, termina el túnel al salir
y no toca el servidor administrativo 8501 ni las credenciales. La URL generada
queda excluida de Git. Instrucciones y pruebas físicas: docs/ACCESO_SEGURO_MOVIL.md.

Validación: 51 pruebas aisladas aprobadas en 21,481 s, pip check OK y sintaxis
PowerShell comprobada. La red del entorno impidió consultar la API de GitHub;
no se descargó ni ejecutó cloudflared. No se inició servidor real, no se publicó
un enlace y no se verificaron certificado externo, WebSocket o teléfonos físicos.
No se declara resuelto el acceso HTTPS hasta completar esa puesta en marcha.
Pendientes: confirmar alcance Wi-Fi/Internet y dominio, instalar conector desde
Windows y probar Android/iPhone. Quick Tunnel es temporal para pruebas; para
producción siguen pendientes dominio/túnel permanente y controles de OPERACION.md.

## Revisión 16/11/2026: comprobación de últimos cambios

Primera ronda: 51 pruebas aprobadas en 15,994 s; pip check, diagnóstico de
solo lectura, AST de 38 archivos Python, seis scripts PowerShell y diff check OK.
Un administrador y cuatro empresas sin propietario. Se comprobó la existencia
del conector HTTPS y de un acceso temporal, sin ejecutarlo ni validar su binario.
No se verificaron dispositivos físicos ni el enlace público. La revisión anterior
contenía caracteres dañados al escribir desde consola; esta sección los corrige.

## Avance 16/11/2026: tres primeros pendientes

Pedido: avanzar en dispositivos, propiedad y recuperación. Antes del punto 4,
mostrar al propietario el proceso completo de publicación para que pueda aprender.
Ese punto no se ha iniciado; no se ha publicado la aplicación por Internet.

Cambios y resultados:

- ipconfig confirma Wi-Fi 192.168.1.102, diferente de 192.168.1.86. Se respaldaron
  configuración TLS, identidad pública, certificado público, accesos y estado en
  backups/validacion_tres_puntos_20261116_114054/. Se regeneró TLS para la IP actual
  y se actualizaron el acceso URL y la guía de cinco PC. Clave privada fuera de Git.
- HTTPS y WebSocket comprobados realmente en loopback con certificado y hostname
  verificados y SQLite sintético: 29 elementos de interfaz, sin excepción.
  scripts/verificar_https_local.py reproduce esa prueba y termina su propio servidor.
- Intento de Chrome: Page.enable agotó el tiempo de espera. Una comprobación
  directa mostró procesos GPU rechazados por permisos; no se validó el CSS visual.
  scripts/verificar_navegador.mjs prepara prueba aislada de cuatro tamaños y guarda
  resultados privados en backups/. No se desactivó el sandbox de Chrome.
- database/ownership.py y scripts/asignar_empresas.py preparan asignaciones
  explícitas, vista previa por defecto, respaldo antes de aplicar, autenticación
  administrativa en la consola y auditoría transaccional. No fusionan ni borran.
  Se espera el mapa de propietarios del usuario; ninguna empresa real se reasignó.
- database/admin_recovery.py y scripts/recuperar_admin_local.py implementan el
  procedimiento local documentado, con vista previa, contraseña oculta, respaldo,
  control de versión, invalidación de sesiones y auditoría en la misma transacción.
  Solo se ejecutó la vista previa real. No se cambiaron claves reales.
  Confía en la protección de Windows y del archivo SQLite; no incorpora TOTP ni
  añade autenticación remota. La recuperación pública de admin sigue bloqueada.
- Se añadió EMPRESA_ASIGNADA a los eventos permitidos de auditoría.
- scripts/verificar_smtp.py: presencia de campos OK; conexión sin autenticación
  ni envío rechazada con PermissionError por el entorno. No se verificaron claves
  SMTP ni entrega. Falta el destinatario autorizado. La URL pública permanente
  sigue sin configurarse; no se puede validar un enlace definitivo de recuperación.
- tests/test_ownership.py y tests/test_admin_recovery.py: preservación de datos,
  permisos, aislamiento, concurrencia por versión y rollback de auditoría.
  La primera ronda nueva tenía una expectativa incorrecta de acceso denegado en
  una prueba; se corrigió para esperar PermissionError, el contrato existente.
- Suite final: **58 pruebas aprobadas, 0 fallos**, en 17,460 s. pip check,
  diagnóstico de integridad/configuración y git diff --check correctos.
- Procedimiento, comandos, límites y pendientes en docs/VALIDACION_Y_RECUPERACION.md.

No se alteraron usuarios, contraseñas, roles, empresas o reportes reales. No se
inició servidor sobre la base real, túnel público ni se modificó el firewall.
Se conservaron los cambios previos sin commit. No se ejecutó push.

Para completar el pedido hacen falta: respuesta sobre dispositivos disponibles,
asignación explícita de las cuatro empresas y destinatario autorizado para un
mensaje de prueba. SMTP requiere ejecutarse desde Windows con red disponible si
persiste la restricción de este entorno. No marcar estos puntos como completados.

## Continuación 16/11/2026: recuperación desde la interfaz

El propietario pidió continuar después de identificar las cuatro empresas y su
cuenta administrativa. Se mantuvo pendiente la asignación: no hay un mapa
empresa/usuario autorizado. Sigue vigente explicar archivos, comandos y finalidad
antes de cada ejecución del punto 4; no se inició publicación ni operación externa.

Se añadieron cuatro pruebas AppTest en tests/test_web.py:

- Solicitar recuperación de usuario normal, capturar el correo simulado, abrir
  su enlace HTTPS en la interfaz, cambiar contraseña, limpiar el token de la URL,
  comprobar versión de sesión, rechazo de clave anterior y de reutilización.
- Administrador y cuenta inexistente: misma respuesta pública sin correo ni token.
- Error SMTP: respuesta genérica sin mostrar el detalle técnico privado.
- Confirmación distinta: rechazar el cambio sin consumir el enlace.

Resultado: **62 pruebas aprobadas, cero fallos**, en 20,452 s. Todas las escrituras
fueron en SQLite temporal y los correos de la suite se simularon. HTTPS/WebSocket
local aislado volvió a pasar (29 elementos); diagnóstico real de solo lectura OK.
git diff --check sin errores. No hubo cambios de código funcional en esta ronda.

Se intentó un único mensaje SMTP sin tokens ni claves hacia la cuenta identificada
por el propietario. Resultado: PermissionError; no se completó el envío. No se
reintentó ni se alteró la configuración privada. Probar desde PowerShell normal
de Windows con scripts.verificar_smtp --conexion --enviar y confirmar recepción.
Este mensaje de prueba no restablece la contraseña del administrador.

Respaldo previo: backups/recuperacion_interfaz_20261116_122503/.
Las empresas y credenciales reales se conservaron. Siguen pendientes las pruebas
físicas, el mapa de propietarios y la entrega real por SMTP.

## Continuación 16/11/2026: guía de publicación para el propietario

Se recuperó el contexto desde este registro y los documentos locales; no se
dispuso del texto completo del otro chat. Se añadió docs/PUBLICAR_PASO_A_PASO.md
con explicación del error «Hola» en la terminal, comandos PowerShell, diferencias
entre local/LAN/Internet, uso del lanzador HTTPS existente, ruta hacia un dominio
permanente y consecuencias de trasladar Python/SQLite a otro servidor.
docs/REGISTRO_DISPOSITIVOS.md permite documentar pruebas físicas sin marcarlas
como realizadas. README_WEB.md enlaza la guía. No cambió código funcional.

Respaldo previo de estado y README: backups/guia_publicacion_20261116_212036/.
Verificación: unittest discover -s tests -v terminó con código 0; pip check
sin requisitos incompatibles; git diff --check sin errores (avisos de finales
de línea en archivos previamente modificados). No se añadieron pruebas para
estos cambios de documentación. Se conservaron los cambios anteriores.

Se consultó documentación oficial de Cloudflare y Streamlit. No se ejecutó
instalación del conector, túnel, despliegue, envío de correo ni cambios de datos
reales. La elección PC/servidor y dominio sigue pendiente del propietario.
La guía prepara el punto 4 para revisión; no equivale a publicación completada.
Persisten el mapa de propietarios, SMTP real y dispositivos físicos pendientes.

## Cierre solicitado: retomar el 17/11/2026

El propietario pidió guardar el avance para mañana y detener el trabajo aquí.
Los archivos y cambios previos quedan conservados localmente, sin commit nuevo,
push ni publicación. Este registro resume el contexto; no es una copia literal
del historial de chat.

Para retomar: leer AGENTS.md, este estado, docs/OPERACION.md y
docs/PUBLICAR_PASO_A_PASO.md; revisar git status sin descartar cambios.
La guía de publicación y docs/REGISTRO_DISPOSITIVOS.md ya están guardados.
La última suite terminó con código 0, pip check pasó y diff --check no tuvo errores.

Continuar con la elección pendiente: mantener esta PC como servidor o usar uno
permanente, y confirmar si dispone de dominio/proveedor. Después completar las
pruebas físicas, el mapa autorizado de propietarios de cuatro empresas y SMTP.
Conservar la publicación como etapa final y explicar archivos, comandos y finalidad
antes de ejecutarlos para que el propietario aprenda el proceso. No declarar
compatibilidad con todos los móviles sin pruebas ni publicar datos reales como demo.
No repetir provisión de cuentas, cambios de contraseñas ni migraciones anteriores.

## Piloto de WhatsApp del 18/11/2026

El flujo implementado permite vincular y desvincular un número desde Mi cuenta,
consultar el último reporte de una empresa propia y pedir un PDF de sus indicadores.
El código dura diez minutos y solo funciona desde el número que se indicó al
generarlo. El webhook verifica la firma de Meta y está preparado para ejecutarse
en un proceso local separado. El bot queda habilitado en la interfaz al configurar
`REPORTESPRO_WHATSAPP_NUMERO` para cuentas de usuario.

Cambios en `services/whatsapp.py`, `services/whatsapp_webhook.py`, `web_app.py`,
`database/db.py`, `requirements.txt` y `tests/test_whatsapp.py`.
Respaldo previo de código y estado en `backups/whatsapp_20261118_122934/`.
La guía [docs/WHATSAPP.md](docs/WHATSAPP.md) detalla el piloto.
La suite completa pasó con 66 pruebas. Las pruebas de WhatsApp usaron SQLite
temporal y simularon las respuestas de Meta.
Queda pendiente confirmar `hello_world` en Meta y conectar el callback HTTPS
con una instancia de prueba y datos sintéticos para validar la entrega real.

## Cierre semanal de ventas del 19/11/2026

El análisis y las exportaciones existentes ya cubrían la validación por fila,
la consolidación entre hojas y el historial por empresa. El flujo nuevo añade
la carga de varios archivos, la semana de lunes a domingo, los ingresos por día
y la comparación opcional con un total independiente. Las incidencias identifican
archivo, hoja y registro. Los archivos idénticos se rechazan por contenido.
El guardado exige ventas válidas, cero incidencias y coincidencia con la referencia
si se introdujo una. El historial muestra los ingresos por semana y guarda los
metadatos del cierre en el JSON existente. Se conserva el análisis de un documento.

Verificación: 69 pruebas aprobadas y `pip check` correcto. La prueba del panel
inyecta archivos sintéticos, comprueba el bloqueo por diferencia y verifica el
guardado y el historial en SQLite temporal. El respaldo de código y documentación
se guardó en `backups/cierre_semanal_20261119_094254/`. No se cambió el esquema
ni se operó sobre la base real.

El siguiente hito es un piloto con un encargado y un cierre aprobado. Queda
por comprobar el ahorro de tiempo y la autonomía de uso. Los archivos distintos
pueden solaparse y el flujo requiere cantidades positivas y una sola moneda.
Ver [instrucciones del cierre](README_WEB.md#cierre-semanal-de-ventas).

## Cierre multimoneda del 19/11/2026

El cierre semanal admite DOP, USD y EUR en una misma carga. La columna `moneda`
identifica la divisa por fila. Para hojas sin esa columna, el operador puede
seleccionar una moneda predeterminada. Las celdas vacías dentro de una columna
`moneda` y los códigos no admitidos generan incidencias.

Los totales, la serie diaria, las referencias, el PDF, el Excel y el historial
mantienen las monedas separadas, sin conversión cambiaria. El CSV conserva la
moneda por fila. Los cierres históricos sin moneda se muestran como «Sin
especificar» y conservan sus importes. No se modificó la base real.

Pasaron las 70 pruebas y `pip check`. Una comprobación adicional del panel
verificó que un cierre antiguo y uno multimoneda aparecen juntos en el historial.
Respaldo previo en `backups/monedas_20261119_095820/`.

## Accesos de escritorio y celular del 19/11/2026

El acceso directo ReportesPro.lnk del escritorio ejecuta el lanzador local desde
la carpeta activa y abre el navegador en el puerto 8501. Al iniciar con el
acceso directo, Streamlit vuelve a ejecutar el código guardado cuando detecta
cambios. Si ya responde una instancia local, abre esa instancia.

El registro en `docs/avances.html` se sirve por separado en el puerto 8504 de
la interfaz Wi-Fi. El enlace al momento de la entrega es
`http://192.168.1.124:8504/avances`. Al abrir el acceso directo, el lanzador
muestra la dirección Wi-Fi detectada e inicia el registro si hace falta.
AGENTS.md indica actualizarlo al completar y verificar cada tarea.

Verificación: destino y argumentos del acceso directo leídos después de
guardarlo, sintaxis de PowerShell válida, Streamlit aislado con respuesta 200
y la página de avances accesible por su IP Wi-Fi desde la PC. El registro
respondió 404 ante una ruta a la base de datos. Queda por comprobar desde
un celular físico conectado al mismo Wi-Fi. No se publicó en Internet ni se
modificó el firewall o la base real. Respaldo previo en
`backups/accesos_20261119_101152/`.

## Copia de desarrollo para colaborar

DESARROLLO.md explica como clonar la rama y abrir una copia local con SQLite
separado. Se preparo un ZIP con codigo y CSV sinteticos. Se verificaron la
integridad del ZIP y la apertura del formulario de registro desde una extraccion
limpia con SQLite temporal. Pasaron 70 pruebas y pip check. La publicacion de la
rama y la comprobacion de visibilidad siguen pendientes por falta de conexion
con GitHub desde este entorno.
