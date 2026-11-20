# Copia de desarrollo de ReportesPro 3.0

## Obtener el proyecto

Para colaborar desde GitHub, acepta la invitación al repositorio y ejecuta:

```powershell
git clone --branch desarrollo-reportespro-3 https://github.com/blackysha/ReportesPro.git
cd ReportesPro
```

Si recibiste el ZIP de desarrollo, extráelo y abre la carpeta extraída en PowerShell.
El ZIP es una copia de la versión al momento de prepararlo. Para compartir cambios
y recibir actualizaciones, usa el repositorio de GitHub cuando esté disponible.

## Abrir la aplicación en Windows

Con Python 3.14 instalado, ejecuta desde la carpeta que contiene `web_app.py`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Cada vez que quieras iniciar la copia de desarrollo, ejecuta este segundo bloque
en PowerShell. La base SQLite de prueba queda en `.local` y se conserva entre inicios.

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
$env:REPORTESPRO_DB_PATH = Join-Path (Get-Location).Path '.local\reportespro-desarrollo.db'
$env:LOGIN_SECURITY_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
$env:REPORTESPRO_ACCESS_MODE = 'local'
.\.venv\Scripts\python.exe -m streamlit run web_app.py --server.address 127.0.0.1 --server.port 8510 --server.runOnSave true
```

Abre `http://127.0.0.1:8510`, elige **Crear cuenta** y usa un correo de
prueba como `diseno@example.com` con una contraseña propia de al menos 12
caracteres. Crea una empresa de ejemplo y carga `examples/csv/ventas_prueba.csv`.
Streamlit recarga la interfaz cuando guardas cambios en el código.

## Compartir cambios de diseño

Crea tu rama desde `desarrollo-reportespro-3`. Después de guardar y probar los
cambios, haz un commit, sube tu rama y abre un pull request hacia
`desarrollo-reportespro-3`. Los cambios guardados aparecen enseguida en tu
copia local. Ambos verán los cambios compartidos al actualizar su rama con Git.

Usa datos sintéticos durante las pruebas. Mantén las bases SQLite, los secretos
de Streamlit y las credenciales de cada equipo fuera del repositorio y del ZIP.
