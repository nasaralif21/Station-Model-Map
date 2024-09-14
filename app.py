from flask import Flask, request, render_template,jsonify
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_svg import FigureCanvasSVG
from metpy.units import units
from metpy.calc import wind_components
from metpy.plots import StationPlot, sky_cover
from metpy.plots import StationPlot, sky_cover, current_weather, pressure_tendency as pt_symbols
import io,os,json
from flask_compress import Compress
from flask_caching import Cache

import matplotlib
matplotlib.use('Agg')

app = Flask(__name__,template_folder="templates")
Compress(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})


def read_data(time_stamp):
    try:
        data_file = f"Decoded_Data/{time_stamp}.csv"
        data = pd.read_csv(data_file)
        return data
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred:", str(e))


@app.route("/")
def home():    
    return render_template("index.html")

@app.route('/api/geojson', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def get_geojson():
    time_stamp = request.args.get('timestamp', type=int)
    json_path = f"contours_data/{time_stamp}.geojson"
    
    if not os.path.exists(json_path):
        return jsonify({"error": "File not found"}), 404

    try:
        with open(json_path, 'r') as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode JSON"}), 500
    
    return jsonify(data)

@app.route('/api/temperature',methods=["GET"])
def get_temperature_data():
    time_stamp = request.args.get('timestamp', type=int)

    data=read_data(time_stamp)
    data = data.dropna(subset=['air_temp'])
    data = data.drop_duplicates(subset='station_id')
    lats = data['Latitude'].tolist()
    lons = data['Longitude'].tolist()
    air_temp = data['air_temp'].tolist()
    stations = data['Station_Name'].tolist()
    codes=data["station_id"].tolist()
    
    response_data = [{'lat': lat, 'lon': lon, 'temp': temp,'station':station,"code":code} for lat, lon, temp,station,code in zip(lats, lons, air_temp,stations,codes)]
    
    return jsonify(response_data)

@app.route('/list_data_files')
def list_html_files():
    geojson_dir = "contours_data"
    geojson_files = [f for f in os.listdir(geojson_dir) if f.endswith('.geojson')]
    return jsonify(geojson_files)

@app.route('/generate_svg', methods=['GET'])
def generate_svg():
    station_id = request.args.get('code', type=int)
    time_stamp = request.args.get('timestamp', type=int)
    data=read_data(time_stamp)

    data = data.drop_duplicates(subset='station_id')

    station_data = data[data['station_id'] == station_id]

    if station_data.empty:
        raise ValueError(f"No station found with station_id: {station_id}. Please check the data.")

    closest_station = station_data.iloc[0]
    
    air_temp = float(closest_station['air_temp']) if not np.isnan(closest_station['air_temp']) else None
    dew_point = float(closest_station['dew_point']) if not np.isnan(closest_station['dew_point']) else None
    pressure = float(closest_station['pressure_sea_level']) if not np.isnan(closest_station['pressure_sea_level']) else None
    pressure_station = float(closest_station['pressure_station_level']) if not np.isnan(closest_station['pressure_station_level']) else None
    wind_speed_knots = float(closest_station['wind_speed']) if not np.isnan(closest_station['wind_speed']) else None
    wind_dir = float(closest_station['wind_direction']) if not np.isnan(closest_station['wind_direction']) else None
    cloud_cover_value = int(round(closest_station['cloud_cover'])) if not np.isnan(closest_station['cloud_cover']) else None
    lat = closest_station['Latitude']
    lon = closest_station['Longitude']
    weather_code = int(closest_station['present_weather']) if not np.isnan(closest_station['present_weather']) else None
    pressure_tendency = int(closest_station['tendency']) if not np.isnan(closest_station['tendency']) else None
    pressure_change = float(closest_station['pressure_change']) if not np.isnan(closest_station['pressure_change']) else None
    Place = closest_station['Place_Name']

    # Create a station plot
    fig = plt.figure(figsize=(2, 2), dpi=300)
    ax = fig.add_subplot(1, 1, 1)
    # ax.axis('off')
    
    station_plot = StationPlot(ax, lon, lat, fontsize=15, spacing=25)

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
    
    response_data = {
        'station_id': station_id,
        'timestamp': time_stamp,
        'svg': svg_data,
        'additional_data': {
            'air_temp': air_temp,
            'dew_point': dew_point,
            'pressure': pressure_station,
            'wind_speed_knots': wind_speed_knots,
            'wind_dir': wind_dir,
            'cloud_cover_value': cloud_cover_value,
            'lat': round(lat, 3) ,
            'lon': round(lon, 3) ,
            'weather_code': weather_code,
            'pressure_tendency': pressure_tendency,
            'pressure_change': pressure_change,
            'place_name':Place
        }
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True,port=8000)
