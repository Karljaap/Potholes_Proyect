##--------------------------------------------------------------------------------------------------------------------##
## Install
##--------------------------------------------------------------------------------------------------------------------##

# Install necessary libraries (if needed)
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

        # Create a marker with CircleMarker and larger image link
        folium.CircleMarker(
            location=[point[1], point[0]],  # Coordinates (lat, lon)
            radius=10,  # Larger circle radius
            color=color,  # Border color
            fill=True,
            fill_color=color,  # Fill color based on severity_score
            fill_opacity=0.7,
            popup=f"<div style='text-align: center;'><img src='{image_link}' width='250'><br><b>Severity Score:</b> {severity_score}</div>" if image_link else f"<b>Pothole<br>Severity Score:</b> {severity_score}",  # Larger image and score text
            tooltip=f"Severity Score: {severity_score}"  # Display score in tooltip
        ).add_to(mapa)

# Create the Streamlit interface
st.title("Pothole Map in San Francisco")
st.write("This map shows pothole points in San Francisco. The color indicates severity (red = high priority, green = low priority).")

# Display the Folium map in Streamlit
st_folium(mapa, width=700, height=500)

# Dynamic filtering and Data Table with more interactivity
st.subheader("Interactive Pothole Data Table")

# Filter by severity score using a slider
min_score, max_score = st.slider("Select severity score range", int(pothole_data['severity_score'].min()), int(pothole_data['severity_score'].max()), (0, 100))
filtered_data = pothole_data[(pothole_data['severity_score'] >= min_score) & (pothole_data['severity_score'] <= max_score)]

# Filter by multiple locations (assuming there is a 'location' column)
if 'location' in pothole_data.columns:
    unique_locations = pothole_data['location'].unique()
    selected_locations = st.multiselect("Select locations", options=unique_locations, default=unique_locations)
    if selected_locations:
        filtered_data = filtered_data[filtered_data['location'].isin(selected_locations)]

# Optional search by image_id
search_term = st.text_input("Search by image_id")
if search_term:
    filtered_data = filtered_data[filtered_data['image_id'].str.contains(search_term, case=False, na=False)]

# Select specific columns to display
columns_to_display = ['image_id', 'damaged_area', 'num_potholes', 'urban/rural', 'severity_score']
filtered_data = filtered_data[columns_to_display]

# Display filtered data with selected columns
st.dataframe(filtered_data)

# Simple button to reset filters by clearing session state (if needed)
if st.button("Reset Filters"):
    st.session_state.clear()
