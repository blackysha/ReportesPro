"""Motor de consolidación y análisis de ReportesPro 3.0."""
from __future__ import annotations
import io
import math
import zipfile
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
from hashlib import sha256
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, KeepTogether

PROFILES = {
    'ventas': ('fecha','producto','cantidad','precio'),
    'inventario': ('producto','stock','costo'),
    'clientes': ('nombre','correo','fecha_registro'),
    'general': ('nombre','correo','edad','monto'),
}
LABELS = {'ventas':'Ventas','inventario':'Inventario','clientes':'Clientes','general':'General'}
SALES_CURRENCIES = ('DOP', 'USD', 'EUR')
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_SHEETS = 25
MAX_ROWS = 100_000
MAX_TOTAL_ROWS = 200_000
MAX_CELLS = 2_000_000
MAX_COLUMNS = 256
ALIASES = {'articulo':'producto','articulo_servicio':'producto','servicio':'producto','unidades':'cantidad',
           'precio_unitario':'precio','precio_unit':'precio','existencias':'stock','existencia':'stock',
           'fecha_venta':'fecha','email':'correo','e_mail':'correo','fecha_alta':'fecha_registro',
           'cliente':'nombre','importe':'monto'}

def normalize_columns(df):
    result = df.copy()
    names=[]
    for name in result.columns:
        n = unicodedata.normalize('NFKD',str(name).strip().lower())
        n = ''.join(c for c in n if not unicodedata.combining(c))
        n = re.sub(r'[^a-z0-9]+','_',n).strip('_')
        names.append(ALIASES.get(n,n))
    if len(set(names)) != len(names):
        raise ValueError('Hay columnas con nombres duplicados después de normalizarlas. Revisa los encabezados.')
    result.columns=names
    return result

def read_sheets(filename: str, data: bytes) -> dict[str,pd.DataFrame]:
    if not isinstance(data, bytes) or not data:
        raise ValueError('El archivo está vacío.')
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('El archivo supera el límite de 10 MB.')
    suffix = filename.lower().rsplit('.',1)[-1]
    if suffix == 'csv':
        last=None
        for encoding in ('utf-8-sig','cp1252','latin1'):
            try:
                sample = pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine='python', nrows=0)
                if len(sample.columns) > MAX_COLUMNS:
                    raise ValueError('Se admiten como máximo 256 columnas.')
                max_rows = min(MAX_ROWS, MAX_CELLS // max(1, len(sample.columns)))
                df=pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine='python', nrows=max_rows + 1)
                _check_frames({'CSV': df})
                return {'CSV':normalize_columns(df)}
            except UnicodeDecodeError as exc:
                last=exc
        raise ValueError(f'No se pudo leer el CSV: {last}')
    if suffix in ('xlsx','xls'):
        if suffix == 'xlsx':
            with zipfile.ZipFile(io.BytesIO(data)) as book:
                entries = book.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError('El libro Excel descomprimido supera los límites permitidos.')
                if any(e.flag_bits & 1 for e in entries):
                    raise ValueError('No se admiten libros cifrados.')
        elif not data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):
            raise ValueError('El contenido no corresponde a un archivo XLS.')
        with pd.ExcelFile(io.BytesIO(data)) as book:
            if len(book.sheet_names) > MAX_SHEETS:
                raise ValueError('Se admiten como máximo 25 hojas.')
            frames = {}
            for name in book.sheet_names:
                sample = pd.read_excel(book, sheet_name=name, nrows=0)
                if len(sample.columns) > MAX_COLUMNS:
                    raise ValueError('Se admiten como máximo 256 columnas.')
                remaining = MAX_CELLS - sum(df.size for df in frames.values())
                max_rows = min(MAX_ROWS, remaining // max(1, len(sample.columns)))
                frames[name] = pd.read_excel(book, sheet_name=name, nrows=max_rows + 1)
                _check_frames(frames)
        if not frames: raise ValueError('El libro no contiene hojas.')
        return {name:normalize_columns(frame) for name,frame in frames.items()}
    raise ValueError('Formato no admitido. Sube CSV, XLSX o XLS.')


def _check_frames(frames):
    if any(len(df.columns) > MAX_COLUMNS for df in frames.values()):
        raise ValueError('Se admiten como máximo 256 columnas.')
    if any(len(df) > MAX_ROWS for df in frames.values()):
        raise ValueError('Una hoja supera las 100.000 filas.')
    if sum(len(df) for df in frames.values()) > MAX_TOTAL_ROWS:
        raise ValueError('El documento supera las 200.000 filas totales.')
    if sum(df.size for df in frames.values()) > MAX_CELLS:
        raise ValueError('El documento supera los dos millones de celdas.')

def detect_profile(frame):
    columns=set(frame.columns)
    matches=[p for p,required in PROFILES.items() if set(required).issubset(columns)]
    return matches[0] if matches else None

def _validate(frame,profile,sheet,week=None):
    df=frame.copy().reset_index(drop=True)
    if {'hoja_origen', 'fila_origen', 'perfil_analisis'} & set(df.columns):
        raise ValueError('El archivo utiliza nombres de columnas reservados para trazabilidad.')
    df.insert(0,'hoja_origen',sheet)
    df.insert(1,'fila_origen',range(2,len(df)+2))
    problems=[]
    for col in {'ventas':('cantidad','precio'),'inventario':('stock','costo'),'general':('edad','monto')}.get(profile,()):
        df[col]=pd.to_numeric(df[col],errors='coerce')
    for col in {'ventas':('fecha',),'clientes':('fecha_registro',)}.get(profile,()):
        if week is None:
            df[col]=pd.to_datetime(df[col],errors='coerce')
        else:
            dates = df[col].astype('string').str.strip()
            iso_dates = dates.str.extract(r'^(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?$', expand=False)
            iso = pd.to_datetime(iso_dates, format='%Y-%m-%d', errors='coerce')
            local = pd.to_datetime(dates, format='%d/%m/%Y', errors='coerce')
            df[col] = iso.where(iso.notna(), local)
    for i,row in df.iterrows():
        if week is not None and row['moneda'] not in SALES_CURRENCIES:
            problems.append({'hoja':sheet,'fila':i+2,'campo':'moneda','problema':'Usa DOP, USD o EUR'})
        for col in PROFILES[profile]:
            val=row[col]
            if pd.isna(val) or (isinstance(val,str) and not val.strip()):
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'Valor vacío o inválido'})
            elif col in ('cantidad','precio','stock','costo','edad','monto') and not math.isfinite(val):
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'Debe ser un número finito'})
            elif col in ('cantidad',) and val<=0:
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'Debe ser mayor que cero'})
            elif col in ('precio','stock','costo','edad','monto') and val<0:
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'No puede ser negativo'})
            elif col=='correo' and ('@' not in str(val) or '.' not in str(val).split('@')[-1]):
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'Correo inválido'})
            elif week is not None and col == 'fecha' and not week[0] <= val.date() <= week[1]:
                problems.append({'hoja':sheet,'fila':i+2,'campo':col,'problema':'Fecha fuera de la semana del cierre'})
    issues=pd.DataFrame(problems,columns=['hoja','fila','campo','problema'])
    bad=set(issues['fila'].tolist()) if not issues.empty else set()
    valid=df[~df['fila_origen'].isin(bad)].copy()
    invalid=df[df['fila_origen'].isin(bad)].copy()
    return valid,invalid,issues

def analyze(filename,data):
    return _analyze_sheets(filename, read_sheets(filename, data))


def analyze_weekly_sales(files, start, default_currency=None):
    """Consolidar exportaciones de ventas para una semana de lunes a domingo."""
    if start.weekday() != 0:
        raise ValueError('Selecciona el lunes de la semana que quieres cerrar.')
    if default_currency not in (*SALES_CURRENCIES, None):
        raise ValueError('Selecciona DOP, USD o EUR como moneda predeterminada.')
    if not 1 <= len(files) <= 10:
        raise ValueError('Adjunta entre uno y diez archivos.')
    if sum(len(data) for _, data in files) > MAX_FILE_BYTES:
        raise ValueError('Los archivos del cierre juntos superan los 10 MB.')

    end = start + timedelta(days=6)
    sheets = {}
    seen = set()
    for index, (filename, data) in enumerate(files, start=1):
        digest = sha256(data).digest()
        if digest in seen:
            raise ValueError('Hay dos archivos con el mismo contenido. Retira la copia y vuelve a analizar.')
        seen.add(digest)
        try:
            book = read_sheets(filename, data)
        except ValueError as exc:
            raise ValueError(f'{filename}: {exc}') from exc
        for sheet, frame in book.items():
            label = f'{index}. {filename} / {sheet}'
            missing = [column for column in PROFILES['ventas'] if column not in frame.columns]
            if missing:
                raise ValueError(f'{label}: faltan columnas de ventas ({", ".join(missing)}).')
            currency = (frame['moneda'] if 'moneda' in frame
                        else pd.Series(default_currency or '', index=frame.index))
            currency = currency.fillna('').astype(str).str.strip().str.upper()
            frame = frame.assign(moneda=currency)
            sheets[label] = frame
        if len(sheets) > MAX_SHEETS:
            raise ValueError('El cierre admite como máximo 25 hojas entre todos los archivos.')
        _check_frames(sheets)

    result = _analyze_sheets(f'Cierre de ventas {start.isoformat()}', sheets, week=(start, end))
    metrics = result['indicators']['ventas']
    totals = {code: metrics[f'ingresos_{code}'] for code in SALES_CURRENCIES if f'ingresos_{code}' in metrics}
    result['cierre'] = {'inicio': start.isoformat(), 'fin': end.isoformat(), 'archivos': len(files),
                       'ingresos_por_moneda': totals}
    return result


def sales_amount(value):
    with localcontext() as context:
        context.prec = 330
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _analyze_sheets(filename, sheets, week=None):
    groups=defaultdict(list)
    issues_all=[]
    manifest=[]
    unrecognized={}
    for sheet,frame in sheets.items():
        profile=detect_profile(frame)
        manifest.append({'Hoja':sheet,'Tipo':LABELS.get(profile,'No reconocido'),'Filas':len(frame),'Columnas':', '.join(frame.columns)})
        if profile is None:
            unrecognized[sheet]=frame
            continue
        groups[profile].append((sheet,frame))
    if not groups:
        raise ValueError('Ninguna hoja contiene las columnas necesarias para Ventas, Inventario, Clientes o General. Revisa la vista previa.')
    consolidated={}; valid_groups={}; indicators={}; breakdowns={}; invalid_groups={}
    for profile,items in groups.items():
        # Unificar hojas de un mismo perfil antes de detectar duplicados entre hojas.
        all_frames=[]; val_frames=[]; inv_frames=[]
        for sheet,frame in items:
            val,inv,iss=_validate(frame,profile,sheet,week)
            all_frames.append(frame.assign(hoja_origen=sheet,fila_origen=range(2,len(frame)+2)))
            val_frames.append(val); inv_frames.append(inv)
            if not iss.empty: issues_all.append(iss)
        merged=pd.concat(all_frames,ignore_index=True)
        valid=pd.concat(val_frames,ignore_index=True)
        invalid=pd.concat(inv_frames,ignore_index=True)
        # Duplicados solo cuando la fila completa coincide en las columnas requeridas.
        # Ventas idénticas pueden ser transacciones legítimas: no se eliminan automáticamente.
        if profile in ('clientes','inventario'):
            key=['correo'] if profile=='clientes' else ['producto']
            duplicates=valid.duplicated(subset=key,keep='first')
            for _,r in valid[duplicates].iterrows():
                issues_all.append(pd.DataFrame([{'hoja':r['hoja_origen'],'fila':int(r['fila_origen']),
                                                  'campo':key[0],'problema':'Duplicado entre hojas'}]))
            invalid=pd.concat([invalid,valid[duplicates]],ignore_index=True)
            valid=valid[~duplicates].copy()
        consolidated[profile]=merged
        valid_groups[profile]=valid
        invalid_groups[profile]=invalid
        m={'registros_totales':int(len(merged)),'registros_validos':int(len(valid)),
           'registros_con_incidencias':int(len(merged)-len(valid))}
        if profile=='ventas':
            valid=valid.copy(); valid['importe']=valid['cantidad']*valid['precio']; valid_groups[profile]=valid
            m['unidades_vendidas'] = float(valid['cantidad'].sum())
            if week is not None:
                m.update({f'ingresos_{code}': float(rows['importe'].sum()) for code, rows in valid.groupby('moneda')})
                if not valid.empty:
                    daily = valid.assign(Periodo=valid['fecha'].dt.strftime('%Y-%m-%d'))
                    breakdowns[profile] = (daily.groupby(['Periodo', 'moneda'], as_index=False)['importe']
                                           .sum().rename(columns={'moneda': 'Moneda', 'importe': 'Ingresos'}))
            else:
                m['ingresos_totales'] = float(valid['importe'].sum())
            if week is None and not valid.empty:
                monthly=valid.assign(mes=valid['fecha'].dt.strftime('%Y-%m')).groupby('mes')['importe'].sum().reset_index()
                breakdowns[profile]=monthly.rename(columns={'mes':'Periodo','importe':'Ingresos'})
        elif profile=='inventario':
            m.update(valor_inventario=float((valid['stock']*valid['costo']).sum()),productos_agotados=int((valid['stock']==0).sum()))
        elif profile=='clientes':m['clientes_validos']=int(len(valid))
        elif profile=='general':m['monto_total_valido']=float(valid['monto'].sum())
        if any(isinstance(value, float) and not math.isfinite(value) for value in m.values()):
            raise ValueError('Los cálculos exceden el rango numérico permitido.')
        indicators[profile]=m
    all_issues=pd.concat(issues_all,ignore_index=True) if issues_all else pd.DataFrame(columns=['hoja','fila','campo','problema'])
    return {'archivo':filename,'manifest':pd.DataFrame(manifest),'consolidated':consolidated,
            'valid':valid_groups,'invalid':invalid_groups,'issues':all_issues,
            'indicators':indicators,'breakdowns':breakdowns,'unrecognized':unrecognized}

def _excel_safe(df):
    result=df.copy()
    for col in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[col]):
            result[col]=result[col].dt.tz_localize(None) if getattr(result[col].dt,'tz',None) is not None else result[col]
        elif result[col].dtype=='object':
            result[col]=result[col].map(lambda v: v.replace(tzinfo=None) if isinstance(v,datetime) and v.tzinfo else v)
    result = result.map(_safe_cell)
    result.columns = [_safe_cell(c) for c in result.columns]
    return result


def _safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def make_csv(result):
    """CSV UTF-8 para Excel, con neutralización de fórmulas."""
    frames = [df.assign(perfil_analisis=LABELS[profile]) for profile, df in result['valid'].items()]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _excel_safe(frame).to_csv(index=False).encode('utf-8-sig')

def make_excel(result):
    buffer=io.BytesIO()
    with pd.ExcelWriter(buffer,engine='openpyxl',datetime_format='yyyy-mm-dd') as writer:
        _excel_safe(result['manifest']).to_excel(writer,sheet_name='Resumen_hojas',index=False)
        for profile,df in result['valid'].items():
            _excel_safe(df).to_excel(writer,sheet_name=f'{LABELS[profile]}_unificado',index=False)
        for profile,df in result['invalid'].items():
            if not df.empty: _excel_safe(df).to_excel(writer,sheet_name=f'{LABELS[profile]}_excluidos',index=False)
        _excel_safe(result['issues']).to_excel(writer,sheet_name='Incidencias',index=False)
        rows=[{'Tipo':LABELS[p],'Indicador':k.replace('_',' ').capitalize(),'Valor':v} for p,m in result['indicators'].items() for k,v in m.items()]
        pd.DataFrame(rows).to_excel(writer,sheet_name='Indicadores',index=False)
        for profile,df in result['breakdowns'].items():
            period = 'dia' if 'cierre' in result else 'mes'
            df.to_excel(writer,sheet_name=f'{LABELS[profile]}_por_{period}',index=False)
        if 'cierre' in result:
            close = result['cierre']
            details = {key: close[key] for key in ('inicio', 'fin', 'archivos')}
            pd.DataFrame([details]).to_excel(writer, sheet_name='Cierre_semanal', index=False)
            rows = [
                {'Moneda': code, 'Ingresos': total, **close.get('referencias', {}).get(code, {})}
                for code, total in close['ingresos_por_moneda'].items()
            ]
            pd.DataFrame(rows, columns=['Moneda', 'Ingresos', 'total_referencia', 'diferencia', 'conciliado']).to_excel(
                writer, sheet_name='Totales_por_moneda', index=False,
            )
        for name,df in result['unrecognized'].items():
            # Hojas desconocidas se preservan sin mezclarse.
            safe=re.sub(r'[^A-Za-z0-9_]','_',name)[:22]
            target=f'Original_{safe}'[:31]
            suffix=1
            while target in writer.sheets:
                target=f'Original_{safe[:18]}_{suffix}';suffix+=1
            _excel_safe(df).to_excel(writer,sheet_name=target,index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
            for cell in ws[1]:
                from openpyxl.styles import Font,PatternFill
                cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='174A7E')
            from openpyxl.utils import get_column_letter
            for col in ws.columns:
                length=max((len(str(c.value)) for c in list(col)[:150] if c.value is not None),default=12)
                ws.column_dimensions[get_column_letter(col[0].column)].width=min(42,max(13,length+2))
    return buffer.getvalue()

def make_pdf(result,company):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.7*cm,rightMargin=1.7*cm,topMargin=1.6*cm,bottomMargin=1.6*cm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BlueTitleRP',parent=styles['Title'],textColor=colors.HexColor('#174A7E'),alignment=TA_CENTER,spaceAfter=14))
    story=[Paragraph('ReportesPro | Informe empresarial',styles['BlueTitleRP']),
           Paragraph(f'<b>Empresa:</b> {escape(company)}',styles['Normal']),
           Paragraph(f'<b>Archivo:</b> {escape(result["archivo"])}',styles['Normal']),
           Paragraph(f'<b>Fecha:</b> {datetime.now():%d/%m/%Y %H:%M}',styles['Normal']),Spacer(1,0.5*cm),
           Paragraph('Resumen ejecutivo',styles['Heading2'])]
    if 'cierre' in result:
        close = result['cierre']
        story.insert(3, Paragraph(f'<b>Semana:</b> {close["inicio"]} al {close["fin"]}', styles['Normal']))
        for code, reference in close.get('referencias', {}).items():
            story.insert(4, Paragraph(
                f'<b>Referencia {code}:</b> {reference["total_referencia"]} | <b>Diferencia:</b> {reference["diferencia"]}',
                styles['Normal'],
            ))
    total=sum(m['registros_totales'] for m in result['indicators'].values())
    valid=sum(m['registros_validos'] for m in result['indicators'].values())
    story.append(Paragraph(f'Se analizaron {len(result["manifest"])} hojas, con {total} registros en estructuras reconocidas; '
                           f'{valid} registros se consideraron válidos. Las hojas de diferentes tipos no se mezclaron.',styles['Normal']))
    def add_table(rows):
        t=LongTable([[Paragraph(escape(str(v)),styles['Normal']) for v in row] for row in rows],repeatRows=1,hAlign='LEFT',colWidths=[8.3*cm,8.1*cm])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEAF7')),
                               ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#CFD8E3')),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7)]))
        story.append(t)
    story.extend([Spacer(1,0.35*cm),Paragraph('Hojas procesadas',styles['Heading2'])])
    add_table([['Hoja','Tipo y registros']]+[[r['Hoja'],f"{r['Tipo']} · {r['Filas']} filas"] for _,r in result['manifest'].iterrows()])
    for profile,m in result['indicators'].items():
        story.extend([Spacer(1,0.4*cm),Paragraph(f'Análisis de {LABELS[profile].lower()}',styles['Heading2'])])
        add_table([['Indicador','Resultado']]+[[k.replace('_',' ').capitalize(),f'{v:,.2f}' if isinstance(v,float) else v] for k,v in m.items()])
        if profile=='ventas' and profile in result['breakdowns']:
            monthly=result['breakdowns'][profile]
            story.append(Spacer(1,0.2*cm));story.append(Paragraph('Ingresos por período',styles['Heading3']))
            period = 'Día' if 'cierre' in result else 'Mes'
            add_table([[period,'Ingresos']]+[
                [r['Periodo'], f"{r.get('Moneda', '')} {r['Ingresos']:,.2f}".strip()]
                for _,r in monthly.head(24).iterrows()
            ])
            if len(monthly)>24:story.append(Paragraph('Se muestran los primeros 24 períodos.',styles['Italic']))
    story.extend([Spacer(1,0.35*cm),Paragraph('Calidad de los datos',styles['Heading2'])])
    story.append(Paragraph(f'Se detectaron {len(result["issues"])} incidencias. '
                           'Los registros excluidos se encuentran en el Excel consolidado.',styles['Normal']))
    if result['unrecognized']:
        story.append(Paragraph('Hojas no reconocidas: '+escape(', '.join(result['unrecognized']))+'. Se conservaron en el Excel sin incluirlas en los cálculos.',styles['Normal']))
    story.extend([Spacer(1,0.35*cm),Paragraph('Conclusión',styles['Heading2']),
                  Paragraph('Este informe resume los datos válidos disponibles. Los importes se presentan en la unidad monetaria del archivo original; no se realiza conversión de moneda. Verifica las incidencias antes de tomar decisiones.',styles['Normal'])])
    doc.build(story)
    return buf.getvalue()
