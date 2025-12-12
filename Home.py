import streamlit as st
import folium
from streamlit_folium import st_folium
import random
import time

# Configurar la página
st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")


# Inicializar el estado de la sesión para los puntos si no existe
if 'points' not in st.session_state:
    st.session_state.points = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

# Función para generar puntos aleatorios
def generate_points():
    # Puntos base (ciudades principales)
    base_points = [
        [-34.6037, -58.3816, "Buenos Aires"],
        [-31.4201, -64.1811, "Córdoba"],
        [-32.8908, -68.8272, "Mendoza"],
        [-26.8083, -65.2226, "Tucumán"],
        [-31.6187, -60.6917, "Santa Fe"]
    ]
    
    # Regiones de Argentina (lat_min, lat_max, lon_min, lon_max)
    regions = [
        (-35.5, -30.0, -61.0, -57.0),  # Buenos Aires y Santa Fe
        (-33.0, -29.0, -69.0, -63.0),  # Córdoba y San Luis
        (-42.0, -36.0, -68.0, -62.0),  # La Pampa y Río Negro
        (-28.0, -22.0, -67.0, -63.0),  # Salta y Jujuy
        (-30.0, -25.0, -61.0, -58.0),  # Chaco y Formosa
        (-32.0, -28.0, -59.0, -56.0),  # Entre Ríos y Corrientes
        (-46.0, -42.0, -71.0, -65.0)   # Chubut
    ]
    
    # Añadir puntos aleatorios
    random_points = []
    for i in range(5):
        region = random.choice(regions)
        lat = random.uniform(region[0], region[1])
        lon = random.uniform(region[2], region[3])
        random_points.append([lat, lon, f"Punto {i+1}"])
    
    return base_points + random_points

# Crear el mapa base centrado en Argentina con vista satelital
m = folium.Map(
    location=[-38.416097, -63.616672],
    zoom_start=4,
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri'
)

# Añadir capa de fronteras y divisiones políticas
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Divisiones Políticas',
    overlay=True
).add_to(m)

# Verificar si es tiempo de actualizar (cada 5 segundos)
current_time = time.time()
if current_time - st.session_state.last_update >= 5:
    st.session_state.points = generate_points()
    st.session_state.last_update = current_time

# Añadir marcadores para cada punto
for lat, lon, name in st.session_state.points:
    folium.Marker(
        location=[lat, lon],
        popup=name,
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

# Añadir control de capas
folium.LayerControl().add_to(m)

# Centrar el título y el mapa usando columnas
col1, col2, col3 = st.columns([1, 4, 1])
with col2:
    # Título centrado
    st.markdown('<left><h2 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;">  🗺️ Sistema de Vigilancia de la Salud</h2></left>', unsafe_allow_html=True)
    
    # Mapa
    st_folium(
        m,
        width=800,
        height=600,
        key=f"map_{st.session_state.last_update}"
    )

# Pequeña pausa y rerun para actualización
time.sleep(0.1)
st.rerun()

# Sidebar para navegación a pages (multipage)
st.sidebar.title("Páginas")
# Las pages se cargan automáticamente