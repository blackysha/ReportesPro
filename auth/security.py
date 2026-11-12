
"""Funciones de seguridad para ReportesPro 3.0."""

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError,
)

password_hasher = PasswordHasher()


def crear_hash_password(password: str) -> str:
    """Genera un hash seguro de una contraseña."""
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError(
            "La contraseña debe tener entre 12 y 1024 caracteres."
        )

    return password_hasher.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña sin almacenar su valor original."""
    if not isinstance(password, str) or len(password) > 1024:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False
