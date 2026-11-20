# Validación, propiedad y recuperación local

## Última comprobación: recuperación en interfaz

Suite ampliada: **62 pruebas aprobadas**, cero fallos, en 20,452 segundos.
Incluye el recorrido del enlace por la interfaz con correo simulado, cambio de
clave, limpieza del token de la URL y rechazo de reutilización. También comprueba
que admin/cuenta inexistente no generan enlaces, que un error SMTP no expone
detalles y que una confirmación distinta no consume el enlace.
HTTPS/WebSocket local y diagnóstico de solo lectura correctos.

El intento de un único correo real de prueba terminó con PermissionError.
Para completar la comprobación desde PowerShell normal de Windows:

```powershell
Set-Location -LiteralPath 'C:\Users\Jhon PC\Documents\sistema_reportes_python'
.\.venv\Scripts\python.exe -B -m scripts.verificar_smtp --conexion --enviar
```

Primero verifica TLS sin enviar. Si pasa, solicita el destinatario y la palabra
ENVIAR para un único mensaje sin contraseñas ni tokens. Usar la dirección indicada
por el propietario y comprobar recepción y spam. No crear cuentas ni modificar
credenciales para esta prueba. Si falla, conservar solo el tipo de error que
muestra la herramienta; no compartir secrets.toml ni contraseñas.

## Resultado del 16/11/2026

58 pruebas aisladas aprobadas en 17,460 segundos. Se añaden pruebas para la
asignación transaccional de empresas y recuperación administrativa local.
HTTPS y WebSocket reales comprobados con certificado verificado, en loopback y
SQLite temporal: 29 elementos de interfaz recibidos sin excepción.
No constituye una prueba de Android/iPhone ni de cinco PC físicas.

La IP Wi-Fi obtenida mediante ipconfig es 192.168.1.102. Se regeneró el certificado
LAN con OpenSSL, se verificó el par certificado/clave y se actualizaron el acceso
URL y la guía de cinco PC. Los archivos reemplazados se respaldaron en
backups/validacion_tres_puntos_20261116_114054/. No se inició el servidor real ni
se modificó el firewall. La dirección LAN es https://192.168.1.102:8502/.
El certificado LAN sigue siendo autofirmado; no equivale a un certificado público.

## Pruebas desde dispositivos

Antes de iniciar una prueba física, confirmar qué dispositivos están disponibles
y preparar una base de demostración separada de la real mediante
REPORTESPRO_DB_PATH, con cuentas y empresas sintéticas. No dar por probado un
dispositivo a partir de AppTest ni de emulación de tamaños.

En cada dispositivo comprobar acceso, sesión, carga de CSV sintético, descarga
PDF/XLSX/CSV, guardado e historial. Con dos cuentas, verificar que ninguna ve
empresas o reportes de la otra. Probar cierre de sesión y rechazo de admin en
la entrada de usuarios. Anotar dispositivo, navegador, hora y resultado.

Para repetir HTTPS/WebSocket sin exponer datos:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.verificar_https_local
```

Para comprobar tamaños en Chrome con perfil temporal y SQLite sintético:

```powershell
node scripts/verificar_navegador.mjs
```

Este último requiere Node con WebSocket integrado y Chrome en su ruta habitual.
El primer intento del entorno administrado agotó el tiempo de Page.enable; una
comprobación directa posterior mostró procesos GPU de Chrome rechazados por
permisos. No se obtuvo evidencia visual. No se desactivó el sandbox del navegador.
Los resultados de cada ejecución se guardan en backups/navegador_*/.

## Empresas sin propietario

Se identificaron cuatro empresas: #1 (sin reportes), #2 (ocho reportes), #3 y #4
(un reporte cada una). No se han reasignado; se espera la decisión del propietario.
Las dos empresas de nombres parecidos no se fusionan automáticamente.

La herramienta muestra una vista previa sin escrituras por defecto. Ejemplo
ilustrativo, únicamente después de confirmar que el mapa corresponde al pedido:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.asignar_empresas --asignar 1:5
```

Cada pareja significa EMPRESA:USUARIO. Repetir --asignar para cada empresa.
Tras revisar el mapa autorizado, --aplicar pide autenticación administrativa,
confirmación escrita y crea un respaldo SQLite coherente antes de asignar.
La asignación y auditoría son una sola transacción; un error cancela el lote.
No altera reportes, no fusiona empresas y rechaza empresas ya asignadas.
No incluir contraseñas en comandos ni archivos de planes.

## Correo

Los campos SMTP requeridos están presentes; sus valores no se imprimieron.
La prueba de conexión TLS terminó con PermissionError en el entorno administrado,
antes de autenticar o enviar. No permite concluir si las credenciales funcionan.
Falta un destinatario autorizado y confirmar recepción, incluida carpeta de spam.

```powershell
.\.venv\Scripts\python.exe -B -m scripts.verificar_smtp --conexion
```

Con el destinatario autorizado, --enviar pide su dirección y confirmación ENVIAR
antes de enviar un único mensaje sin claves ni tokens. No modifica cuentas.
No repetir envíos automáticamente. La recuperación real debe usar una URL
REPORTESPRO_PUBLIC_URL válida para el acceso elegido; hoy no hay una URL pública
permanente configurada. Un enlace temporal deja de servir al terminar el túnel.

## Recuperación del administrador

Se define un procedimiento fuera de la web. No se habilitó recuperación pública
para administradores ni se implementó TOTP. El procedimiento confía en la cuenta
Windows del operador que puede leer y modificar SQLite: el modo local y la
confirmación escrita no son un segundo factor ni una barrera frente a otro
operador que ya controle esos archivos. Mantener Windows bloqueado y restringir
los permisos del proyecto, base, secretos y respaldos a sus responsables.

1. Verificar identidad del propietario y obtener autorización específica para
   cambiar su clave. Este procedimiento no se ejecuta como prueba automática.
2. Desde la PC administradora, revisar una vista previa:

   ```powershell
   .\.venv\Scripts\python.exe -B -m scripts.recuperar_admin_local
   ```

3. Verificar la ruta de trabajo y REPORTESPRO_DB_PATH. La herramienta requiere
   un único administrador activo. Coordinar que sus sesiones quedarán invalidadas.
4. Solo tras esa autorización, usar --aplicar. Pide RECUPERAR seguido del ID
   mostrado y la nueva contraseña dos veces, con entrada oculta. Crea un respaldo
   coherente antes de escribir. No guardar la clave en argumentos ni registros.
5. La transacción cambia solo la clave del admin, incrementa versión de sesión,
   invalida enlaces pendientes, limpia su bloqueo local y registra auditoría.
   Un fallo de auditoría revierte todos esos cambios. Una versión concurrente
   distinta cancela la operación. No cambia roles, estados ni otras cuentas.
6. El propietario verifica el acceso desde localhost:8501; la entrada LAN debe
   seguir rechazando al administrador. Conservar el respaldo en carpeta privada.

La herramienta está preparada y probada con cuentas sintéticas. En esta sesión
solo se ejecutó la vista previa contra la base real. La contraseña real se conserva.

## Publicación y operación: punto 4

Todavía no iniciado. Antes de configurar servicios o publicar se explicará al
propietario el recorrido completo: destino de alojamiento, URL y DNS, HTTPS,
separación de administración, variables privadas, almacenamiento persistente,
copias externas y restauración, monitorización, validación y reversión.
Se mostrarán los archivos y comandos concretos antes de ejecutarlos. Primero se
validará un entorno sintético; la publicación real requerirá el destino acordado.
