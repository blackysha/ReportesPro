# Administración local y cinco laptops

## Entradas separadas

- `run_reportespro.ps1`: administración local, `http://127.0.0.1:8501/`.
- `run_pruebas_red.ps1`: usuarios de la LAN, HTTPS en la IP privada y puerto 8502.
  `REPORTESPRO_ACCESS_MODE=lan` rechaza cuentas administradoras tanto en login como
  en validación de sesiones y operaciones administrativas.
- El modo local exige dirección de escucha loopback. No se utiliza una IP enviada
  por el navegador ni una huella del dispositivo como prueba de identidad.
- Esto limita el acceso por red a la administración; no es un bloqueo criptográfico
  contra quien posea una copia de la base, del código y de los archivos privados.

Las dos instancias usan SQLite en esta PC. Las otras laptops solo necesitan
navegador y red; no deben copiar la base ni instalar cinco servidores.

## VS Code

Abrir `ReportesPro.code-workspace`. El intérprete seleccionado es
`.venv/Scripts/python.exe`. Las tareas incluyen pruebas, diagnóstico,
administrador local y prueba LAN. F5 depura únicamente el servidor local.
No se copiaron credenciales a settings, tasks, launch ni al workspace.

## Entrega privada

Los TXT y CSV de accesos están fuera del repositorio, en Documentos/contraseñas.
Las contraseñas antiguas no son recuperables. El inventario las marca como tales;
solo se entregan claves nuevas expresamente generadas.

- `04_ADMIN_SOLO_ESTA_PC.txt`: propietario y nueva contraseña; no compartir.
- `03_ACCESOS_5_LAPTOPS.txt`: cinco usuarios normales para la prueba.
- `LAPTOP_XX_ACCESO.txt`: repartir solo el archivo que corresponde al equipo.
- `02_GUIA_REPORTESPRO.txt`: manual completo.
- `05_PLAN_PRUEBAS_5_LAPTOPS.txt`: secuencia de prueba simultánea.
- `06_CERTIFICADO_RED.txt`: huella pública del certificado.
- `07_PERMISOS_CARPETA.txt`: estado real de permisos.

El entorno administrado no permitió cambiar la ACL de la carpeta privada. Sus
permisos se conservaron heredados; no se afirma que sean exclusivos. Ejecutar
`PROTEGER_CARPETA.ps1` desde la sesión real del propietario para restringirla.
No distribuir la carpeta completa: contiene claves en texto plano por solicitud
del propietario. No versionarla, subirla a GitHub ni enviarla por chat/correo.

## Certificado y red

El certificado autofirmado de prueba dura treinta días. Su clave privada está
fuera del repositorio. El certificado público se puede repartir; verificar su
huella en cada laptop antes de confiar en él. No deshabilitar TLS globalmente.

La IP configurada se guarda en `.local/red.json`, excluido de Git. Si cambia:

```powershell
.\scripts\configurar_tls_red.ps1 -ServerIP TU_IP_PRIVADA
```

La regeneración actualiza la configuración y la huella del certificado. Los TXT
y CSV de acceso contienen la URL de la preparación original: usar la URL nueva
indicada en `06_CERTIFICADO_RED.txt` si la IP cambia. Las claves no cambian al
regenerar TLS.

En una red privada confiable, si el firewall impide la conexión, revisar y ejecutar
desde una terminal de Windows con privilegios administrativos:

```powershell
.\scripts\configurar_firewall_pruebas.ps1
```

La regla se limita a la subred local, perfil Privado, Python del proyecto y TCP
8502. No abrir 8501 ni reenviar puertos en el router. El agente no modificó el
firewall. Al terminar:

```powershell
.\scripts\configurar_firewall_pruebas.ps1 -Remove
```

## Prueba funcional

Cada equipo inicia sesión con una cuenta distinta, registra su propia empresa y
procesa sus cuatro CSV desde `examples/csv/pruebas_5_laptops/`. Debe analizar,
descargar y guardar cada uno una sola vez. Comparar indicadores con
`resultados_esperados.csv` y comprobar que no aparecen empresas de otras cuentas.
Las incidencias de los archivos son intencionales.

La verificación automatizada de la entrega clona SQLite a una carpeta temporal y
ejecuta cinco usuarios concurrentes con veinte análisis/exportaciones/guardados.
No escribe en la base real. Para repetirla sin mostrar claves:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.verificar_entrega --private-directory RUTA_CARPETA_PRIVADA
```

La medición automatizada de backend no representa cinco dispositivos reales,
tiempos de Wi-Fi ni una prueba de carga de producción. La prueba física y la
confianza del certificado deben comprobarse mañana en cada laptop.

No se inició el servicio LAN ni se publicaron cambios en Internet/GitHub.
