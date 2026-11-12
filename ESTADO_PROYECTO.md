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
