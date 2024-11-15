import os
import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import random
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from shapely import wkt

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
        latitude, longitude = point[1], point[0]  # Extract lat and lon

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
            location=[latitude, longitude],  # Coordinates (lat, lon)
            radius=10,  # Larger circle radius
            color=color,  # Border color
            fill=True,
            fill_color=color,  # Fill color based on severity_score
            fill_opacity=0.7,
            popup=f"""
                <div style='text-align: center;'>
                    <img src='{image_link}' width='250'><br>
                    <b>Severity Score:</b> {severity_score}<br>
                    <b>Latitude:</b> {latitude:.6f}<br>
                    <b>Longitude:</b> {longitude:.6f}
                </div>
            """ if image_link else f"<b>Pothole<br>Severity Score:</b> {severity_score}<br><b>Latitude:</b> {latitude:.6f}<br><b>Longitude:</b> {longitude:.6f}",  # Larger image and score text
            tooltip=f"Severity Score: {severity_score}"  # Display score in tooltip
        ).add_to(mapa)

# Create the Streamlit interface with tabs
st.title("Pothole Detection Dashboard")

tabs = st.tabs(["San Francisco Map", "Interactive Data Table"])

with tabs[0]:
    st.write("This is a dashboard for pothole detection using images from Autonomous Vehicles. The object detection involves pointing out and delineating the exact shapes of individual objects in an image. The results include precise masks for each object expressed in areas, accompanied by labels and severity scores to indicate the seriousness of the gap. The YOLOv8-seg model has been used, which offers high accuracy in real-time applications. If you need any further assistance or modifications, feel free to ask!")
    
    # Display the Folium map in Streamlit
    st_folium(mapa, width=700, height=600)  # Adjusted height to reduce space

with tabs[1]:
    st.subheader("Interactive Pothole Data Table")
    
    # Filter by severity score using a slider
    min_score, max_score = st.slider("Select severity score range", int(pothole_data['severity_score'].min()), int(pothole_data['severity_score'].max()), (0, 100))
    filtered_data = pothole_data[(pothole_data['severity_score'] >= min_score) & (pothole_data['severity_score'] <= max_score)]
    
    # Filter by damaged area using quartiles
    quartiles = pd.qcut(pothole_data['damaged_area'], 4, labels=["Q1 (0-25%)", "Q2 (25-50%)", "Q3 (50-75%)", "Q4 (75-100%)"])
    selected_quartile = st.selectbox("Select damaged area quartile", options=["All", "Q1 (0-25%)", "Q2 (25-50%)", "Q3 (50-75%)", "Q4 (75-100%)"])
    if selected_quartile != "All":
        filtered_data = filtered_data[quartiles == selected_quartile]
    
    # Filter by number of potholes using a range slider
    min_potholes, max_potholes = st.slider("Select number of potholes range", int(pothole_data['num_potholes'].min()), int(pothole_data['num_potholes'].max()), (0, int(pothole_data['num_potholes'].max())))
    filtered_data = filtered_data[(filtered_data['num_potholes'] >= min_potholes) & (filtered_data['num_potholes'] <= max_potholes)]
    
    # Filter by urban/rural using a selectbox
    urban_rural_filter = st.selectbox("Select urban/rural classification", options=["All", 0, 1], index=0)
    if urban_rural_filter != "All":
        filtered_data = filtered_data[filtered_data['urban/rural'] == urban_rural_filter]
    
    # Select specific columns to display and rename them
    columns_to_display = ['image_id', 'damaged_area', 'num_potholes', 'urban/rural', 'severity_score']
    filtered_data = filtered_data[columns_to_display]
    filtered_data = filtered_data.rename(columns={
        'image_id': 'image id',
        'damaged_area': 'damaged area',
        'num_potholes': 'num potholes',
        'urban/rural': 'urban/rural',
        'severity_score': 'severity score'
    })
    
    # Display filtered data with selected columns
    st.dataframe(filtered_data)
