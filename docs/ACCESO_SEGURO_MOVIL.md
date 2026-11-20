# HTTPS y celulares

La URL de IP privada del puerto 8502 usa un certificado autofirmado de prueba.
Aunque cifra la conexion, los navegadores no reconocen a su emisor. Regenerarlo
no elimina ese aviso. No desactivar la proteccion de Brave ni instalar la clave
privada en los dispositivos.

## Enlace temporal para pruebas desde cualquier red

Se preparo `run_acceso_seguro.ps1`, sin ponerlo en marcha. Utiliza Cloudflare
Quick Tunnel para obtener una URL HTTPS con certificado reconocido por los
navegadores modernos, sin dominio propio. Permite entrar desde PC, Android o
iPhone, con Wi-Fi o datos moviles. Requiere Internet en la PC anfitriona.

1. En **ReportesPro - Accesos**, abrir **0 - Instalar conector HTTPS** una vez.
   Descarga desde el repositorio oficial de Cloudflare y verifica la huella
   SHA256 publicada por GitHub antes de instalar. No publica la aplicacion.
   Si la descarga falla, descargar **Windows 64-bit Executable** desde la pagina oficial:
   https://developers.cloudflare.com/tunnel/downloads/
   El enlace de descarga debe pertenecer a `github.com/cloudflare/cloudflared`.
2. Guardarlo como `.local/cloudflared.exe` en la carpeta del proyecto. Si Windows
   no muestra extensiones, comprobar que no termine en `.exe.exe`.
3. En el acceso del escritorio **ReportesPro - Accesos**, abrir
   **3 - Iniciar HTTPS temporal**. Esta accion publica la entrada de usuarios
   por Internet mientras la ventana este abierta; realizarla al comenzar la
   prueba acordada, con archivos sinteticos.
4. Esperar el mensaje **ENLACE PARA PC Y CELULARES**. Abrir esa URL o el acceso
   **3 - Abrir enlace seguro temporal** que se genera en la misma carpeta.
   Compartir la URL nueva, no la direccion IP anterior. No aceptar avisos de
   certificado si aparecieran en la URL nueva.
5. Cada persona utiliza su cuenta normal. El administrador no puede entrar
   por este enlace. Sigue en `http://127.0.0.1:8501/` desde esta PC.
6. Mantener la PC encendida, sin suspension, y la ventana abierta. Al finalizar,
   pulsar Ctrl+C. El enlace anterior deja de funcionar y cambia en cada inicio.

El servicio interno escucha solo en `127.0.0.1:8503` con el modo que rechaza
administradores. Cloudflare transporta la conexion mediante un tunel cifrado;
el tramo HTTP queda dentro de esta PC. No se abre un puerto en el router ni se
deshabilitan CORS, XSRF, TLS del navegador o la separacion administrativa.
No ejecutar cloudflared apuntando a 8501.

Quick Tunnel es para pruebas, sin garantia de disponibilidad. No es una entrega
de produccion. La direccion HTTPS no sustituye la autenticacion ni garantiza
por si sola la seguridad completa de la aplicacion. Para una direccion estable
se necesita definir dominio y cuenta del proveedor, configurar un tunel
permanente, limites del acceso publico y completar los pendientes de OPERACION.md.

## Comprobacion en dispositivos

En Brave/Chrome de Android y Safari de iPhone actualizados, abrir la URL HTTPS:

- Comprobar que no aparece advertencia de certificado y que el navegador muestra
  conexion segura en la informacion del sitio.
- En pantalla vertical, verificar las cuatro pestanas de acceso, los campos y
  el teclado. Abrir la barra lateral con el control de Streamlit si esta plegada.
- Iniciar sesion con un usuario de prueba, subir un CSV sintetico desde Archivos,
  analizar, descargar PDF/Excel/CSV y consultar historial. En iPhone, las descargas
  pueden abrirse en una vista previa o quedar en Archivos/Descargas.
- Comprobar que no se muestran datos de otra cuenta. Probar un telefono con
  Wi-Fi desactivado para verificar acceso por datos moviles.

No se afirma compatibilidad con navegadores antiguos ni se ha realizado aun la
prueba fisica en Android/iPhone. El CSS mejora pestanas y controles en pantallas
de hasta 640px; las tablas conservan el desplazamiento horizontal de Streamlit.

Referencias oficiales:
https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
https://developers.cloudflare.com/tunnel/downloads/
