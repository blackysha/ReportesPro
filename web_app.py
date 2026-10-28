"""Interfaz simplificada de ReportesPro 2.0."""
import streamlit as st
import pandas as pd
from main import analyze,make_excel,make_pdf,LABELS
from database.db import crear_tablas,registrar_empresa,listar_empresas,guardar_reporte,listar_reportes

st.set_page_config(page_title='ReportesPro',page_icon='📊',layout='wide')
st.title('📊 ReportesPro')
st.caption('Unifica hojas de Excel, analiza tus datos y descarga dos informes independientes.')
crear_tablas()

st.header('1. Selecciona tu empresa')
with st.expander('➕ Registrar una nueva empresa'):
    with st.form('empresa_form'):
        nombre=st.text_input('Nombre de la empresa')
        correo=st.text_input('Correo (opcional)')
        if st.form_submit_button('Registrar empresa'):
            if not nombre.strip():st.error('Escribe el nombre de la empresa.')
            else:
                try:
                    registrar_empresa(nombre,correo)
                    st.success('Empresa registrada. Selecciónala abajo.')
                    st.rerun()
                except Exception as exc:st.error(f'No se pudo registrar: {exc}')
empresas=listar_empresas()
if not empresas:
    st.info('Registra una empresa para comenzar.')
    st.stop()
options={f"{e['nombre']} (#{e['id']})":e for e in empresas}
chosen=st.selectbox('Empresa',list(options))
empresa=options[chosen]

st.header('2. Sube el archivo')
file=st.file_uploader('Selecciona un CSV o un libro Excel con una o varias hojas',type=['csv','xlsx','xls'])
if file:
    st.info('Se detectarán automáticamente las hojas de ventas, inventario, clientes y datos generales. Las hojas incompatibles no se mezclarán.')
    key=f"{empresa['id']}:{file.name}:{len(file.getvalue())}:{hash(file.getvalue())}"
    if st.button('🔎 Analizar y preparar los dos archivos',type='primary'):
        try:
            with st.spinner('Leyendo hojas, validando y generando archivos...'):
                result=analyze(file.name,file.getvalue())
                excel=make_excel(result)
                pdf=make_pdf(result,empresa['nombre'])
                totals={'registros_totales':sum(m['registros_totales'] for m in result['indicators'].values()),
                        'registros_validos':sum(m['registros_validos'] for m in result['indicators'].values()),
                        'registros_con_incidencias':sum(m['registros_con_incidencias'] for m in result['indicators'].values()),
                        'hojas_procesadas':len(result['manifest'])}
                # El análisis y los archivos son utilizables aunque falle el historial.
                st.session_state['rp2']={'key':key,'result':result,'excel':excel,'pdf':pdf,'totals':totals,'saved':False}
        except Exception as exc:
            st.error(f'No se pudo completar el análisis: {exc}')
            st.exception(exc)
    current=st.session_state.get('rp2')
    if current and current['key']==key:
        result=current['result']; totals=current['totals']
        st.success('¡Análisis completado! Los dos archivos están listos para descargar.')
        st.header('3. Revisa el resultado')
        a,b,c=st.columns(3)
        a.metric('Hojas detectadas',len(result['manifest']))
        b.metric('Registros válidos',totals['registros_validos'])
        c.metric('Registros con incidencias',totals['registros_con_incidencias'])
        st.dataframe(result['manifest'],hide_index=True,use_container_width=True)
        for profile,df in result['valid'].items():
            with st.expander(f"{LABELS[profile]} · {len(df)} registros válidos"):
                st.dataframe(df.head(100),hide_index=True,use_container_width=True)
                st.write('Indicadores:',result['indicators'][profile])
                if profile in result['breakdowns']:
                    st.bar_chart(result['breakdowns'][profile].set_index('Periodo')['Ingresos'])
        if result['unrecognized']:
            st.warning('Hojas conservadas sin analizar: '+', '.join(result['unrecognized']))
        if not result['issues'].empty:
            with st.expander('Ver incidencias'):
                st.dataframe(result['issues'],hide_index=True,use_container_width=True)
        st.header('4. Descarga tus resultados por separado')
        col1,col2=st.columns(2)
        safe=''.join(c if c.isalnum() else '_' for c in empresa['nombre']).strip('_') or 'empresa'
        with col1:
            st.download_button('📗 Descargar Excel unificado',data=current['excel'],
                file_name=f'{safe}_consolidado.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True)
        with col2:
            st.download_button('📄 Descargar informe PDF',data=current['pdf'],
                file_name=f'{safe}_informe.pdf',mime='application/pdf',use_container_width=True)
        if not current['saved']:
            try:
                guardar_reporte(empresa['id'],file.name,totals,perfil='consolidado')
                current['saved']=True
            except Exception as exc:
                st.warning(f'Los archivos se generaron, pero no se pudo guardar el historial: {exc}')

st.divider()
st.header('Historial de análisis')
try:
    history=listar_reportes(empresa['id'])
    if history:
        st.dataframe(pd.DataFrame(history)[['id','archivo','perfil','registros_totales','registros_validos','fecha_generacion']],hide_index=True,use_container_width=True)
        st.caption('El historial guarda los indicadores, no los archivos descargables. Descárgalos al finalizar cada análisis.')
    else:st.info('Todavía no hay análisis registrados.')
except Exception as exc:st.warning(f'No se pudo consultar el historial: {exc}')
st.caption('Demostración sin autenticación. No cargues información real ni confidencial en la versión pública. SQLite en Streamlit Cloud no garantiza persistencia.')