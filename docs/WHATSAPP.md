# Piloto de WhatsApp en ReportesPro

## Flujo de prueba

1. En la aplicación de Meta, agrega tu WhatsApp como destinatario de prueba y
   confirma que recibes `hello_world` desde el número de prueba.
2. Usa una copia de prueba de ReportesPro con una base sintética y una cuenta
   normal, una empresa y por lo menos un análisis guardado. Streamlit y el
   webhook deben recibir la misma ruta absoluta en `REPORTESPRO_DB_PATH`.
3. En el entorno de Streamlit, define `REPORTESPRO_WHATSAPP_NUMERO` con el número
   de prueba de Meta en formato internacional. Arranca la copia de prueba.
4. Configura las siguientes variables en el entorno del webhook y ejecuta
   `.\.venv\Scripts\python.exe -B -m services.whatsapp_webhook`.

| Variable | Valor |
| --- | --- |
| `WHATSAPP_APP_SECRET` | Secreto de la aplicación de Meta |
| `WHATSAPP_VERIFY_TOKEN` | Valor aleatorio privado elegido para verificar el callback |
| `WHATSAPP_PHONE_NUMBER_ID` | Identificador del número de prueba en Meta |
| `WHATSAPP_GRAPH_VERSION` | Versión de Graph API que muestra el panel de Meta, con prefijo `v` |
| `WHATSAPP_ACCESS_TOKEN` | Token válido del entorno de prueba de Meta |

5. Configura HTTPS para reenviar únicamente `/webhooks/whatsapp` al puerto local
   `8503`. En el panel de Meta registra la URL HTTPS completa como callback,
   introduce el mismo token de verificación y suscribe el campo `messages`.
6. Ve a **Mi cuenta → WhatsApp**. Introduce tu número con código de país, genera
   un código y envíalo al número de prueba desde ese mismo teléfono antes de
   diez minutos.
7. Escribe **Último reporte**. Si hay varias empresas, responde
   **Último reporte ID** con el ID correspondiente. Usa el comando
   **PDF ID_EMPRESA ID_REPORTE** que indica el resumen para recibir ese documento.

El PDF se genera con los indicadores guardados en el historial. La fecha que
aparece corresponde a la generación del reporte. Los indicadores del período
aparecen cuando el reporte los conserva.

Usa una sola instancia del webhook para este piloto. El servidor de prueba
escucha en loopback y procesa los eventos de forma síncrona. Registra los IDs
ya respondidos en SQLite para omitir reintentos confirmados. Si Meta acepta un
envío pero se corta la conexión antes de registrarlo, un reintento puede generar
una respuesta duplicada. Conserva los secretos fuera de Git y desactiva el
registro de la cadena de consulta en el proxy del piloto.

Los vínculos y los IDs de entrega se guardan en el archivo auxiliar
`<nombre-de-la-base>.whatsapp.db`, al lado de la base de ReportesPro. Al cambiar
la contraseña o desactivar la cuenta, la versión de sesión invalida el vínculo.
También se puede retirar desde **Mi cuenta → WhatsApp**. Usa datos sintéticos
durante la prueba porque el chat y los documentos se envían a través de Meta.

- [Verificación y firma del webhook](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/)
- [Ejemplo oficial de envío de documento por ID](https://www.postman.com/meta/whatsapp-business-platform/request/zjtbdpz/send-document-message-by-id)
