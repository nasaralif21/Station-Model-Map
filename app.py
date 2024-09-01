from flask import Flask, request, render_template,jsonify
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_svg import FigureCanvasSVG
from metpy.units import units
from metpy.calc import wind_components
from metpy.plots import StationPlot, sky_cover
from metpy.plots import StationPlot, sky_cover, current_weather, pressure_tendency as pt_symbols
from scipy.spatial import cKDTree
import io,os
from datetime import datetime, timezone


# Use the Agg backend for Matplotlib
import matplotlib
matplotlib.use('Agg')

shared_storage_path = os.getenv('SHARED_STORAGE_PATH', '/data/shared')

# Set the path to the templates directory within the shared storage
template_folder_path = os.path.join(shared_storage_path, 'templates')
print(template_folder_path)
# Initialize the Flask app with the custom template folder
app = Flask(__name__, template_folder=template_folder_path)
# app = Flask(__name__,template_folder="templates")

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

def read_data(time_stamp):
    try:
        # data_file = f"Decoded_Data/{time_stamp}.csv"
        shared_storage_path = os.getenv('SHARED_STORAGE_PATH', '/data/shared')

        # Construct the full path to the data file
        data_file = os.path.join(shared_storage_path, "Decoded_Data", f"{time_stamp}.csv")
        print(data_file)
        print(f"SHARED_STORAGE_PATH: {shared_storage_path}")

        data = pd.read_csv(data_file)
        return data
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred:", str(e))


@app.route("/")
def home():
    # now = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    # timestamp = now.strftime("%Y%m%d")
    timestamp="20240831"
    print(timestamp)
    file_path = f"templates/{timestamp}00.html"
    print("File path in home method", file_path)
    return render_template(f"{timestamp}00.html")

@app.route('/list_html_files')
def list_html_files():
    template_dir = os.path.join(shared_storage_path, 'templates')
    print(template_dir)
    html_files = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    return jsonify(html_files)

@app.route('/<timestamp>')
def serve_html(timestamp):
    return render_template(f'{timestamp}.html')

@app.route("/getfile",methods=['GET'])
def get_timestamp_file():
    timestamp = request.args.get('timestamp', type=int)
    return render_template(f"{timestamp}.html")

@app.route('/generate_svg', methods=['GET'])
def generate_svg():
    current_directory = os.getcwd()
    print("Current Working Directory:", current_directory)
    station_id = request.args.get('code', type=int)
    time_stamp = request.args.get('timestamp', type=int)
    print(station_id)
    print(time_stamp)
     # Load the data
    data=read_data(time_stamp)

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


if __name__ == '__main__':
    app.run(debug=True)
