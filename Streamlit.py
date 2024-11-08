##--------------------------------------------------------------------------------------------------------------------##
## Install
##--------------------------------------------------------------------------------------------------------------------##

# Instalar bibliotecas necesarias
# %pip install folium geopandas shapely streamlit-folium pandas streamlit

##--------------------------------------------------------------------------------------------------------------------##
## Library
##--------------------------------------------------------------------------------------------------------------------##

import os
import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import random
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from shapely import wkt

##--------------------------------------------------------------------------------------------------------------------##
## Codes
##--------------------------------------------------------------------------------------------------------------------##

# Función para convertir el enlace de Google Drive al formato adecuado para miniatura
def convert_drive_link(link):
    file_id = link.split('/d/')[1].split('/view')[0]
    return f"https://drive.google.com/thumbnail?id={file_id}"

# Cargar el archivo CSV de rutas y el archivo de datos de baches
csv_path = './Street_Sweeping_Schedule_20241105.csv'
pothole_data_path = './pothole_data.csv'  # Nueva fuente de datos de baches
sweeping_schedule_df = pd.read_csv(csv_path)
pothole_data = pd.read_csv(pothole_data_path)

# Aplicamos la conversión a la columna 'Link photo' para usar el enlace de miniatura si existe en pothole_data
if 'link_photo' in pothole_data.columns:
    pothole_data['converted_link'] = pothole_data['link_photo'].apply(convert_drive_link)

# Filtrar filas que tengan valores NaN en 'Line' y convertir a geometría
sweeping_schedule_df = sweeping_schedule_df[sweeping_schedule_df['Line'].notna()]
sweeping_schedule_df['geometry'] = sweeping_schedule_df['Line'].apply(lambda x: wkt.loads(x) if isinstance(x, str) else None)

# Crear un GeoDataFrame
gdf = gpd.GeoDataFrame(sweeping_schedule_df, geometry='geometry', crs="EPSG:4326")

# Establecemos una semilla para la selección aleatoria
random.seed(42)

# Seleccionamos 60 puntos aleatorios de las rutas
sample_points = gdf.sample(n=60, random_state=42)

# Crear un mapa centrado en San Francisco
mapa = folium.Map(location=[37.7749, -122.4194], zoom_start=13)

# Añadimos los puntos aleatorios en el mapa con un marcador de color basado en severity_score
for idx, row in sample_points.iterrows():
    # Obtenemos las coordenadas del primer punto de cada línea (LINESTRING)
    if row['geometry'] and row['geometry'].geom_type == 'LineString':
        point = row['geometry'].coords[0]  # Primer punto de la línea

        # Seleccionamos una imagen aleatoria de pothole de los enlaces convertidos (si existe)
        image_row = pothole_data.sample(n=1, random_state=random.randint(0, 1000)).iloc[0]
        image_link = image_row['converted_link'] if 'converted_link' in image_row else None

        # Obtener el severity_score (asegúrate de que existe en los datos)
        severity_score = image_row['severity_score'] if 'severity_score' in image_row else 0

        # Convertir severity_score al rango de 0 a 1 para determinar el color (rojo para alta prioridad, verde para baja)
        color_intensity = int((severity_score / 100) * 255)  # Escala 0-255
        color = f'#{color_intensity:02x}{255 - color_intensity:02x}00'  # Gradiente de verde a rojo

        # Crear el marcador con CircleMarker y el enlace de imagen
        folium.CircleMarker(
            location=[point[1], point[0]],  # Coordenadas (lat, lon)
            radius=7,  # Radio del círculo
            color=color,  # Color del borde
            fill=True,
            fill_color=color,  # Color de relleno basado en severity_score
            fill_opacity=0.7,
            popup=f"<img src='{image_link}' width='150'>" if image_link else "Pothole",  # Imagen desde el link convertido
            tooltip=f"Severity Score: {severity_score}"  # Mostrar el score en el tooltip
        ).add_to(mapa)

# Crear la interfaz en Streamlit
st.title("Mapa de Baches en San Francisco")
st.write("Este mapa muestra los puntos con baches en San Francisco. El color indica la severidad (rojo = alta prioridad, verde = baja prioridad).")

# Mostrar el mapa de Folium en Streamlit
st_folium(mapa, width=700, height=500)
