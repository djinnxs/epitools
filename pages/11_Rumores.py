import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.exceptions import RequestException
import time
import random

st.set_page_config(page_title="Epirumores", page_icon=":newspaper:", layout="wide")

max_retries = 3
timeout = 10
backoff_factor = 0.3

def scrape_diario(url, keywords, session, max_retries=3, backoff_factor=0.3):
    last_error = None
    for i in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            break
        except RequestException as e:
            last_error = str(e)
            if i == max_retries - 1:
                return pd.DataFrame([]), last_error
            time.sleep(backoff_factor * (2 ** i))

    soup = BeautifulSoup(response.content, 'html.parser')

    noticias = []
    for noticia in soup.find_all('article'):
        titulo = noticia.find('h2')
        if titulo:
            titulo = titulo.text.strip()
        else:
            titulo = ''

        enlace = noticia.find('a')
        if enlace:
            enlace = enlace.get('href', '')
        else:
            enlace = ''

        enlace_absoluto = urljoin(url, enlace)

        if any(keyword.lower() in titulo.lower() for keyword in keywords):
            noticias.append({'titulo': titulo, 'enlace': enlace_absoluto})

    return pd.DataFrame(noticias), None

keywords = ['epidemia', 'enfermedad', 'virus', 'vacuna', 'Rabia', 'Lepidópteros', 'Lonomía', 'Alacranismo', 'Amebiasis', 'Araneísmo', 'Latrodectismo', 'Loxoscelismo', 'Foneutrismo', 'Aspergilosis', 'Bartonelosis', 'Botulismo', 'Bronquiolitis', 'Brucelosis', 'Candidemias', 'Candidiasis', 'Carbunco', 'Miositis', 'Celiaquía', 'Chagas', 'Cisticercosis', 'Citomegalovirus', 'Clamidiasis', 'Coccidioidomicosis', 'Cólera', 'Coqueluche', 'Coriomeningitis', 'COVID-19', 'Influenza', 'Cromoblastomicosis', 'Biotinidasa', 'Dengue', 'Dermatofitosis', 'Diabetes', 'Diarrea', 'Difteria', 'Encefalitis de San Luis', 'Encefalitis equina del Oeste', 'Encefalopatía espongiforme', 'Enfermedad Febril Exantemática-EFE (Sarampión/Rubéola)', 'Sarampión', 'Rubéola', 'Virus del Zika', 'Esporotricosis', 'Fenilcetonuria', 'Feohifomicosis', 'Fibrosis Quística', 'Fiebre Amarilla', 'Chikungunya', 'Oropouche', 'Fiebre del Nilo Occidental', 'Fiebre Hemorrágica Argentina', 'Fiebre Q', 'Borreliosis', 'Fiebre tifoidea', 'Filariosis', 'Galactosemia', 'Gonorrea', 'Hantavirosis', 'paratifoidea', 'Hepatitis', 'Hialohifomicosis', 'Hidatidosis', 'Hidroarsenicismo', 'Hiperplasia Suprarrenal Congénita', 'Hipotiroidismo congénito', 'Histoplasmosis', 'HTLV', 'Infección respiratoria aguda bacteriana', 'Infecciones genitales', 'Infecciones por Candida auris', 'Cryptococcus', 'hongos miceliales', 'Influenza Aviar', 'Intoxicación medicamentosa', 'Intoxicación por Moluscos', 'Intoxicación por ARSÉNICO', 'Intoxicación por Cromo', 'Intoxicación por hidrocarburos', 'Intoxicación por Mercurio', 'Intoxicación por plaguicidas', 'Intoxicación por Plomo', 'Intoxicación por Monóxido de Carbono', 'Legionelosis', 'Leishmaniasis', 'Lepra', 'Leptospirosis', 'Linfogranuloma Venéreo', 'Listeriosis', 'Meningoencefalitis', 'Metahemoglobinemia del lactante', 'Micetomas actinomicóticos', 'Mucormicosis', 'Neumonía', 'Ofidismo', 'infecciones bacterianas', 'Paludismo', 'Pandrogo resistencia', 'Paracoccidioidomicosis', 'Parotiditis', 'Poliomielitis', 'Psitacosis', 'Rickettsiosis', 'Sífilis', 'brote de ETA', 'virus emergente', 'Streptococcus agalactiae', 'Sindrome Urémico Hemolítico', 'Tétanos', 'Toxocariasis', 'Toxoplasmosis', 'Triquinelosis', 'Tuberculosis', 'Triquinosis', 'VIH', 'Viruela', 'Antrax']

diarios = [
    {'nombre': 'TN', 'url': 'https://tn.com.ar/'},
    {'nombre': 'Clarín', 'url': 'https://www.clarin.com/'},
    {'nombre': 'La Nación', 'url': 'https://www.lanacion.com.ar/'},
    {'nombre': 'Página/12', 'url': 'https://www.pagina12.com.ar/'},
    {'nombre': 'El Ancasti', 'url': 'https://www.elancasti.com/'},
    {'nombre': 'Norte', 'url': 'https://www.diarioelnorte.com/'},
    {'nombre': 'El Diario', 'url': 'https://www.diarioelnorte.com/'},
    {'nombre': 'El Chubut', 'url': 'https://www.elchubut.com.ar/'},
    {'nombre': 'La Voz del Interior', 'url': 'https://www.lavoz.com.ar/'},
    {'nombre': 'Día a Día', 'url': 'https://www.diaadia.com.ar/'},
    {'nombre': 'El Litoral', 'url': 'https://www.ellitoral.com/'},
    {'nombre': 'Uno', 'url': 'https://www.unoentrerios.com.ar/'},
    {'nombre': 'La Mañana', 'url': 'https://www.lamanana.com.ar/'},
    {'nombre': 'El Comercial', 'url': 'https://www.elcomercial.com.ar/'},
    {'nombre': 'El Tribuno', 'url': 'https://www.eltribuno.com/'},
    {'nombre': 'Jujuy al Día', 'url': 'https://www.jujuyaldia.com.ar/'},
    {'nombre': 'La Arena', 'url': 'https://www.laarena.com.ar/'},
    {'nombre': 'El Diario', 'url': 'https://www.eldiariodelapampa.com.ar/'},
    {'nombre': 'El Independiente', 'url': 'https://www.elindependiente.com.ar/'},
    {'nombre': 'Los Andes', 'url': 'https://www.losandes.com.ar/'},
    {'nombre': 'El Sol', 'url': 'https://www.elsol.com.ar/'},
    {'nombre': 'El Territorio', 'url': 'https://www.elterritorio.com.ar/'},
    {'nombre': 'Primera Edición', 'url': 'https://www.primeraedicion.com.ar/'},
    {'nombre': 'La Mañana de Neuquén', 'url': 'https://www.lmneuquen.com/'},
    {'nombre': 'Diario Neuquén', 'url': 'https://www.diarioneuquen.com.ar/'},
    {'nombre': 'Río Negro', 'url': 'https://www.rionegro.com.ar/'},
    {'nombre': 'La Angostura Digital', 'url': 'https://www.laangosturadigital.com.ar/'},
    {'nombre': 'El Zonda', 'url': 'https://www.diarioelzondasj.com.ar/'},
    {'nombre': 'Diario de Cuyo', 'url': 'https://www.diariodecuyo.com.ar/'},
    {'nombre': 'El Diario de la República', 'url': 'https://www.eldiariodelarepublica.com/'},
    {'nombre': 'La Gaceta', 'url': 'https://lagacetadigital.com.ar/'},
    {'nombre': 'El Patagónico', 'url': 'https://www.elpatagonico.com/'},
    {'nombre': 'La Opinión Austral', 'url': 'https://laopinionaustral.com.ar/ultimas-noticias.html'},
    {'nombre': 'La Capital', 'url': 'https://www.lacapital.com.ar/'},
    {'nombre': 'El Litoral', 'url': 'https://www.ellitoral.com/'},
    {'nombre': 'El Liberal', 'url': 'https://www.elliberal.com.ar/'},
    {'nombre': 'Nuevo Diario', 'url': 'https://www.nuevodiarioweb.com.ar/'},
    {'nombre': 'Diario de Cuyo', 'url': 'https://www.diariodecuyo.com.ar/'},
    {'nombre': 'La Gaceta', 'url': 'https://www.lagaceta.com.ar/'},
    {'nombre': 'Los primeros', 'url': 'https://www.losprimeros.tv/'},
]

def main():
    st.title("📰 Noticias de Salud en Argentina")

    session = requests.Session()
    # Agregar headers para simular un navegador real y evitar bloqueos 403
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })

    noticias_totales = []
    sitios_exitosos = 0
    sitios_fallidos = 0
    errores_detallados = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    detalles = []

    for i, diario in enumerate(diarios):
        status_text.text(f"Procesando {diario['nombre']}...")
        noticias, error = scrape_diario(diario['url'], keywords, session)
        if not noticias.empty:
            noticias['diario'] = diario['nombre']
            noticias_totales.append(noticias)
            sitios_exitosos += 1
            detalles.append(f"✅ Encontradas {len(noticias)} noticias en {diario['nombre']}")
        else:
            sitios_fallidos += 1
            if error:
                error_msg = f"❌ {diario['nombre']}: {error}"
                detalles.append(error_msg)
                errores_detallados.append(error_msg)
            else:
                msg = f"⚠️ {diario['nombre']}: No se encontraron noticias con las palabras clave"
                detalles.append(msg)
        time.sleep(random.uniform(1, 3))
        progress_bar.progress((i + 1) / len(diarios))

    status_text.text("Procesamiento completado.")

    if noticias_totales:
        noticias_df = pd.concat(noticias_totales, ignore_index=True)
        st.dataframe(noticias_df, height=400)
        st.success(f"Se encontraron {len(noticias_df)} noticias relacionadas con la salud.")
    else:
        st.info("No se encontraron noticias que coincidan con las palabras clave.")

    st.info(f"Sitios procesados exitosamente: {sitios_exitosos}")
    
    if sitios_fallidos > 0:
        st.warning(f"Sitios con errores: {sitios_fallidos}")
        with st.expander("🔍 Ver detalles de errores"):
            if errores_detallados:
                for error in errores_detallados:
                    st.text(error)
            else:
                st.text("No se encontraron noticias en estos sitios (sin errores de conexión)")

    with st.expander("📋 Ver todos los detalles por sitio"):
        for detalle in detalles:
            st.text(detalle)

if __name__ == "__main__":
    main()