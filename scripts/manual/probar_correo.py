"""Prueba del servicio SMTP de ReportesPro 3.0."""

from services.email_service import enviar_correo_prueba


def main():
    print("\n=== PRUEBA SMTP REPORTESPRO ===")

    destinatario = input("Correo destinatario: ").strip()

    if not destinatario:
        print("Debes introducir un correo.")
        return

    try:
        enviar_correo_prueba(destinatario)
        print("\nCorreo enviado correctamente.")
        print("Revisa tu bandeja de entrada y spam.")

    except Exception as error:
        print("\nNo se pudo enviar el correo.")
        print(f"Tipo de error: {type(error).__name__}")
        print(
            "Revisa la configuración SMTP, "
            "las credenciales y tu conexión."
        )


if __name__ == "__main__":
    main()
