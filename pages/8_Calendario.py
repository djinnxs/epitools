import datetime
import calendar
import streamlit as st
from weasyprint import HTML
from io import BytesIO

calendar.setfirstweekday(calendar.SUNDAY)

# Configuración
st.set_page_config(page_title="Calendario", page_icon=":date:", layout="wide")

# Título
st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'> &#x1F4C5; Calendario de Semanas Epidemiológicas</h1>", unsafe_allow_html=True)

# Semana actual
hoy = datetime.date.today()
semana_actual = hoy.isocalendar()[1]
st.markdown(f"<h3 style='text-align: center;'>Semana actual: <span style='color: red; font-weight:bold;'>{semana_actual}</span> del {hoy.year}</h3>", unsafe_allow_html=True)

def get_epi_week(fecha):
    if fecha.weekday() == 6:  # Domingo
        next_day = fecha + datetime.timedelta(days=1)
        return next_day.isocalendar()[1]
    else:
        return fecha.isocalendar()[1]

# Función principal del calendario
def generar_calendario_mes(anio, mes):
    nbsp = "\xa0"
    meses_es = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
   
    cal = calendar.monthcalendar(anio, mes)
    lineas = []
    lineas.append(f"{meses_es[mes].upper()}:")
    lineas.append("    D  L  M  M  J  V  S  ".replace(" ", nbsp))
   
    for fila in cal:
        num_semana = " "
        for dia in fila:
            if dia != 0:
                fecha = datetime.date(anio, mes, dia)
                num_semana = f"{get_epi_week(fecha):2d}"
                break
       
        dias_str = ""
        for dia in fila:
            if dia == 0:
                dias_str += nbsp * 3
            else:
                dias_str += f"{dia:2d}{nbsp}"
       
        lineas.append(f"{num_semana}{nbsp}{dias_str.rstrip()}")
   
    # Añadir líneas vacías para que todos los meses tengan la misma altura (header + 6 semanas)
    while len(lineas) < 8:
        lineas.append(f"{nbsp*2} {nbsp*21}")
   
    return "\n".join(lineas)

# Selector de año a la IZQUIERDA + hasta 2050 + año actual por defecto
col_izq, col_der = st.columns([1, 5])
with col_izq:
    anios = list(range(2020, 2051))  # hasta 2050
    anio = st.selectbox("Año", anios, index=anios.index(hoy.year) if hoy.year in anios else 5)

# Generar meses
meses = [generar_calendario_mes(anio, m) for m in range(1, 13)]

# Mostrar en 3 columnas → QUEDA EXACTAMENTE IGUAL QUE ANTES
col1, col2, col3 = st.columns(3)
for i, texto in enumerate(meses):
    with [col1, col2, col3][i % 3]:
        st.code(texto, language=None)

# ====================== PDF OFICIAL: 3 MESES POR FILA, 1 HOJA A4 ======================
st.markdown("---")
st.subheader("Descargar PDF para imprimir")

if st.button("Generar PDF", type="primary"):
    filas = [(0,1,2), (3,4,5), (6,7,8), (9,10,11)]
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 1.2cm; }}
            body {{ font-family: 'Courier New', monospace; font-size: 11pt; line-height: 1.4; background: white; }}
            h1 {{ text-align: center; color: #003366; font-size: 18pt; margin-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td {{ width: 33.3%; vertical-align: top; padding: 8px 5px; }}
            .mes {{ border: 1px solid #999; border-radius: 8px; padding: 5px; background: #f9f9f9; }}
            .titulo {{ font-weight: bold; color: #003366; margin-bottom: 6px; }}
            pre {{ margin: 0; white-space: pre; font-size: 10pt; }}
        </style>
    </head>
    <body>
        <h1>Calendario de Semanas Epidemiológicas {anio}</h1>
        <table>
    """
    
    for a, b, c in filas:
        html += "<tr>"
        for idx in (a, b, c):
            mes_texto = meses[idx]
            titulo = mes_texto.split("\n")[0]
            contenido = "\n".join(mes_texto.split("\n")[1:]).replace("\n", "<br>")
            html += f'<td><div class="mes"><div class="titulo">{titulo}</div><pre>{contenido}</pre></div></td>'
        html += "</tr>"
    
    html += """
        </table>
    </body>
    </html>
    """

    buffer = BytesIO()
    HTML(string=html).write_pdf(buffer, presentational_hints=True)
    
    st.download_button(
        label="Descargar PDF",
        data=buffer.getvalue(),
        file_name=f"Calendario_Semanas_Epidemiologicas_{anio}.pdf",
        mime="application/pdf"
    )
    st.success("Listo! PDF generado con éxito")