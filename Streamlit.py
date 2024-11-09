##--------------------------------------------------------------------------------------------------------------------##
## Install
##--------------------------------------------------------------------------------------------------------------------##

# Install necessary libraries
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

# Function to convert Google Drive link to appropriate thumbnail format
def convert_drive_link(link):
    file_id = link.split('/d/')[1].split('/view')[0]
    return f"https://drive.google.com/thumbnail?id={file_id}"

# Load the CSV file of routes and pothole data file
csv_path = './Street_Sweeping_Schedule_20241105.csv'
pothole_data_path = './pothole_data.csv'  # New pothole data source
sweeping_schedule_df = pd.read_csv(csv_path)
pothole_data = pd.read_csv(pothole_data_path)

# Apply conversion to 'Link photo' column to use thumbnail link if it exists in pothole_data
if 'link_photo' in pothole_data.columns:
    pothole_data['converted_link'] = pothole_data['link_photo'].apply(convert_drive_link)

# Filter rows that have NaN values in 'Line' and convert to geometry
sweeping_schedule_df = sweeping_schedule_df[sweeping_schedule_df['Line'].notna()]
sweeping_schedule_df['geometry'] = sweeping_schedule_df['Line'].apply(lambda x: wkt.loads(x) if isinstance(x, str) else None)

# Create a GeoDataFrame
gdf = gpd.GeoDataFrame(sweeping_schedule_df, geometry='geometry', crs="EPSG:4326")

# Set a seed for random selection
random.seed(42)

# Select 60 random points from the routes
sample_points = gdf.sample(n=60, random_state=42)

# Create a map centered on San Francisco
mapa = folium.Map(location=[37.7749, -122.4194], zoom_start=13)

# Add random points to the map with a marker colored based on severity_score
for idx, row in sample_points.iterrows():
    # Get the coordinates of the first point of each line (LINESTRING)
    if row['geometry'] and row['geometry'].geom_type == 'LineString':
        point = row['geometry'].coords[0]  # First point of the line

        # Select a random pothole image link from converted links (if exists)
        image_row = pothole_data.sample(n=1, random_state=random.randint(0, 1000)).iloc[0]
        image_link = image_row['converted_link'] if 'converted_link' in image_row else None

        # Get the severity_score (make sure it exists in the data)
        severity_score = image_row['severity_score'] if 'severity_score' in image_row else 0

        # Convert severity_score to range 0 to 1 to determine color (red for high priority, green for low)
        color_intensity = int((severity_score / 100) * 255)  # Scale 0-255
        color = f'#{color_intensity:02x}{255 - color_intensity:02x}00'  # Gradient from green to red

        # Create a marker with CircleMarker and image link
        folium.CircleMarker(
            location=[point[1], point[0]],  # Coordinates (lat, lon)
            radius=7,  # Circle radius
            color=color,  # Border color
            fill=True,
            fill_color=color,  # Fill color based on severity_score
            fill_opacity=0.7,
            popup=f"<img src='{image_link}' width='150'>" if image_link else "Pothole",  # Image from converted link
            tooltip=f"Severity Score: {severity_score}"  # Show score in tooltip
        ).add_to(mapa)

# Create the Streamlit interface
st.title("Pothole Map in San Francisco")
st.write("This map shows pothole points in San Francisco. The color indicates severity (red = high priority, green = low priority).")

# Display the Folium map in Streamlit
st_folium(mapa, width=700, height=500)
