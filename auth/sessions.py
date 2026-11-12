"""Estado de sesión independiente de Streamlit, verificable sin datos reales."""

import logging
import time

logger = logging.getLogger(__name__)
IDLE_SECONDS = 30 * 60
MAX_SECONDS = 8 * 60 * 60


def iniciar_sesion(estado, usuario, ahora=None):
    ahora = time.monotonic() if ahora is None else ahora
    estado.clear()
    estado.update(
        rp_usuario=usuario,
        rp_invitado=False,
        rp_resultado=None,
        rp_version_sesion=usuario["version_sesion"],
        rp_inicio=ahora,
        rp_actividad=ahora,
    )


def sesion_expirada(estado, ahora=None):
    ahora = time.monotonic() if ahora is None else ahora
    inicio = estado.get("rp_inicio")
    actividad = estado.get("rp_actividad")
    if inicio is None or actividad is None:
        return True
    if ahora < inicio or ahora < actividad:
        return True
    if ahora - inicio >= MAX_SECONDS or ahora - actividad >= IDLE_SECONDS:
        return True
    estado["rp_actividad"] = ahora
    return False


def limpiar_sesion(estado, registrar, evento="LOGOUT"):
    """La indisponibilidad de auditoría nunca impide salir de la sesión."""
    usuario = estado.get("rp_usuario")
    estado.clear()
    if usuario is not None:
        try:
            registrar(usuario["id"], evento, "Sesión finalizada")
        except Exception:
            # No incluir excepción, datos de usuario ni credenciales en logs.
            logger.error("No se pudo registrar la finalización de una sesión")
