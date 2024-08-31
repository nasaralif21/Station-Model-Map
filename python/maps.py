import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from folium import GeoJson, Marker, DivIcon
from folium.plugins import MarkerCluster
import scipy as sp
import json,os,random,folium
from mpl_toolkits.basemap import maskoceans

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

def read_data(time_stamp):
    try:
        data_file = f"Decoded_Data/{time_stamp}.csv"
        data = pd.read_csv(data_file)
        return data
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred:", str(e))


def generate_map(time_stamp):
    data=read_data(time_stamp)

    print("Generating maps")
    lats = data['Latitude'].values
    lons = data['Longitude'].values
    air_temp = data['air_temp'].values  
    dew_point = data['dew_point'].values
    wind_speed = data['wind_speed'].values
    wind_dir = data['wind_direction'].values
    cloud_cover = data['cloud_cover'].values
    pressure = data['pressure_sea_level'].values
    stations = data['Station_Name'].values
    codes = data['WMO'].values.astype(int)
    precep = data['precipitation24H'].values

    valid_indices = ~np.isnan(air_temp)
    valid_indices1 = ~np.isnan(pressure)
    valid_lats = lats[valid_indices1]
    valid_lons = lons[valid_indices1]
    valid_temps = air_temp[valid_indices].astype(float)
    valid_pressure = pressure[valid_indices1].astype(float)

    min_temp = np.min(valid_temps)
    max_temp = np.max(valid_temps)
    print(min_temp, max_temp)

    # Define a dynamic temperature range based on the data
    temperature_range = np.linspace(min_temp, max_temp, num=10)
    colors = [
        "rgb(149, 137, 211)",  # Cool temperature color
        "rgb(150, 209, 216)",  # Slightly warm temperature color
        "rgb(129, 204, 197)",  # Warm temperature color
        "rgb(103, 180, 186)",  # Warmer
        "rgb(95, 143, 197)",   # Hot temperature color
        "rgb(80, 140, 62)",    # Hotter
        "rgb(121, 146, 28)",   # Very hot temperature color
        "rgb(171, 161, 14)",   # Extremely hot
        "rgb(223, 177, 6)",    # Scorching
        "rgb(236, 95, 21)"     # Burning hot
    ]

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

    m = folium.Map(location=[32, 72], zoom_start=5)
    m._name = 'map'
    m._id = 'id'

    marker_cluster = MarkerCluster(name="Wind Data").add_to(m)

    for lat, lon, speed, angle, temp, dew, cloud, station, code, pre in zip(lats, lons, wind_speed, wind_dir, air_temp, dew_point, cloud_cover, stations, codes, precep):
        if not np.isnan(temp):
            icon_html = create_temp_icon(temp)
            popup_html = (
                '<div>'
                + '<b>Station (' + '{:.3f}'.format(lat) + ', ' + '{:.3f}'.format(lon) + ')</b><br>'
                + 'Temp: ' + '{:.1f}'.format(temp) + '&deg;C<br>'
                + 'Rain: ' + '{:.1f}'.format(pre) + 'mm<br>'
                + 'Dew Point: ' + '{:.1f}'.format(dew) + '&deg;C<br>'
                + 'Wind: ' + '{:.1f}'.format(speed) + ' knots<br>'
                + '<button onclick="onMarkerClick(' + str(code) + ', \'' + time_stamp + '\')" id="show-model-' + str(code) + '">Show Station Model</button>'
                + '<div id="model' + str(code) + '"></div>'
                + '</div>'
            )
            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(html=icon_html),
                popup=folium.Popup(folium.Html(popup_html, script=True), max_width=800),
                tooltip=station
            ).add_to(marker_cluster)
        

    m.get_root().html.add_child(folium.Element(
    '<script src="/static/script.js"></script>'
    ))



    lat_arr = np.linspace(valid_lats.min(), valid_lats.max(), 1000)
    lon_arr = np.linspace(valid_lons.min(), valid_lons.max(), 1000)
    lat_grid, lon_grid = np.meshgrid(lat_arr, lon_arr)
    lat_grid_flat, lon_grid_flat = lat_grid.flatten(), lon_grid.flatten()

    pressure_grid_flat = idw_interpolation(valid_lons, valid_lats, valid_pressure, lon_grid_flat, lat_grid_flat)
    pressure_grid = pressure_grid_flat.reshape(lat_grid.shape)
    
    pressure_grid = sp.ndimage.gaussian_filter(pressure_grid, sigma=5)
    
    pressure_grid_masked = maskoceans(lon_grid, lat_grid, pressure_grid)

    contours = plt.contour(lon_grid, lat_grid, pressure_grid, levels=30)

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
        m.save(f"./templates/{time_stamp}.html")
        print("Map saved successfully.")
    except Exception as e:
        print(f"Error saving map: {e}")
