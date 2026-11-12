
"""ReportesPro 3.0 - Plataforma de análisis empresarial."""

import io
import zipfile
import hashlib
import logging

from auth.sessions import iniciar_sesion, sesion_expirada, limpiar_sesion
from auth.access_policy import validar_direccion_servidor, modo_acceso
from database.schema import preparar_base_datos

import pandas as pd
import streamlit as st

from main import analyze, make_excel, make_pdf, make_csv, LABELS
from database.recovery import restablecer_password
from database.auditoria import registrar_evento
from services.password_recovery_service import enviar_recuperacion, MENSAJE_PUBLICO

from database.db import (
    registrar_empresa_usuario,
    listar_empresas_usuario,
    guardar_reporte_usuario,
    listar_reportes_usuario,
)

from database.usuarios import (
    obtener_version_sesion,
    registrar_usuario,
    autenticar_usuario,
    desactivar_mi_cuenta,
)

from database.admin import (
    es_administrador,
    listar_usuarios_admin,
    cambiar_estado_usuario,
)

logger = logging.getLogger(__name__)


# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="ReportesPro 3.0",
    page_icon="📊",
    layout="wide",
)

try:
    validar_direccion_servidor(st.get_option("server.address"))
    preparar_base_datos()
except Exception:
    logger.error("No se pudo comprobar el esquema de datos")
    st.error("No se pudo preparar la aplicación. Solicita al administrador revisar la base de datos.")
    st.stop()

if modo_acceso() == "lan":
    st.info("Prueba en red: acceso exclusivo para usuarios. La administración está disponible únicamente en la PC anfitriona.")


# ==================================================
# ESTADO DE SESIÓN
# ==================================================

if "rp_usuario" not in st.session_state:
    st.session_state.rp_usuario = None

if "rp_invitado" not in st.session_state:
    st.session_state.rp_invitado = False

if "rp_resultado" not in st.session_state:
    st.session_state.rp_resultado = None


def limpiar_analisis():
    st.session_state.rp_resultado = None


def cerrar_sesion():
    """Cierra la sesión y registra el evento de auditoría."""

    limpiar_sesion(st.session_state, registrar_evento)
    st.rerun()


def crear_zip(pdf, excel, nombre):
    """Genera un archivo ZIP con el PDF y Excel."""

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archivo:

        archivo.writestr(
            f"{nombre}_informe.pdf",
            pdf,
        )

        archivo.writestr(
            f"{nombre}_consolidado.xlsx",
            excel,
        )

    return buffer.getvalue()


def nombre_seguro(nombre):
    """Convierte un nombre en uno adecuado para archivos."""

    return (
        "".join(
            c if c.isalnum() else "_"
            for c in nombre
        ).strip("_")
        or "reporte"
    )


# ==================================================
# PANTALLA DE ACCESO
# ==================================================

def mostrar_acceso():

    st.title("📊 ReportesPro 3.0")

    st.write(
        "Plataforma de análisis empresarial "
        "y generación automática de informes."
    )

    tab_login, tab_registro, tab_invitado, tab_recuperar = st.tabs(
        [
            "🔐 Iniciar sesión",
            "📝 Crear cuenta",
            "👤 Invitado",
            "🔑 Recuperar contraseña",
        ]
    )

    # ----------------------------------------------
    # INICIAR SESIÓN
    # ----------------------------------------------

    with tab_login:

        st.subheader("Iniciar sesión")

        with st.form("form_login"):

            correo = st.text_input(
                "Correo electrónico"
            )

            password = st.text_input(
                "Contraseña",
                type="password",
            )

            entrar = st.form_submit_button(
                "Iniciar sesión",
                width="stretch",
            )

        # Procesar el formulario solamente
        # cuando se presione Iniciar sesión.
        if entrar:

            try:
                usuario = autenticar_usuario(correo, password)
            except Exception:
                logger.error("No se pudo completar la autenticación")
                st.error("No se pudo iniciar sesión. Inténtalo más tarde.")
            else:
                if usuario is not None:
                    iniciar_sesion(st.session_state, usuario)
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos, o la cuenta no está disponible.")
    # ----------------------------------------------
    # REGISTRAR USUARIO
    # ----------------------------------------------

    with tab_registro:

        st.subheader("Crear cuenta")

        with st.form("form_registro"):

            nombre = st.text_input(
                "Nombre completo"
            )

            correo_nuevo = st.text_input(
                "Correo electrónico",
                key="registro_correo",
            )

            password_nuevo = st.text_input(
                "Contraseña (mínimo 12 caracteres)",
                type="password",
                key="registro_password",
            )

            confirmar = st.text_input(
                "Confirmar contraseña",
                type="password",
            )

            registrar = st.form_submit_button(
                "Crear cuenta",
                width="stretch",
            )

        if registrar:

            if password_nuevo != confirmar:

                st.error(
                    "Las contraseñas no coinciden."
                )

            else:

                try:

                    registrar_usuario(
                        nombre,
                        correo_nuevo,
                        password_nuevo,
                    )

                    st.success(
                        "Cuenta creada correctamente. "
                        "Ahora puedes iniciar sesión."
                    )

                except ValueError as exc:

                    st.error(str(exc))

    # ----------------------------------------------
    # MODO INVITADO
    # ----------------------------------------------

    with tab_invitado:

        st.subheader("Acceso como invitado")

        st.info(
            "Puedes analizar archivos y descargar "
            "informes sin crear una cuenta. "
            "No podrás guardar historial."
        )

        if st.button(
            "Continuar como invitado",
            width="stretch",
        ):

            st.session_state.clear()

            st.session_state.rp_usuario = None
            st.session_state.rp_invitado = True
            st.session_state.rp_resultado = None

            st.rerun()

    # ----------------------------------------------
    # RECUPERACIÓN DE CONTRASEÑA (USUARIOS NORMALES)
    # ----------------------------------------------

    with tab_recuperar:
        st.subheader("Recuperar contraseña")
        st.caption("Solo cuentas normales activas. Los administradores requieren verificación reforzada.")
        with st.form("form_solicitar_recuperacion"):
            correo_recuperacion = st.text_input("Correo registrado", key="correo_recuperacion")
            solicitar = st.form_submit_button("Enviar enlace", width="stretch")

        if solicitar:
            if not correo_recuperacion.strip():
                st.error("Introduce tu correo electrónico.")
            else:
                try:
                    # URL local; sustituir por HTTPS antes de desplegar.
                    enviar_recuperacion(correo_recuperacion)
                except Exception:
                    # No revelar si la dirección corresponde a una cuenta.
                    # Consultar logs privados para diagnosticar errores SMTP.
                    logger.error("No se pudo completar el envío de recuperación")
                st.info(MENSAJE_PUBLICO)


def mostrar_formulario_restauracion(token):
    """Formulario local para consumir un token de recuperación."""
    st.title("🔑 Restablecer contraseña")
    st.caption("El enlace es de un solo uso y caduca a los 15 minutos.")
    with st.form("form_nueva_password"):
        nueva = st.text_input("Nueva contraseña", type="password")
        confirmar = st.text_input("Confirmar contraseña", type="password")
        guardar = st.form_submit_button("Cambiar contraseña", width="stretch")

    if guardar:
        if nueva != confirmar:
            st.error("Las contraseñas no coinciden.")
        else:
            try:
                actualizado = restablecer_password(token, nueva)
            except ValueError:
                st.error("La contraseña no cumple los requisitos de seguridad.")
            except Exception:
                st.error("No se pudo completar el restablecimiento.")
            else:
                if actualizado:
                    st.query_params.clear()
                    st.success("Contraseña actualizada. Vuelve a iniciar sesión.")
                    if st.button("Ir al inicio de sesión"):
                        st.rerun()
                else:
                    st.error("Enlace inválido, caducado o ya utilizado.")


# ==================================================
# PANEL PRINCIPAL
# ==================================================

def mostrar_panel():

    usuario = st.session_state.rp_usuario
    invitado = st.session_state.rp_invitado

    st.title("📊 ReportesPro 3.0")

    # ----------------------------------------------
    # USUARIO INVITADO
    # ----------------------------------------------

    if invitado:

        st.info(
            "Modo invitado: tus análisis son "
            "temporales y no se guardan "
            "en el historial."
        )

        empresa = {
            "id": None,
            "nombre": "Invitado",
        }

        identidad = "invitado"

    # ----------------------------------------------
    # USUARIO REGISTRADO
    # ----------------------------------------------

    else:

        st.success(
            f"Bienvenido, {usuario['nombre']}"
        )

        identidad = f"usuario:{usuario['id']}"

        st.header("1. Selecciona tu empresa")

        with st.expander(
            "➕ Registrar una nueva empresa"
        ):

            with st.form("form_empresa"):

                nombre = st.text_input(
                    "Nombre de la empresa"
                )

                correo = st.text_input(
                    "Correo de la empresa (opcional)"
                )

                registrar = st.form_submit_button(
                    "Registrar empresa"
                )

            if registrar:

                try:

                    registrar_empresa_usuario(
                        usuario["id"],
                        nombre,
                        correo,
                        version_sesion=st.session_state.rp_version_sesion,
                    )

                    limpiar_analisis()

                    st.success(
                        "Empresa registrada correctamente."
                    )

                    st.rerun()

                except Exception as exc:

                    logger.error("No se pudo registrar una empresa (%s)", type(exc).__name__)

                    st.error(
                        "No se pudo registrar la empresa. Revisa los datos o inténtalo más tarde."
                    )

        empresas = listar_empresas_usuario(
            usuario["id"]
        )

        if not empresas:

            st.warning(
                "Registra una empresa para comenzar."
            )

            return

        opciones = {
            f"{e['nombre']} (#{e['id']})": e
            for e in empresas
        }

        seleccion = st.selectbox(
            "Empresa",
            list(opciones),
        )

        empresa = opciones[seleccion]

    # ----------------------------------------------
    # SUBIR DOCUMENTO
    # ----------------------------------------------

    st.header("2. Subir documento")

    archivo = st.file_uploader(
        "Selecciona un archivo CSV o Excel",
        type=["csv", "xlsx", "xls"],
        key="archivo_analisis",
        help="Máximo 10 MB, 25 hojas, 100.000 filas por hoja y 200.000 filas totales.",
    )

    if archivo is not None:

        datos = archivo.getvalue()

        huella = hashlib.sha256(
            datos
        ).hexdigest()

        clave = (
            identidad,
            empresa["id"],
            archivo.name,
            huella,
        )

        if st.button(
            "🔎 Analizar documento",
            type="primary",
        ):

            try:

                with st.spinner(
                    "Analizando documento..."
                ):

                    resultado = analyze(
                        archivo.name,
                        datos,
                    )

                    excel = make_excel(resultado)

                    pdf = make_pdf(
                        resultado,
                        empresa["nombre"],
                    )

                    indicadores = resultado["indicators"]

                    totales = {
                        "registros_totales": sum(
                            m["registros_totales"]
                            for m in indicadores.values()
                        ),
                        "registros_validos": sum(
                            m["registros_validos"]
                            for m in indicadores.values()
                        ),
                        "registros_con_incidencias": sum(
                            m["registros_con_incidencias"]
                            for m in indicadores.values()
                        ),
                        "hojas_procesadas": len(
                            resultado["manifest"]
                        ),
                        "perfiles": indicadores,
                    }

                    st.session_state.rp_resultado = {
                        "clave": clave,
                        "resultado": resultado,
                        "excel": excel,
                        "pdf": pdf,
                        "totales": totales,
                        "guardado": False,
                    }

            except Exception as exc:

                logger.error("No se pudo analizar un documento (%s)", type(exc).__name__)

                limpiar_analisis()

                st.error(
                    f"Error durante el análisis: {exc}"
                )

        actual = st.session_state.rp_resultado

        if actual and actual["clave"] == clave:

            mostrar_resultados(
                actual,
                empresa,
                usuario,
                invitado,
                archivo.name,
            )

    # ----------------------------------------------
    # HISTORIAL PRIVADO
    # ----------------------------------------------

    if not invitado:

        st.divider()

        st.header("📚 Mi historial de análisis")

        try:

            historial = listar_reportes_usuario(
                usuario["id"],
                empresa["id"],
                version_sesion=st.session_state.rp_version_sesion,
            )

            if historial:

                columnas = [
                    "id",
                    "archivo",
                    "perfil",
                    "registros_totales",
                    "registros_validos",
                    "fecha_generacion",
                ]

                tabla = pd.DataFrame(
                    historial
                )[columnas]

                st.dataframe(
                    tabla,
                    hide_index=True,
                    width="stretch",
                )

                st.caption(
                    "El historial almacena indicadores, "
                    "no los archivos PDF o Excel."
                )

            else:

                st.info(
                    "Esta empresa todavía no tiene "
                    "análisis guardados."
                )

        except Exception as exc:

            logger.error("No se pudo consultar un historial (%s)", type(exc).__name__)

            st.error(
                    "No se pudo consultar el historial. Inténtalo más tarde."
            )


# ==================================================
# RESULTADOS Y DESCARGAS
# ==================================================

def mostrar_resultados(
    actual,
    empresa,
    usuario,
    invitado,
    nombre_archivo,
):

    resultado = actual["resultado"]
    totales = actual["totales"]

    st.success("¡Análisis completado!")

    st.header("3. Resultados del análisis")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Hojas detectadas",
        len(resultado["manifest"]),
    )

    col2.metric(
        "Registros válidos",
        totales["registros_validos"],
    )

    col3.metric(
        "Registros con incidencias",
        totales["registros_con_incidencias"],
    )

    st.dataframe(
        resultado["manifest"],
        hide_index=True,
        width="stretch",
    )

    # ----------------------------------------------
    # RESULTADOS POR PERFIL
    # ----------------------------------------------

    for perfil, df in resultado["valid"].items():

        with st.expander(
            f"{LABELS[perfil]} - {len(df)} registros"
        ):

            st.dataframe(
                df.head(100),
                hide_index=True,
                width="stretch",
            )

            st.write(
                "Indicadores:",
                resultado["indicators"][perfil],
            )

            if perfil in resultado["breakdowns"]:

                desglose = resultado[
                    "breakdowns"
                ][perfil]

                if not desglose.empty:

                    st.bar_chart(
                        desglose.set_index(
                            "Periodo"
                        )["Ingresos"]
                    )

    # ----------------------------------------------
    # HOJAS NO RECONOCIDAS
    # ----------------------------------------------

    if resultado["unrecognized"]:

        st.warning(
            "Hojas conservadas sin analizar: "
            + ", ".join(
                resultado["unrecognized"]
            )
        )

    # ----------------------------------------------
    # INCIDENCIAS
    # ----------------------------------------------

    if not resultado["issues"].empty:

        with st.expander(
            "Ver incidencias"
        ):

            st.dataframe(
                resultado["issues"],
                hide_index=True,
                width="stretch",
            )

    # ----------------------------------------------
    # DESCARGAR INFORMES
    # ----------------------------------------------

    st.header("4. Descargar informe")

    formato = st.radio(
        "Selecciona el formato de descarga",
        [
            "PDF",
            "CSV",
            "XLSX",
            "Ambos (ZIP)",
        ],
        horizontal=True,
    )

    seguro = nombre_seguro(
        empresa["nombre"]
    )

    if formato == "PDF":

        st.download_button(
            "📄 Descargar PDF",
            data=actual["pdf"],
            file_name=f"{seguro}_informe.pdf",
            mime="application/pdf",
            width="stretch",
        )

    elif formato == "CSV":
        st.download_button(
            "Descargar CSV", data=make_csv(resultado),
            file_name=f"{seguro}_datos.csv", mime="text/csv",
            width="stretch",
        )

    elif formato == "XLSX":

        st.download_button(
            "📗 Descargar Excel",
            data=actual["excel"],
            file_name=f"{seguro}_consolidado.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            width="stretch",
        )

    else:

        paquete = crear_zip(
            actual["pdf"],
            actual["excel"],
            seguro,
        )

        st.download_button(
            "📦 Descargar PDF y Excel",
            data=paquete,
            file_name=f"{seguro}_informes.zip",
            mime="application/zip",
            width="stretch",
        )

    # ----------------------------------------------
    # GUARDAR HISTORIAL
    # ----------------------------------------------

    if invitado:

        st.info(
            "Como invitado puedes descargar "
            "los informes, pero no guardar "
            "análisis ni modificar historiales."
        )

    elif actual["guardado"]:

        st.success(
            "Este análisis ya fue guardado "
            "en tu historial."
        )

    else:

        if st.button(
            "💾 Guardar análisis en mi historial"
        ):

            try:

                guardar_reporte_usuario(
                    usuario["id"],
                    empresa["id"],
                    nombre_archivo,
                    totales,
                    perfil="consolidado",
                    version_sesion=st.session_state.rp_version_sesion,
                )

                actual["guardado"] = True

                st.success(
                    "Análisis guardado correctamente."
                )

                st.rerun()

            except Exception as exc:

                logger.error("No se pudo guardar un reporte (%s)", type(exc).__name__)

                st.error(
                    "No se pudo guardar el análisis. Inténtalo más tarde."
                )


# ==================================================
# MI CUENTA
# ==================================================

def mostrar_mi_cuenta(usuario):

    st.divider()

    st.subheader("⚙️ Mi cuenta")

    with st.expander(
        "Desactivar mi cuenta"
    ):

        st.warning(
            "Si desactivas tu cuenta, no podrás "
            "iniciar sesión. Tus empresas y reportes "
            "se conservarán. La reactivación requerirá "
            "asistencia de un administrador autorizado."
        )

        with st.form("form_desactivar_cuenta"):

            password = st.text_input(
                "Confirma tu contraseña",
                type="password",
            )

            confirmacion = st.checkbox(
                "Entiendo que perderé el acceso "
                "hasta que se reactive mi cuenta."
            )

            enviar = st.form_submit_button(
                "Desactivar mi cuenta"
            )

        if enviar:

            if not confirmacion:

                st.error(
                    "Debes confirmar que comprendes "
                    "las consecuencias."
                )

            elif not password:

                st.error(
                    "Introduce tu contraseña."
                )

            else:

                try:

                    desactivar_mi_cuenta(
                        usuario["id"],
                        password,
                    )

                    limpiar_sesion(st.session_state, registrar_evento)
                    st.rerun()

                except ValueError as exc:

                    st.error(str(exc))


# ==================================================
# PANEL ADMINISTRATIVO
# ==================================================

def mostrar_panel_administrativo(usuario):
    """
    Panel de administración exclusivo
    para administradores activos.
    """

    if usuario is None:
        return

    if not es_administrador(usuario["id"]):
        return

    st.divider()

    st.header("🛡️ Administración de usuarios")

    st.caption(
        "Gestiona las cuentas registradas "
        "en ReportesPro 3.0."
    )

    # ----------------------------------------------
    # CONSULTAR USUARIOS
    # ----------------------------------------------

    try:

        usuarios = listar_usuarios_admin(
            usuario["id"]
        )

    except PermissionError:

        st.error(
            "No tienes permisos para acceder "
            "a esta sección."
        )

        return

    # ----------------------------------------------
    # ESTADÍSTICAS ADMINISTRATIVAS
    # ----------------------------------------------

    total = len(usuarios)

    activos = sum(
        1 for u in usuarios
        if u["activo"] == 1
    )

    inactivos = total - activos

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Usuarios registrados",
        total,
    )

    col2.metric(
        "Usuarios activos",
        activos,
    )

    col3.metric(
        "Usuarios desactivados",
        inactivos,
    )

    # ----------------------------------------------
    # TABLA DE USUARIOS
    # ----------------------------------------------

    st.subheader("Cuentas registradas")

    datos_tabla = [
        {
            "ID": u["id"],
            "Nombre": u["nombre"],
            "Correo": u["correo"],
            "Estado": (
                "Activo"
                if u["activo"] == 1
                else "Desactivado"
            ),
            "Rol": u["rol"],
            "Fecha de registro": u["fecha_creacion"],
        }
        for u in usuarios
    ]

    st.dataframe(
        datos_tabla,
        width="stretch",
        hide_index=True,
    )

    # ----------------------------------------------
    # GESTIÓN DE ESTADOS
    # ----------------------------------------------

    st.subheader(
        "Cambiar estado de una cuenta"
    )

    usuarios_gestionables = [
        u for u in usuarios
        if u["id"] != usuario["id"]
    ]

    if not usuarios_gestionables:

        st.info(
            "No hay otras cuentas para administrar."
        )

        return

    opciones = {
        u["id"]: u
        for u in usuarios_gestionables
    }

    with st.form(
        "formulario_administracion_usuarios"
    ):

        usuario_objetivo_id = st.selectbox(
            "Selecciona una cuenta",
            options=list(opciones.keys()),
            format_func=lambda uid: (
                f"{opciones[uid]['nombre']} "
                f"({opciones[uid]['correo']}) "
                f"- ID {uid}"
            ),
        )

        objetivo = opciones[
            usuario_objetivo_id
        ]

        estado_actual = (
            "Activa"
            if objetivo["activo"] == 1
            else "Desactivada"
        )

        st.write(
            f"Estado actual: **{estado_actual}**"
        )

        accion = st.radio(
            "Acción administrativa",
            options=[
                "Activar",
                "Desactivar",
            ],
            horizontal=True,
        )

        confirmacion = st.checkbox(
            "Confirmo que deseo cambiar "
            "el estado de esta cuenta."
        )

        enviar = st.form_submit_button(
            "Aplicar cambio"
        )

    # ----------------------------------------------
    # PROCESAR ACCIÓN ADMINISTRATIVA
    # ----------------------------------------------

    if enviar:

        if not confirmacion:

            st.error(
                "Debes confirmar la operación "
                "antes de continuar."
            )

            return

        nuevo_estado = (
            accion == "Activar"
        )

        if (
            bool(objetivo["activo"])
            == nuevo_estado
        ):

            st.info(
                "La cuenta ya tiene el estado "
                "seleccionado."
            )

            return

        try:

            cambiar_estado_usuario(
                admin_id=usuario["id"],
                usuario_id=usuario_objetivo_id,
                activo=nuevo_estado,
            )

        except (PermissionError, ValueError) as error:

            st.error(str(error))
            return

        except Exception:

            st.error(
                "No se pudo actualizar la cuenta. "
                "Revisa los registros del servidor."
            )

            return

        st.success(
            "Cuenta actualizada correctamente. "
            f"Nuevo estado: "
            f"{'Activa' if nuevo_estado else 'Desactivada'}."
        )

        st.rerun()


# ==================================================
# NAVEGACIÓN PRINCIPAL
# ==================================================

usuario = st.session_state.rp_usuario
invitado = st.session_state.rp_invitado

token_recuperacion = st.query_params.get("recovery_token")

if token_recuperacion:
    # No mostrar paneles autenticados mientras se procesa el enlace.
    mostrar_formulario_restauracion(token_recuperacion)

elif usuario is None and not invitado:

    mostrar_acceso()

else:

    if usuario is not None:
        try:
            version_actual = obtener_version_sesion(usuario["id"])
            invalida = (
                version_actual is None
                or st.session_state.get("rp_version_sesion") != version_actual
                or sesion_expirada(st.session_state)
            )
        except Exception:
            logger.error("No se pudo validar una sesión")
            invalida = True
        if invalida:
            limpiar_sesion(st.session_state, registrar_evento, "SESION_INVALIDADA")
            st.rerun()

    with st.sidebar:

        st.title("ReportesPro")

        if invitado:

            st.write("👤 Invitado")

        else:

            st.write(
                f"👤 {usuario['nombre']}"
            )

            st.caption(
                usuario["correo"]
            )

            if es_administrador(usuario["id"]):

                st.success(
                    "🛡️ Administrador"
                )

        if st.button(
            "🚪 Cerrar sesión",
            width="stretch",
        ):

            cerrar_sesion()

    # ----------------------------------------------
    # PANEL PRINCIPAL
    # ----------------------------------------------

    mostrar_panel()

    # ----------------------------------------------
    # OPCIONES PARA USUARIOS REGISTRADOS
    # ----------------------------------------------

    if usuario is not None:

        if es_administrador(
            usuario["id"]
        ):

            mostrar_panel_administrativo(
                usuario
            )

        mostrar_mi_cuenta(
            usuario
        )
