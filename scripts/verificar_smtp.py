"""Comprobar configuración y TLS; enviar solo al pedirlo explícitamente."""

import argparse
import smtplib
import ssl
from pathlib import Path
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conexion', action='store_true')
    parser.add_argument('--enviar', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / '.streamlit' / 'secrets.toml'
    config = tomllib.loads(path.read_text(encoding='utf-8-sig')).get('email', {})
    if not all(config.get(k) for k in ('sender','app_password','smtp_host','smtp_port')):
        print('SMTP: configuración incompleta; valores ocultos.')
        return 1
    print('SMTP: campos requeridos presentes; valores ocultos.')
    if args.conexion:
        with smtplib.SMTP_SSL(config['smtp_host'], int(config['smtp_port']), context=ssl.create_default_context(), timeout=15) as smtp:
            status, _ = smtp.noop()
            if status != 250:
                raise RuntimeError('Respuesta SMTP inesperada.')
        print('Conexión SMTP y certificado TLS: OK. Sin autenticación ni envío.')
    if args.enviar:
        from services.email_service import enviar_correo
        recipient = input('Destinatario autorizado para un único mensaje: ').strip()
        if not recipient or '@' not in recipient or any(c in recipient for c in '\r\n,;'):
            raise ValueError('Destinatario no admitido.')
        if input('Escribe ENVIAR para confirmar un único correo de prueba: ') != 'ENVIAR':
            print('Envío cancelado.')
            return 1
        enviar_correo(recipient, 'ReportesPro 3.0 - Prueba SMTP',
                      'Mensaje de prueba autorizado de ReportesPro. No contiene contraseñas ni enlaces de recuperación. No modifica ninguna cuenta.')
        print('SMTP aceptó el mensaje. Confirmar recepción y carpeta de spam con el destinatario.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('Verificación no completada. Tipo: ' + type(exc).__name__ + '. Sin mostrar configuración ni credenciales.')
        raise SystemExit(1) from None
