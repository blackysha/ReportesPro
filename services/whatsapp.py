"""Vinculación y consultas de WhatsApp con los permisos de ReportesPro."""

import hashlib
import io
import re
import secrets
import sqlite3
import time
import unicodedata
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from database import db
from database.usuarios import obtener_version_sesion


def _almacen():
    # Usar una base auxiliar por instalación, incluida cada base de prueba.
    conexion = sqlite3.connect(
        db.DB_PATH.with_suffix(".whatsapp.db"), factory=db.Conexion, timeout=10
    )
    try:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS vinculos (
                usuario INTEGER PRIMARY KEY,
                version INTEGER NOT NULL,
                telefono TEXT NOT NULL UNIQUE,
                codigo TEXT UNIQUE,
                caduca INTEGER
            )
        """)
    except Exception:
        conexion.close()
        raise
    return conexion


def _telefono(numero):
    numero = numero.strip().removeprefix("+")
    if not re.fullmatch(r"[1-9][0-9]{6,14}", numero):
        raise ValueError("Escribe el número con su código de país, sin espacios.")
    return numero


def _huella(codigo):
    return hashlib.sha256(codigo.encode("ascii")).hexdigest()


def generar_codigo(usuario, version, numero):
    numero = _telefono(numero)
    if obtener_version_sesion(usuario) != version:
        raise PermissionError("Vuelve a iniciar sesión.")
    codigo = secrets.token_hex(16)
    ahora = int(time.time())
    with _almacen() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        conexion.execute("DELETE FROM vinculos WHERE caduca <= ?", (ahora,))
        vinculo = conexion.execute(
            "SELECT usuario, version FROM vinculos WHERE telefono = ?", (numero,)
        ).fetchone()
        if vinculo is not None and vinculo[0] != usuario:
            if obtener_version_sesion(vinculo[0]) == vinculo[1]:
                raise ValueError("Ese número ya está asociado o pendiente de confirmación.")
            conexion.execute("DELETE FROM vinculos WHERE usuario = ?", (vinculo[0],))
        conexion.execute("DELETE FROM vinculos WHERE usuario = ?", (usuario,))
        conexion.execute(
            "INSERT INTO vinculos VALUES (?, ?, ?, ?, ?)",
            (usuario, version, numero, _huella(codigo), ahora + 600),
        )
    return f"VINCULAR {codigo}"


def desvincular(usuario, version):
    if obtener_version_sesion(usuario) != version:
        raise PermissionError("Vuelve a iniciar sesión.")
    with _almacen() as conexion:
        conexion.execute("DELETE FROM vinculos WHERE usuario = ? AND version = ?", (usuario, version))


def _identidad(numero, codigo=None):
    with _almacen() as conexion:
        if codigo is not None:
            conexion.execute("BEGIN IMMEDIATE")
        fila = conexion.execute(
            "SELECT usuario, version, codigo, caduca FROM vinculos WHERE telefono = ?",
            (numero,),
        ).fetchone()
        if fila is None:
            return None
        usuario, version, pendiente, caduca = fila
        if obtener_version_sesion(usuario) != version:
            return None
        if codigo is not None:
            if pendiente is None or caduca <= time.time():
                return None
            if not secrets.compare_digest(pendiente, _huella(codigo)):
                return None
            conexion.execute(
                "UPDATE vinculos SET codigo = NULL, caduca = NULL WHERE usuario = ?",
                (usuario,),
            )
        elif pendiente is not None:
            return None
        return usuario, version


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def _lineas_reporte(empresa, reporte):
    lineas = [
        empresa[:150],
        f"Reporte {reporte['id']} · {reporte['perfil'].capitalize()}",
        f"Fecha de generación: {reporte['fecha_generacion']}",
        f"Archivo: {str(reporte['archivo'])[:150]}",
        f"Registros: {reporte['registros_totales']}",
        f"Válidos: {reporte['registros_validos']} · Inválidos: {reporte['registros_invalidos']}",
    ]

    def agregar(indicadores, prefijo=""):
        for clave, valor in indicadores.items():
            nombre = clave.replace("_", " ").capitalize()[:80]
            if isinstance(valor, (str, int, float)) and not isinstance(valor, bool):
                resultado = f"{valor:,.2f}" if isinstance(valor, float) else str(valor)[:150]
                lineas.append(f"{prefijo}{nombre}: {resultado}")

    indicadores = reporte["indicadores"]
    if isinstance(indicadores, dict):
        perfiles = indicadores.get("perfiles")
        if isinstance(perfiles, dict):
            for perfil, valores in perfiles.items():
                if isinstance(valores, dict):
                    agregar(valores, f"{perfil.capitalize()[:50]} · ")
        agregar(indicadores)
    return lineas


def _pdf(lineas):
    buffer = io.BytesIO()
    estilos = getSampleStyleSheet()
    historia = [Paragraph("ReportesPro | Resumen histórico", estilos["Title"])]
    historia.extend(Paragraph(escape(linea), estilos["BodyText"]) for linea in lineas)
    SimpleDocTemplate(buffer).build(historia)
    return buffer.getvalue()


def responder(numero, texto):
    """Devuelve el mensaje y, cuando corresponde, el PDF que lo acompaña."""
    numero = _telefono(numero)
    comando = _normalizar(texto)
    if comando in {"enviame el pdf", "enviar pdf", "dame el pdf"}:
        comando = "pdf"
    elif comando in {"dame mi ultimo reporte", "muestrame el ultimo reporte"}:
        comando = "ultimo reporte"
    vincular = re.fullmatch(r"vincular ([0-9a-f]{32})", comando)
    if vincular:
        if _identidad(numero, vincular[1]):
            return "Número vinculado. Escribe Último reporte para empezar.", None
        return "Código inválido o vencido. Genera uno nuevo en Mi cuenta.", None

    identidad = _identidad(numero)
    if identidad is None:
        return "Vincula tu número desde Mi cuenta en ReportesPro y envía el código aquí.", None
    usuario, version = identidad
    solicitud = re.fullmatch(
        r"(?:(ultimo reporte|pdf)(?: ([0-9]{1,18}))?|pdf ([0-9]{1,18}) ([0-9]{1,18}))",
        comando,
    )
    if solicitud is None:
        return "Escribe Último reporte para consultar tus empresas y reportes.", None

    accion, empresa_id, empresa_pdf, reporte_id = solicitud.groups()
    empresas = db.listar_empresas_usuario(usuario)
    if not empresas:
        return "Tu cuenta no tiene empresas disponibles.", None
    if empresa_id is None and empresa_pdf is None and len(empresas) > 1:
        orden = "PDF" if accion == "pdf" else "Último reporte"
        lista = "\n".join(f"{e['id']} · {e['nombre'][:70]}" for e in empresas[:18])
        if len(empresas) > 18:
            lista += "\nPuedes consultar los demás IDs en ReportesPro."
        return f"Elige una empresa enviando {orden} seguido de su ID.\n\n{lista}", None
    elegido = int(empresa_id or empresa_pdf or empresas[0]["id"])
    empresa = next((e for e in empresas if e["id"] == elegido), None)
    if empresa is None:
        return "La empresa no está disponible para tu cuenta.", None
    try:
        reportes = db.listar_reportes_usuario(
            usuario, elegido, version, limite=1, reporte_id=int(reporte_id) if reporte_id else None
        )
    except PermissionError:
        return "La empresa no está disponible para tu cuenta.", None
    if not reportes:
        return "No hay un reporte guardado para esa solicitud.", None
    reporte = reportes[0]
    lineas = _lineas_reporte(empresa["nombre"], reporte)
    if accion == "pdf" or empresa_pdf:
        return "Resumen histórico de ReportesPro", _pdf(lineas)
    resumen = "\n".join(lineas)[:1750]
    return f"{resumen}\n\nPara recibir este documento, escribe PDF {elegido} {reporte['id']}.", None
