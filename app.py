from metpy.plots import StationPlot, sky_cover,current_weather, pressure_tendency as pt_symbols
from flask import Flask, request, render_template,jsonify
from matplotlib.backends.backend_svg import FigureCanvasSVG
from folium import GeoJson, Marker, DivIcon
from folium.plugins import MarkerCluster
from metpy.calc import wind_components
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
from metpy.units import units
import json,os,random,folium,io
import pandas as pd
import numpy as np
import scipy as sp

# Use the Agg backend for Matplotlib
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)

def idw_interpolation(x, y, z, xi, yi, power=3, chunk_size=10000):
    tree = cKDTree(np.c_[x, y])
    zi = np.zeros(len(xi))
    for i in range(0, len(xi), chunk_size):
        xi_chunk = xi[i:i + chunk_size]
        yi_chunk = yi[i:i + chunk_size]
        distances, indices = tree.query(np.c_[xi_chunk, yi_chunk], k=len(x), p=2, workers=-1)
        weights = 1 / (distances + 1e-12) ** power
        weights /= weights.sum(axis=1)[:, np.newaxis]
        zi[i:i + chunk_size] = np.sum(weights * z[indices], axis=1)
    return zi

def contours_to_geojson(contour_set):
    features = []
    for level, segs in zip(contour_set.levels, contour_set.allsegs):
        for seg in segs:
            coords = [[pt[0], pt[1]] for pt in seg if pt[0] is not None and pt[1] is not None]
            if len(coords) > 0:
                label_position = random.choice(['start', 'middle', 'end'])
                if label_position == 'start':
                    label_coords = coords[0]
                elif label_position == 'middle':
                    mid_index = len(coords) // 2
                    label_coords = coords[mid_index]
                else:  # 'end'
                    label_coords = coords[-1]
                    
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "level": int(level),
                        "label": int(level),
                        "label_coords": label_coords,
                        "path": coords
                    }
                })
    return json.dumps({"type": "FeatureCollection", "features": features})


def add_labels_to_map(map_obj, feature):
    label_coords = feature['properties']['label_coords']
    label = feature['properties']['label']
    
    # Add the label horizontally along the contour line
    Marker(
        location=[label_coords[1], label_coords[0]],
        icon=DivIcon(html=f'<div class="pressure-labels" style="font-size: 10px; cursor: grab; width:28px; text-align: center; border-radius:8px; color: white; transform: rotate(0deg); background-color: gray;">{label}</div>')
    ).add_to(map_obj)

def style_function(feature):
    return {
        'color': 'black',
        'weight': 1,
        'opacity': 0.8
    }

# Load the CSV data
try:
    data_file = '2023050315.csv'
    data = pd.read_csv(data_file)
except FileNotFoundError:
    print("File not found.")
except Exception as e:
    print("An error occurred:", str(e))

def generate_map():
    print("Generating maps")
    lats = data['Latitude'].values
    lons = data['Longitude'].values
    air_temp = data['air_temp'].values  
    dew_point = data['dew_point'].values
    wind_speed = data['wind_speed'].values
    wind_dir = data['wind_direction'].values
    cloud_cover = data['cloud_cover'].values
    pressure = data['pressure_sea_level'].values
    stations=data['Station_Name'].values
    codes=data['WMO'].values.astype(int)

    valid_indices = ~np.isnan(air_temp)
    valid_indices1 = ~np.isnan(pressure)
    valid_lats = lats[valid_indices1]
    valid_lons = lons[valid_indices1]
    valid_temps = air_temp[valid_indices].astype(float)
    valid_pressure = pressure[valid_indices1].astype(float)

    min_temp = np.min(valid_temps)
    max_temp = np.max(valid_temps)
    temperature_range = np.arange(min_temp, max_temp , 10)
    colors = [
    "rgb(149, 137, 211)",  # -10°C
    "rgb(150, 209, 216)",  # 0°C
    "rgb(129, 204, 197)",  # 10°C
    "rgb(103, 180, 186)",  # 20°C
    "rgb(95, 143, 197)",   # 30°C
    "rgb(80, 140, 62)",    # 40°C
    "rgb(121, 146, 28)",   # 50°C
    "rgb(171, 161, 14)",   # 60°C
    "rgb(223, 177, 6)",    # 70°C
    "rgb(243, 150, 6)",    # 80°C
    "rgb(236, 95, 21)",    # 90°C
    "rgb(190, 65, 18)",    # 100°C
    "rgb(138, 43, 10)"     # 110°C
    ]

# Ensure the number of colors matches the temperature range
    if len(temperature_range) > len(colors):
        raise ValueError("Not enough colors for the temperature range. Please add more colors.")

    color_stops = list(zip(temperature_range, colors[:len(temperature_range)]))

    def create_temp_icon(temp):
        color = color_stops[0][1]  # Default to the lowest color
        for threshold, color_value in color_stops:
            if temp >= threshold:
                color = color_value
            else:
                break
    
        return f"""
        <div class="icon-container" style="color: white; background-color: {color}; display: flex; align-items: center; justify-content: center; padding: 2px; border-radius: 5px; width: 45px;">
            <div style="font-size: 12px; margin-left: 5px;">{temp}&deg;</div>
        </div>
        """
    m = folium.Map(location=[32, 72], zoom_start=6)
    m._name='map'
    m._id='id'

# Create a MarkerCluster layer
    marker_cluster = MarkerCluster(name="Wind Data").add_to(m)

# Add stations to the cluster
    for lat, lon, speed, angle, temp, dew, cloud,station,code in zip(lats, lons, wind_speed, wind_dir, air_temp, dew_point, cloud_cover,stations,codes):
        if not np.isnan(temp):
            icon_html = create_temp_icon(temp)
            
            popup_html = (
        '<div>'
        + '<b>Station (' + str(lat) + ', ' + str(lon) + ')</b><br>'
        + 'Temp: ' + '{:.1f}'.format(temp) + '&deg;C<br>'
        + 'Dew Point: ' + '{:.1f}'.format(dew) + '&deg;C<br>'
        + 'Wind: ' + '{:.1f}'.format(speed) + ' knots<br>'
        + '<button onclick="onMarkerClick(' + str(code) + ')" id="show-model-' + str(code) + '">Show Station Model</button>'
        + '<div id="model' + str(code) + '"></div>'
        + '</div>'
    )


            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(html=icon_html),
                popup=folium.Popup(folium.Html(popup_html, script=True), max_width=800),
                tooltip=station
            ).add_to(marker_cluster)
    m.get_root().html.add_child(folium.Element("""
    <style>
        .marker-cluster {
            display: none !important;
        }
        .icon-container {
            position: relative;
            display: inline-block;
        }
        .icon-container:hover .popup {
            visibility: visible;
            opacity: 1;
        }
        .popup {
            visibility: hidden;
            opacity: 0;
            width: 120px;
            background-color: black;
            color: white;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -60px;
            transition: opacity 0.3s;
        }
        .popup::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: black transparent transparent transparent;
        }
        .timestamp-selector {
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 5px;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0,0,0,0.5);
        }
        .pressure-labels{
        cursor: grab;
        }
    </style>
    """))

    m.get_root().html.add_child(folium.Element("""
    <script>
        var map = window.map_id 
        console.log(map)                                                       
        function onMarkerClick(code) {
            fetch("http://127.0.0.1:5000/generate_svg?code=" + code)
                .then(response => response.text())
                .then(data => {
                    console.log(data)
                    var element = document.getElementById("model"+code );
                    console.log(element)  
                    if (element) {
                        element.innerHTML = data;
                    } else {
                        console.error("Element not found: station-model-" + code);
                    }
                });
        }
        
    document.addEventListener('DOMContentLoaded', function() {
        
        // Function to fetch and display SVG for the selected station
        function fetchSVG(lat, lon) {
            fetch("http://127.0.0.1:5000/get_station_data?lat=" + lat + "&lon=" + lon)
                .then(response => response.text())
                .then(data => {
                    document.getElementById("station-model-" + lat + "-" + lon).innerHTML = data;
                });
        }
        
        // Create timestamp selector
        var timestampSelector = document.createElement('select');
        timestampSelector.className = 'timestamp-selector';
        timestampSelector.innerHTML = '<option value="2023050315">2023-05-03 15:00</option>';
        document.body.appendChild(timestampSelector);
    });
        function adjustLabelSize() {
        var labels = document.getElementsByClassName('pressure-labels');
        for (var i = 0; i < labels.length; i++) {
            labels[i].style.fontSize = '12px'; // Set a fixed font size
        }
    }

        map.on('zoomend', adjustLabelSize);
        document.addEventListener('DOMContentLoaded', adjustLabelSize);
    </script>
    """))

    lat_arr = np.linspace(valid_lats.min(), valid_lats.max(), 500)
    lon_arr = np.linspace(valid_lons.min(), valid_lons.max(), 500)
    lat_grid, lon_grid = np.meshgrid(lat_arr, lon_arr)
    lat_grid_flat, lon_grid_flat = lat_grid.flatten(), lon_grid.flatten()

    pressure_grid_flat = idw_interpolation(valid_lons, valid_lats, valid_pressure, lon_grid_flat, lat_grid_flat)
    pressure_grid = pressure_grid_flat.reshape(lat_grid.shape)

    pressure_grid = sp.ndimage.gaussian_filter(pressure_grid, sigma=3)

    contours = plt.contour(lon_grid, lat_grid, pressure_grid, levels=20)

    contour_geojson = contours_to_geojson(contours)

    geojson_layer = GeoJson(
        contour_geojson,
        name='contours',
        style_function=style_function,
        popup=None
    ).add_to(m)

    # Manually add labels to the map at varied positions
    for feature in json.loads(contour_geojson)['features']:
        add_labels_to_map(m, feature)

# Add high and low-pressure labels
    min_point = np.unravel_index(np.argmin(pressure_grid), pressure_grid.shape)
    max_point = np.unravel_index(np.argmax(pressure_grid), pressure_grid.shape)

    Marker(
        location=[lat_grid[min_point], lon_grid[min_point]],
        icon=DivIcon(html=f'<div style="font-size: 16px; color: red;">L</div>')
    ).add_to(m)

    Marker(
        location=[lat_grid[max_point], lon_grid[max_point]],
        icon=DivIcon(html=f'<div style="font-size: 16px; color: blue;">H</div>')
    ).add_to(m)

    try:
        m.save("./templates/interactive_map.html")
        print("Map saved successfully.")
    except Exception as e:
        print(f"Error saving map: {e}")

@app.route("/")
def home():
    template_path = "./templates/interactive_map.html"
    if not os.path.exists(template_path):
        print("No file avaialbale")
        generate_map()
    return render_template("interactive_map.html")

@app.route('/generate_svg', methods=['GET'])
def generate_svg():
    station_id = request.args.get('code', type=int)
    print(station_id)
     # Load the data
    data = pd.read_csv(data_file)

    # Drop duplicates
    data = data.drop_duplicates(subset='station_id')

    # Find the station with the specified station_id
    station_data = data[data['station_id'] == station_id]

    # Check if the station exists
    if station_data.empty:
        raise ValueError(f"No station found with station_id: {station_id}. Please check the data.")

    # Extract the station's data
    closest_station = station_data.iloc[0]
    
    # Extract parameters and handle missing values
    air_temp = float(closest_station['air_temp']) if not np.isnan(closest_station['air_temp']) else None
    dew_point = float(closest_station['dew_point']) if not np.isnan(closest_station['dew_point']) else None
    pressure = float(closest_station['pressure_sea_level']) if not np.isnan(closest_station['pressure_sea_level']) else None
    wind_speed_knots = float(closest_station['wind_speed']) if not np.isnan(closest_station['wind_speed']) else None
    wind_dir = float(closest_station['wind_direction']) if not np.isnan(closest_station['wind_direction']) else None
    cloud_cover_value = int(round(closest_station['cloud_cover'])) if not np.isnan(closest_station['cloud_cover']) else None
    lat = closest_station['Latitude']
    lon = closest_station['Longitude']
    weather_code = int(closest_station['present_weather']) if not np.isnan(closest_station['present_weather']) else None
    pressure_tendency = int(closest_station['tendency']) if not np.isnan(closest_station['tendency']) else None
    pressure_change = float(closest_station['pressure_change']) if not np.isnan(closest_station['pressure_change']) else None


    # Create a station plot
    fig = plt.figure(figsize=(3, 3), dpi=300)
    ax = fig.add_subplot(1, 1, 1)

    # Turn off the x-axis and y-axis
    ax.axis('off')
    
    station_plot = StationPlot(ax, lon, lat, fontsize=15, spacing=25)

    # Plot temperature if available
    # Plot temperature if available
    if air_temp is not None:
        station_plot.plot_parameter('NW', [air_temp], color='red')
    station_plot.plot_parameter('SW', [dew_point], color='red')
    # Plot pressure if available
    if pressure is not None:
        station_plot.plot_parameter('NE', [pressure], color='black')
    if weather_code is not None:
        station_plot.plot_symbol('W', [weather_code], current_weather, fontsize=12)
    # Plot wind barb if wind data is available
    if wind_speed_knots is not None and wind_dir is not None:
        u, v = wind_components(wind_speed_knots * units('knots'), wind_dir * units('degrees'))
        station_plot.plot_barb(u=[u.magnitude], v=[v.magnitude])
    
    # Plot cloud cover if available
    if cloud_cover_value is not None:
        station_plot.plot_symbol('C', [cloud_cover_value], sky_cover)

    # Plot pressure tendency if available
    if pressure_tendency is not None:
        station_plot.plot_symbol((1.8, 0.1), [pressure_tendency], pt_symbols)
    # Plot pressure change if available
    if pressure_change is not None:
        station_plot.plot_parameter((1, 0.1), [pressure_change], color='green')
    
    # Convert plot to SVG
    svg_buffer = io.StringIO()
    canvas = FigureCanvasSVG(fig)
    canvas.draw()
    canvas.print_svg(svg_buffer)
    plt.close(fig)
    
    # Return SVG data
    svg_data = svg_buffer.getvalue()
    svg_buffer.close()
    
    return svg_data


@app.route('/get_station_data', methods=['GET'])
def get_station_data():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    print(lat,lon)
    filtered_data = data.drop_duplicates(subset='station_id')
    
    # Apply the same filtering for NaNs
    valid_indices_temp = ~np.isnan(filtered_data['air_temp'])
    valid_indices_pressure = ~np.isnan(filtered_data['pressure_station_level'])
    valid_indices_wind = ~np.isnan(filtered_data['wind_speed']) & ~np.isnan(filtered_data['wind_direction'])
    
    valid_indices = valid_indices_temp & valid_indices_pressure & valid_indices_wind
    filtered_data = filtered_data[valid_indices]
    
    # Find the closest station to the provided lat/lon
    distances = np.sqrt((filtered_data['Latitude'] - lat)**2 + (filtered_data['Longitude'] - lon)**2)
    closest_index = np.argmin(distances)
    closest_station = filtered_data.iloc[closest_index]

    # Find the closest station
    latitude=closest_station['Latitude']
    longitude=closest_station['Longitude']
    air_temp = closest_station['air_temp']
    dew_point = closest_station['dew_point']
    cloud_cover = closest_station['cloud_cover']
    pressure = closest_station['pressure_station_level']
    wind_speed = closest_station['wind_speed']
    wind_dir = closest_station['wind_direction']
    station_name = closest_station['Station_Name']
    
    station_data = {
        'latitude': latitude,
        'longitude': longitude,
        'temperature': air_temp,
        'pressure': pressure,
        'dew_point': dew_point,
        'wind_speed': wind_speed,
        'wind_direction': wind_dir,
        'cloud_cover': cloud_cover
    }
    
    return jsonify(station_data)

if __name__ == '__main__':
    app.run(debug=True)
