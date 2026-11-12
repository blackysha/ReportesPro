"""Entrega privada solicitada por el propietario; nunca imprime credenciales."""

import argparse
import csv
import os
from pathlib import Path
import subprocess
from datetime import datetime

from database import db
from database.backups import crear_respaldo
from database.provisioning import preparar_accesos
from main import analyze

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def carpeta_privada(destino):
    destino = Path(destino).resolve()
    if destino == PROJECT_ROOT or PROJECT_ROOT in destino.parents:
        raise ValueError("Las credenciales deben guardarse fuera del repositorio.")
    destino.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Usar al propietario real, no a la identidad técnica del agente aislado.
        path_literal = str(destino).replace("'", "''")
        owner = subprocess.run([
            "powershell.exe", "-NoProfile", "-Command",
            f"$ErrorActionPreference='Stop'; (Get-Acl -LiteralPath '{path_literal}').Owner",
        ], capture_output=True, check=True).stdout.decode("cp1252").strip()
        resultado = subprocess.run(
            ["icacls", str(destino), "/inheritance:r", "/grant:r", f"{owner}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
            capture_output=True,
        )
        estado = "RESTRINGIDOS al propietario y SYSTEM" if resultado.returncode == 0 else "HEREDADOS: el entorno administrado no permite cambiar la ACL"
        (destino / "07_PERMISOS_CARPETA.txt").write_text(
            "PERMISOS DE LA CARPETA PRIVADA\n" + estado + "\n"
            "Ejecutar PROTEGER_CARPETA.ps1 desde tu propia sesión de Windows para aplicar permisos privados a toda la carpeta.\n"
            "No compartir la carpeta completa: contiene claves en texto plano solicitadas por el propietario.\n",
            encoding="utf-8-sig",
        )
        (destino / "PROTEGER_CARPETA.ps1").write_text(PROTEGER, encoding="ascii")
    return destino


def escribir_texto(ruta, texto):
    with Path(ruta).open("x", encoding="utf-8-sig", newline="") as f:
        f.write(texto)


def escribir_csv(ruta, filas, campos):
    with Path(ruta).open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def archivos_prueba(destino):
    carpeta = destino / "csv_pruebas"
    carpeta.mkdir(exist_ok=True)
    esperados = []
    for n in range(1, 6):
        textos = {
            "ventas": f"fecha,producto,cantidad,precio\n2026-11-11,Producto A,2,{100*n}\n2026-11-12,Producto B,3,{50*n}\n2026-11-12,Producto incorrecto,-1,10\n",
            "inventario": f"producto,stock,costo\nProducto A,10,{20*n}\nProducto B,0,{30*n}\nProducto A,1,{20*n}\nProducto incorrecto,-2,10\n",
            "clientes": f"nombre,correo,fecha_registro\nCliente A {n},clientea{n}@example.invalid,2026-11-01\nCliente B {n},clienteb{n}@example.invalid,2026-11-02\nCliente A repetido,clientea{n}@example.invalid,2026-11-03\nCliente incorrecto,correo_incorrecto,2026-11-04\n",
            "general": f"nombre,correo,edad,monto\nPersona A {n},personaa{n}@example.invalid,25,{100*n}\nPersona B {n},personab{n}@example.invalid,40,{150*n}\nPersona incorrecta,personac{n}@example.invalid,-1,20\n",
        }
        previstos = {
            "ventas": (3, 2, 1, "ingresos_totales", 350*n),
            "inventario": (4, 2, 2, "valor_inventario", 200*n),
            "clientes": (4, 2, 2, "clientes_validos", 2),
            "general": (3, 2, 1, "monto_total_valido", 250*n),
        }
        for perfil, texto in textos.items():
            nombre = f"laptop_{n:02d}_{perfil}.csv"
            contenido = texto.encode("utf-8-sig")
            with (carpeta / nombre).open("xb") as f:
                f.write(contenido)
            indicadores = analyze(nombre, contenido)["indicators"][perfil]
            total, validos, invalidos, indicador, valor = previstos[perfil]
            assert indicadores["registros_totales"] == total
            assert indicadores["registros_validos"] == validos
            assert indicadores["registros_con_incidencias"] == invalidos
            assert indicadores[indicador] == valor
            esperados.append(dict(laptop=n, archivo=nombre, registros_totales=total, registros_validos=validos, registros_con_incidencias=invalidos, indicador=indicador, valor_esperado=valor))
    escribir_csv(carpeta / "resultados_esperados.csv", esperados, list(esperados[0]))


def documentos(destino, claves, cuentas, server_ip):
    propietario = next(c for c in claves if c["rol"] == "admin")
    normales = [c for c in claves if c["rol"] == "usuario" and c["activo"] == 1][:5]
    if len(normales) != 5:
        raise RuntimeError("Se requieren cinco accesos de usuario para la prueba.")
    por_id = {c["id"]: c["password"] for c in claves}
    inventario = [dict(c, password=por_id.get(c["id"], "NO RECUPERABLE: hash Argon2; clave anterior conservada")) for c in cuentas]
    escribir_csv(destino / "inventario_usuarios.csv", inventario, ["id", "nombre", "correo", "rol", "activo", "password"])
    escribir_csv(destino / "admin_local.csv", [propietario], ["id", "nombre", "correo", "rol", "activo", "password"])
    accesos = [dict(laptop=i, correo=c["correo"], password=c["password"], rol="usuario", url=f"https://{server_ip}:8502/") for i, c in enumerate(normales, 1)]
    escribir_csv(destino / "accesos_5_laptops.csv", accesos, list(accesos[0]))
    lineas = ["INVENTARIO PRIVADO DE USUARIOS - REPORTESPRO 3.0", "Las contraseñas antiguas no son recuperables. No se exportan hashes.", "Las claves nuevas indicadas se generaron expresamente para esta entrega.", ""]
    for c in inventario:
        lineas.append(f"ID: {c['id']} | Nombre: {c['nombre']} | Correo: {c['correo']} | Rol: {c['rol']} | Activo: {c['activo']}\nContraseña: {c['password']}\n")
    escribir_texto(destino / "01_INVENTARIO_USUARIOS.txt", "\n".join(lineas))
    escribir_texto(destino / "04_ADMIN_SOLO_ESTA_PC.txt", f"ADMINISTRADOR EXCLUSIVO\nCorreo: {propietario['correo']}\nNueva contraseña: {propietario['password']}\nURL: http://127.0.0.1:8501/\n\nLa cuenta solo puede iniciar sesión en la instancia local. La instancia LAN rechaza administradores.\nNo compartas este TXT ni admin_local.csv. Se invalidaron las sesiones y tokens anteriores.\nNo existe una vinculación criptográfica al hardware: la protección depende de localhost, del modo de acceso y del control de los archivos de Windows.\n")
    lineas = ["ACCESOS PRIVADOS PARA CINCO LAPTOPS", "No repartir el archivo del administrador ni el inventario completo.", ""]
    for acceso in accesos:
        bloque = f"LAPTOP {acceso['laptop']:02d}\nCorreo: {acceso['correo']}\nContraseña: {acceso['password']}\nURL: {acceso['url']}\nRol: usuario, sin administración\nArchivos: csv_pruebas/laptop_{acceso['laptop']:02d}_*.csv\n"
        lineas.append(bloque)
        escribir_texto(destino / f"LAPTOP_{acceso['laptop']:02d}_ACCESO.txt", bloque + "\nComparar el certificado con 06_CERTIFICADO_RED.txt antes de aceptar la conexión.\n")
    escribir_texto(destino / "03_ACCESOS_5_LAPTOPS.txt", "\n".join(lineas))
    escribir_texto(destino / "00_LEEME.txt", "ENTREGA PRIVADA DE REPORTESPRO 3.0\nEstado de credenciales: PREPARADO\n\n01: inventario de cuentas, con las claves antiguas marcadas como no recuperables.\n02: manual de funcionamiento.\n03: cinco accesos de usuario para la prueba en red.\n04: tu nueva contraseña de administrador; no compartir.\n05: protocolo de pruebas simultáneas.\n06: identidad pública del certificado de la red, si se preparó TLS.\n07: estado real de permisos de la carpeta y script para protegerla desde Windows.\nCSV: equivalentes privados de inventario, administrador y accesos.\ncsv_pruebas: veinte archivos sintéticos y resultados esperados; se pueden distribuir.\nLAPTOP_XX_ACCESO: distribuir solamente el de la laptop correspondiente.\n\nNo enviar la carpeta completa por correo, chat ni GitHub. Contiene claves en texto plano por solicitud del propietario. Consulta 07_PERMISOS_CARPETA.txt y ejecuta PROTEGER_CARPETA.ps1 desde tu propia sesión. No sustituye un gestor de contraseñas.\n")
    escribir_texto(destino / "02_GUIA_REPORTESPRO.txt", GUIA.format(project=PROJECT_ROOT, ip=server_ip))
    escribir_texto(destino / "05_PLAN_PRUEBAS_5_LAPTOPS.txt", PLAN.format(project=PROJECT_ROOT, ip=server_ip))


PROTEGER = '''$ErrorActionPreference = 'Stop'
$privateRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$expectedName = 'contrase' + [char]0x00F1 + 'as'
if ((Split-Path -Leaf $privateRoot) -ine $expectedName) {
    throw 'Ejecuta este archivo solo dentro de la carpeta privada solicitada.'
}
$privateSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $privateRoot /inheritance:r /grant:r "*$($privateSid):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' /T /C
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron proteger todos los archivos. Revisa la ACL desde Windows.' }
Set-Content -LiteralPath (Join-Path $privateRoot '07_PERMISOS_CARPETA.txt') -Encoding UTF8 -Value 'RESTRINGIDOS: permisos aplicados desde la sesion de Windows al usuario actual y SYSTEM.'
Write-Output 'Permisos privados aplicados. No se mostraron credenciales.'
'''


GUIA = """REPORTESPRO 3.0 - MANUAL DE FUNCIONAMIENTO

UBICACIÓN: {project}
Aplicación: Python, Streamlit, SQLite, Pandas, OpenPyXL y ReportLab.
Se ejecuta en una sola PC anfitriona; las laptops usan el navegador. No copiar la base a cada laptop.

INICIO LOCAL
Abrir ReportesPro.code-workspace en VS Code. Usar la tarea 'ReportesPro: administrador local'
o ejecutar .\\run_reportespro.ps1 en PowerShell dentro del proyecto.
Entrar en http://127.0.0.1:8501/ con el archivo 04_ADMIN_SOLO_ESTA_PC.txt.
El correo del propietario es el único administrador de la base actual.

INICIO DE LA PRUEBA LAN
Ejecutar .\\run_pruebas_red.ps1 desde otra terminal. La configuración privada de red
está en .local/red.json. La dirección preparada es https://{ip}:8502/.
No se inició el servidor ni se cambió el firewall automáticamente.
Si la IP cambia, ejecutar .\\scripts\\configurar_tls_red.ps1 -ServerIP NUEVA_IP antes de la prueba.
El modo LAN deshabilita la administración incluso con la contraseña correcta.
El certificado es local y autofirmado; comparar la huella de 06_CERTIFICADO_RED.txt
en cada equipo antes de confiar en él. No deshabilitar las comprobaciones TLS globalmente.
Se necesita una red privada confiable, una misma Wi-Fi/LAN y permiso del firewall para TCP 8502.
No crear redirecciones de puerto en el router y no publicar esta prueba en Internet.

USO NORMAL
1. Iniciar sesión con la cuenta asignada; cinco errores bloquean esa cuenta por quince minutos.
2. Registrar una empresa propia, por ejemplo Empresa prueba laptop 01.
3. Seleccionar empresa y subir CSV/XLSX/XLS.
4. Pulsar Analizar documento. Revisar indicadores, datos válidos e incidencias.
5. Descargar PDF, XLSX, CSV o ZIP con PDF/Excel.
6. Guardar análisis en el historial. Consultarlo bajo la misma empresa y cuenta.
7. Cerrar sesión. El modo invitado no permite guardar historial.

PERFILES Y COLUMNAS
Ventas: fecha, producto, cantidad, precio. Calcula ingresos, unidades y evolución mensual.
Inventario: producto, stock, costo. Calcula valor y productos agotados; elimina duplicados por producto.
Clientes: nombre, correo, fecha_registro. Valida correo y fecha; elimina duplicados por correo.
General: nombre, correo, edad, monto. Valida edades y montos y calcula monto válido.
No mezclar perfiles en un mismo CSV; un Excel puede contener hojas de distintos perfiles.
Los campos hoja_origen, fila_origen y perfil_analisis son reservados.
Los archivos de ejemplo son sintéticos; no contienen información de clientes reales.

LÍMITES
10 MB por archivo, 25 hojas, 100.000 filas por hoja, 200.000 filas totales,
256 columnas y dos millones de celdas; XLSX descomprimido hasta 100 MB.
Valores negativos no permitidos se excluyen; infinitos y desbordamientos se rechazan.
Las fórmulas se neutralizan en exportaciones. El historial guarda indicadores, no los archivos originales.
Sesión: treinta minutos de inactividad y ocho horas de duración, comprobados al interactuar.

ADMINISTRACIÓN
La instancia local permite consultar usuarios y activar/desactivar otras cuentas.
No existe pantalla pública para otorgar el rol admin. Un índice de SQLite impide dos administradores.
La recuperación de contraseña por correo solo admite usuarios normales; las cuentas sintéticas
@reportespro.invalid no reciben correos. La recuperación administrativa por TOTP no está implementada.
Desactivar/reactivar y cambiar contraseña invalidan sesiones anteriores.
No se reasignaron empresas antiguas sin propietario: requieren una decisión expresa.

REPOSITORIO Y DATOS
Código en auth/, database/, services/ y scripts/. Pruebas en tests/, ejemplos en examples/csv/,
documentación en docs/. Respaldos en backups/ y exportaciones antiguas en exports/legacy/.
Archivo real: database/reportespro.db. No borrarlo, moverlo ni subirlo a GitHub.
Secretos: .streamlit/secrets.toml. No compartir. El certificado y su clave privada están fuera del repositorio.
No se publican automáticamente cambios en GitHub.

COMPROBACIONES Y RESPALDO
.\\.venv\\Scripts\\python.exe -B -m unittest discover -s tests -v
.\\.venv\\Scripts\\python.exe -B -m scripts.diagnostico --security-config
.\\.venv\\Scripts\\python.exe -B -m database.backups
Las pruebas automáticas escriben solo en SQLite temporal y no envían correos.
No ejecutar herramientas de provisión nuevamente: rotan contraseñas o rechazan cuentas ya preparadas.

ANTES DE INTERNET
Esta prueba no equivale a un despliegue público. Faltan dominio y certificados de confianza,
límites por IP/globales, monitorización, copias externas, revisión de dependencias y recuperación
administrativa reforzada. SQLite admite esta prueba en una sola anfitriona; no se ofrece escalabilidad horizontal.
"""

PLAN = """PRUEBA SIMULTÁNEA CON CINCO LAPTOPS

PC ANFITRIONA
Mantener encendida, conectada a corriente y sin suspensión. Usar un solo servidor LAN,
una sola base SQLite y conexiones separadas por navegador. No ejecutar cinco servidores
ni abrir la base desde una carpeta de red. Anotar la IP Wi-Fi actual con ipconfig.
IP preparada: {ip}; URL: https://{ip}:8502/.

PREPARACIÓN
1. Verificar que las cinco laptops estén en la misma red privada y sin aislamiento de clientes.
2. Preparar el certificado con scripts/configurar_tls_red.ps1 si cambió la IP.
3. Si Windows bloquea acceso, revisar scripts/configurar_firewall_pruebas.ps1 y ejecutarlo
   manualmente como administrador. La regla se limita al perfil Privado, subred local y TCP 8502.
4. Ejecutar run_pruebas_red.ps1. Mantener la terminal abierta.
5. Distribuir únicamente LAPTOP_XX_ACCESO.txt, sus cuatro CSV y la huella pública del certificado.
6. Cada equipo verifica la identidad del certificado y abre su propia sesión.
7. Reservar el administrador para la PC anfitriona en http://127.0.0.1:8501/.

RONDA 1 - INGRESO E INDEPENDENCIA
A una señal, iniciar las cinco sesiones. Registrar una empresa diferente en cada cuenta.
Comprobar que ninguna cuenta ve las empresas o el historial de otra.

RONDA 2 - ANÁLISIS CONCURRENTE
Subir a la vez laptop_XX_ventas.csv. Analizar, descargar PDF/XLSX/CSV y guardar una vez.
Los ingresos esperados son 350 x número de laptop, con tres registros y dos válidos.
Repetir con inventario, clientes y general. Comparar cada resultado con csv_pruebas/resultados_esperados.csv.
Revisar que los archivos descargados y el historial correspondan a la propia empresa.
Esperado por laptop: cuatro reportes guardados si se guarda una vez cada perfil.

RONDA 3 - SESIONES Y SEGURIDAD
Cerrar una sesión: las otras cuatro deben seguir funcionando.
No probar contraseñas de terceros. Si se verifica bloqueo, usar solo una cuenta de prueba asignada.
Desde la consola local, desactivar exclusivamente una cuenta sintética y verificar que su siguiente
interacción cierre la sesión. Reactivarla y confirmar que la sesión vieja no revive.
Esta acción modifica datos de prueba; no usar cuentas reales para la prueba.

REGISTRO DE RESULTADOS
Anotar equipo, hora, duración aproximada, perfil, resultado esperado/obtenido y errores.
Si falla, capturar el mensaje sin mostrar claves. No repetir un guardado sin comprobar el historial.
La medición automatizada de backend no sustituye esta prueba real con cinco navegadores.

FINALIZACIÓN
Cerrar las cinco sesiones, detener la terminal LAN con Ctrl+C y mantener la instancia local si se necesita.
Retirar manualmente la regla de firewall de pruebas si se creó. Conservar los reportes de prueba
hasta revisarlos; no borrar datos reales ni eliminar cuentas sin aprobación.
Guardar un respaldo y revisar ESTADO_PROYECTO.md en {project}.
"""


def crear_entrega(propietario, destino, server_ip, restablecer_existentes=False):
    destino = carpeta_privada(destino)
    if any((destino / nombre).exists() for nombre in ("00_LEEME.txt", "04_ADMIN_SOLO_ESTA_PC.txt", "inventario_usuarios.csv")):
        raise FileExistsError("Ya existe una entrega privada. No se sobrescribió.")
    archivos_prueba(destino)
    backup = PROJECT_ROOT / "backups" / ("antes_accesos_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
    crear_respaldo(db.DB_PATH, backup)
    preparar_accesos(
        propietario, restablecer_existentes=restablecer_existentes,
        entregar=lambda claves, cuentas: documentos(destino, claves, cuentas, server_ip),
    )
    leeme = destino / "00_LEEME.txt"
    leeme.write_text(leeme.read_text(encoding="utf-8-sig").replace("Estado de credenciales: PREPARADO", "Estado de credenciales: APLICADO"), encoding="utf-8-sig")
    return destino


def main():
    parser = argparse.ArgumentParser(description="Configurar accesos y guardar la entrega privada fuera de Git")
    parser.add_argument("--owner-email", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-ip", required=True)
    parser.add_argument("--reset-existing", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Preparación sin aplicar. Usar --apply solo con autorización explícita de cambios de cuentas.")
        return
    try:
        crear_entrega(args.owner_email, args.output, args.server_ip, args.reset_existing)
    except Exception as exc:
        print("No se completó la entrega privada. Tipo de error: " + type(exc).__name__)
        raise SystemExit(1) from None
    print("Entrega privada creada. Credenciales guardadas únicamente en los archivos locales solicitados.")


if __name__ == "__main__":
    main()
