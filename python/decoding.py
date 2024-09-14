import os,math
from pymetdecoder import synop as s
import pandas as pd

# Constants
STATION_TYPE = "AAXX"
DEFAULT_WIND_INDICATOR = "4"

# Function to decode SYNOP data
def decode_synop_data(synop_string):
    try:
        decoded_synop = s.SYNOP().decode(synop_string)
        if decoded_synop is None:
            raise ValueError("Decoding returned None")
        return decoded_synop
    except Exception as e:
        print(f"Error decoding SYNOP data: {e}")
        return {}

def safe_get(d, *keys):
    """Safely get a value from a nested dictionary or list."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, {})
        elif isinstance(d, list) and isinstance(key, int):
            if 0 <= key < len(d):
                d = d[key]
            else:
                return None
        else:
            return None
    return d

def get_safe_value(d, *keys, default=None):
    """Safely get a value from a nested dictionary or list with type conversion."""
    value = safe_get(d, *keys)
    
    if isinstance(value, (int, float)):
        return value
    elif isinstance(value, str):
        return value.strip()
    return default


 
def process_station_id(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'station_id' not in decoded_synop:
       return None  
    return get_safe_value(decoded_synop, 'station_id', 'value')


def process_all_temperatures(decoded_synop):
    if not isinstance(decoded_synop, dict):
        return None

    # Initialize a dictionary to hold the results
    temperature_data = {}

    # Process air temperature
    air_temp_value, air_temp_unit = None, None
    if 'air_temperature' in decoded_synop:
        air_temp_value = get_safe_value(decoded_synop, 'air_temperature', 'value')
        air_temp_unit = get_safe_value(decoded_synop, 'air_temperature', 'unit')
    temperature_data['air_temperature'] = (air_temp_value, air_temp_unit)

    # Process dew point
    dew_point_value, dew_point_unit = None, None
    if 'dewpoint_temperature' in decoded_synop:
        dew_point_value = get_safe_value(decoded_synop, 'dewpoint_temperature', 'value')
        dew_point_unit = get_safe_value(decoded_synop, 'dewpoint_temperature', 'unit')
    temperature_data['dewpoint_temperature'] = (dew_point_value, dew_point_unit)

    # Process maximum temperature
    max_temp_value, max_temp_unit = None, None
    if 'maximum_temperature' in decoded_synop:
        max_temp_value = get_safe_value(decoded_synop, 'maximum_temperature', 'value')
        max_temp_unit = get_safe_value(decoded_synop, 'maximum_temperature', 'unit')
    temperature_data['maximum_temperature'] = (max_temp_value, max_temp_unit)

    # Process minimum temperature
    min_temp_value, min_temp_unit = None, None
    if 'minimum_temperature' in decoded_synop:
        min_temp_value = get_safe_value(decoded_synop, 'minimum_temperature', 'value')
        min_temp_unit = get_safe_value(decoded_synop, 'minimum_temperature', 'unit')
    temperature_data['minimum_temperature'] = (min_temp_value, min_temp_unit)

    # Process temperature change
    temp_change_value, temp_change_unit = None, None
    if 'temperature_change' in decoded_synop:
        temp_change_value = get_safe_value(decoded_synop['temperature_change'], 'change', 'value')
        temp_change_unit = get_safe_value(decoded_synop['temperature_change'], 'change', 'unit')
    temperature_data['temperature_change'] = (temp_change_value, temp_change_unit)

    return temperature_data

def process_wind_indicator(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'wind_indicator' not in decoded_synop:
       return None,None

    value= get_safe_value(decoded_synop, 'wind_indicator', 'value')
    unit= get_safe_value(decoded_synop, 'wind_indicator', 'unit')
    
    return value,unit

def process_wind_speed(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'surface_wind' not in decoded_synop:
        return None,None  

    value = get_safe_value(decoded_synop, 'surface_wind', 'speed', 'value')
    unit = get_safe_value(decoded_synop, 'surface_wind', 'speed', 'unit')
    return value, unit

def process_wind_direction(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'surface_wind' not in decoded_synop:
        return None,None 

    value = get_safe_value(decoded_synop, 'surface_wind', 'direction', 'value')
    unit = get_safe_value(decoded_synop, 'surface_wind', 'direction', 'unit')
    if value is None:
        return None, None
    return value,unit

def process_pressure_sea_level(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'sea_level_pressure' not in decoded_synop:
        g = 9.80665  # Gravity (m/s^2)
        Rd = 287.0   # Specific gas constant for dry air (J/kg·K)
    
        surface, surface_unit = process_geopotential(decoded_synop)
        height, height_unit = process_height(decoded_synop)
        temperature = process_all_temperatures(decoded_synop)
        
        # Check if any of the values are None
        if surface is None or height is None or temperature is None:
            return None, None
        
        air_temp = temperature.get('air_temperature', [None])[0]
        
        # Check if air_temp is None
        if air_temp is None:
            return None, None
        
        air_temp_kelvin = air_temp + 273.15
        surface = surface * 100
        exponent = (g * height) / (Rd * air_temp_kelvin)
        value = surface * math.exp(exponent)
        value = value / 100
        value = round(value, 1)
        return value, surface_unit
        

    value = get_safe_value(decoded_synop, 'sea_level_pressure', 'value')
    unit = get_safe_value(decoded_synop, 'sea_level_pressure', 'unit')
    if value is not None:
        if value<400:
            return None,None
    return value,unit

def process_pressure_station_level(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'station_pressure' not in decoded_synop:
      return None,None 

    value = get_safe_value(decoded_synop, 'station_pressure', 'value')
    unit = get_safe_value(decoded_synop, 'station_pressure', 'unit')
    return value,unit

def process_pressure_change(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'pressure_change' not in decoded_synop:
        return None,None 

    value = get_safe_value(decoded_synop, 'pressure_change', 'value')
    unit = get_safe_value(decoded_synop, 'pressure_change', 'unit')

    return value,unit

def process_pressure_tendency(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'pressure_tendency' not in decoded_synop:
        return None
    pressure_tendency=decoded_synop['pressure_tendency']

    value = get_safe_value(pressure_tendency, 'tendency', 'value')

    return value

def process_geopotential(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'geopotential' not in decoded_synop:
        return None,None 

    value = get_safe_value(decoded_synop, 'geopotential', 'surface', 'value')
    unit = get_safe_value(decoded_synop, 'geopotential', 'surface', 'unit')
    return value,unit

def process_height(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'geopotential' not in decoded_synop:
        return  None,None 

    value = get_safe_value(decoded_synop, 'geopotential', 'height', 'value')
    unit = get_safe_value(decoded_synop, 'geopotential', 'height', 'unit')
    return value,unit

def process_precipitation_indicator(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'precipitation_indicator' not in decoded_synop:
        return None

    value = get_safe_value(decoded_synop, 'precipitation_indicator', 'value')
    return value

def process_precipitation_s1(decoded_synop):
    # Check if precipitation_s1 is present in the dictionary
    if not isinstance(decoded_synop, dict) or 'precipitation_s1' not in decoded_synop:
        return None, None, None, None, None, None, None

    # Extract precipitation_s1 data
    precipitation_s1 = decoded_synop['precipitation_s1']

    # Extract amount and time_before_obs
    amount = get_safe_value(precipitation_s1, 'amount', 'value')
    unit=get_safe_value(precipitation_s1, 'amount', 'unit')
    time_before_obs = get_safe_value(precipitation_s1, 'time_before_obs', 'value')

    if time_before_obs == 3:
        return amount, None, None, None, None, None, unit
    elif time_before_obs == 6:
        return None, amount, None, None, None, None, unit
    elif time_before_obs == 9:
        return None, None, amount, None, None, None, unit
    elif time_before_obs == 12:
        return None, None, None, amount, None, None,  unit
    elif time_before_obs == 15:
        return  None, None, None, None, amount, None,  unit
    elif time_before_obs == 18: 
        return  None, None, None, None, None, amount, unit
    else:
        return None, None, None, None, None,None,None

def process_precipitation_s3(decoded_synop):
    # Check if precipitation_s3 is present in the dictionary
    if not isinstance(decoded_synop, dict) or 'precipitation_s3' not in decoded_synop:
        return  None, None, None, None, None, None, None

    # Extract precipitation_s3 data
    precipitation_s3 = decoded_synop['precipitation_s3']


    time_before_obs = get_safe_value(precipitation_s3, 'time_before_obs', 'value')
    amount = get_safe_value(precipitation_s3, 'amount', 'value')
    unit=get_safe_value(precipitation_s3, 'amount', 'unit')
    time_before_obs = get_safe_value(precipitation_s3, 'time_before_obs', 'value')

    if time_before_obs == 3:
        return amount, None, None, None, None, None, unit
    elif time_before_obs == 6:
        return None, amount, None, None, None, None, unit
    elif time_before_obs == 9:
        return None, None, amount, None, None, None, unit
    elif time_before_obs == 12:
        return None, None, None, amount, None, None,  unit
    elif time_before_obs == 15:
        return  None, None, None, None, amount, None,  unit
    elif time_before_obs == 18: 
        return  None, None, None, None, None, amount, unit
    else:
        return None, None, None, None, None,None,None
  
def process_complete_precipitation(decoded_synop):
    precipitation3H = precipitation6H = precipitation9H = precipitation12H = precipitation15H = precipitation18H = precipitation_unit = None
    new_precipitation3H, new_precipitation6H, new_precipitation9H, new_precipitation12H, new_precipitation15H, new_precipitation18H, new_precipitation_unit = process_precipitation_s1(decoded_synop)

    if new_precipitation3H is not None:
        precipitation3H = new_precipitation3H
    if new_precipitation6H is not None:
        precipitation6H = new_precipitation6H
    if new_precipitation9H is not None:
        precipitation9H = new_precipitation9H
    if new_precipitation12H is not None:
        precipitation12H = new_precipitation12H
    if new_precipitation15H is not None:
        precipitation15H = new_precipitation15H
    if new_precipitation18H is not None:
        precipitation18H = new_precipitation18H
    if new_precipitation_unit is not None:
        precipitation_unit = new_precipitation_unit
    
    new_precipitation3H, new_precipitation6H, new_precipitation9H, new_precipitation12H, new_precipitation15H, new_precipitation18H, new_precipitation_unit = process_precipitation_s3(decoded_synop)

    if new_precipitation3H is not None:
        precipitation3H = new_precipitation3H
    if new_precipitation6H is not None:
        precipitation6H = new_precipitation6H
    if new_precipitation9H is not None:
        precipitation9H = new_precipitation9H
    if new_precipitation12H is not None:
        precipitation12H = new_precipitation12H
    if new_precipitation15H is not None:
        precipitation15H = new_precipitation15H
    if new_precipitation18H is not None:
        precipitation18H = new_precipitation18H
    if new_precipitation_unit is not None:
        precipitation_unit = new_precipitation_unit
    
    return precipitation3H , precipitation6H,  precipitation9H , precipitation12H , precipitation15H , precipitation18H , precipitation_unit


def process_precipitation_24h(decoded_synop):
    # Check if precipitation_24h is present in the dictionary
    if not isinstance(decoded_synop, dict) or 'precipitation_24h' not in decoded_synop:
        return None
    # Extract precipitation_24h data
    precipitation_24h = decoded_synop['precipitation_24h']

    # Extract amount
    amount_value = get_safe_value(precipitation_24h, 'amount', 'value')
    
    
    return amount_value

def process_lowest_cloud_base(decoded_synop):
    # Check if the input is a dictionary and contains the 'lowest_cloud_base' key
    if not isinstance(decoded_synop, dict) or 'lowest_cloud_base' not in decoded_synop:
        return None,None,None
    
    # Retrieve the 'lowest_cloud_base' dictionary
    lowest_cloud_base = get_safe_value(decoded_synop, 'lowest_cloud_base')

    # If lowest_cloud_base is None, return an empty string
    if lowest_cloud_base is None:
        return None,None,None
    
    # Retrieve the relevant values from the dictionary
    min_value = get_safe_value(lowest_cloud_base, 'min')
    max_value = get_safe_value(lowest_cloud_base, 'max')
    unit = get_safe_value(lowest_cloud_base, 'unit')
    quantifier = get_safe_value(lowest_cloud_base, 'quantifier')

    # If quantifier is "isGreaterOrEqual", return the min_value with the unit
    if quantifier == "isGreaterOrEqual":
        return min_value,None,unit
    else:
        # If both min and max values are not None, return the range with the unit
        return min_value,max_value ,unit

def process_visibility(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'visibility' not in decoded_synop:
        return None,None 
    value = get_safe_value(decoded_synop, 'visibility', 'value')
    unit = get_safe_value(decoded_synop, 'visibility', 'unit')
    return value,unit

def process_cloud_cover(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'cloud_cover' not in decoded_synop:
        return 0,None 
    value = get_safe_value(decoded_synop, 'cloud_cover', 'value')
    unit = get_safe_value(decoded_synop, 'cloud_cover', 'unit')
    if value is None:
        value=0
    return value,unit

def process_cloud_types(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'cloud_types' not in decoded_synop:
        return None,None,None # Return an empty string if 'cloud_types' is not present
    
   
    low_cloud_type = get_safe_value(decoded_synop, 'cloud_types', 'low_cloud_type', 'value')
    middle_cloud_type = get_safe_value(decoded_synop, 'cloud_types', 'middle_cloud_type', 'value')
 
    if low_cloud_type==None:
        cloud_amount = get_safe_value(decoded_synop, 'cloud_types', 'cloud_amount', 'value')
        cloud_amount_unit = get_safe_value(decoded_synop, 'cloud_types', 'cloud_amount', 'unit')
        cloud_type=None
        return cloud_type,cloud_amount ,cloud_amount_unit

    if middle_cloud_type==None:
        cloud_amount = get_safe_value(decoded_synop, 'cloud_types', 'cloud_amount', 'value')
        cloud_amount_unit = get_safe_value(decoded_synop, 'cloud_types', 'cloud_amount', 'unit')
        cloud_type=None
        return cloud_type,cloud_amount, cloud_amount_unit

       
    # print("Low cloud type: ",low_cloud_type)
    if low_cloud_type > 0 :
        cloud_amount = get_safe_value(decoded_synop, 'cloud_types', 'low_cloud_amount', 'value')
        cloud_amount_unit = get_safe_value(decoded_synop, 'cloud_types', 'low_cloud_amount', 'unit')
        cloud_type = "low"
    elif middle_cloud_type > 0 :
        cloud_amount = get_safe_value(decoded_synop, 'cloud_types', 'middle_cloud_amount', 'value')
        cloud_amount_unit = get_safe_value(decoded_synop, 'cloud_types', 'middle_cloud_amount', 'unit')
        cloud_type = "middle"
    else:
        cloud_amount = None
        cloud_amount_unit = None
        cloud_type = None
   

    return cloud_type,cloud_amount,cloud_amount_unit

def process_weather_indicator(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'weather_indicator' not in decoded_synop:
        return None
    return get_safe_value(decoded_synop, 'weather_indicator', 'value')

def process_present_weather(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'present_weather' not in decoded_synop:
        return None,None,None
    value = get_safe_value(decoded_synop, 'present_weather', 'value')
    time_before_obs_value = get_safe_value(decoded_synop, 'present_weather', 'time_before_obs', 'value')
    time_before_obs_unit = get_safe_value(decoded_synop, 'present_weather', 'time_before_obs', 'unit')

    return value, time_before_obs_value, time_before_obs_unit

def process_past_weather(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'past_weather' not in decoded_synop:
        return None
    past_weather = decoded_synop['past_weather']
    for weather in past_weather:
        if weather is not None:
            value=weather['value']
            return value

def process_cloud_drift_direction(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'cloud_drift_direction' not in decoded_synop:
        return None,None, None  # Return empty strings for low, middle, and high cloud drift directions

    cloud_drift_direction = get_safe_value(decoded_synop, 'cloud_drift_direction')

    def get_direction(cloud_level):
        is_calm_or_stationary = get_safe_value(cloud_level, 'isCalmOrStationary')
        all_directions = get_safe_value(cloud_level, 'allDirections')
        value = get_safe_value(cloud_level, 'value')

        if is_calm_or_stationary:
            return 'Calm/Stationary'
        elif all_directions:
            return 'All Directions'
        else:
            return value if value else None
        
    # Extract low, middle, and high cloud drift directions
    low_direction = get_direction(get_safe_value(cloud_drift_direction, 'low'))
    middle_direction = get_direction(get_safe_value(cloud_drift_direction, 'middle'))
    high_direction = get_direction(get_safe_value(cloud_drift_direction, 'high'))

    return low_direction, middle_direction, high_direction


def process_evapotranspiration(decoded_synop):
    if not isinstance(decoded_synop, dict) or 'evapotranspiration' not in decoded_synop:
        return None,None,

    evapotranspiration = decoded_synop['evapotranspiration']

    amount_value = get_safe_value(evapotranspiration, 'amount', 'value')
    amoun_unit=get_safe_value(evapotranspiration, 'amount', 'unit')
    return amount_value,amoun_unit


# File paths
station_codes_file = "E:/WMO/WMO_stations_data.csv"

def process_synop_files(station_codes_file, directory, output_directory,timestamp):
    # Read the CSV file
    df = pd.read_csv(station_codes_file)
    wmo_codes = set(df['WMO'].astype(int).astype(str))
    station_details_columns = ['Country', 'Region', 'Place_Name', 'Station_Name', 'WMO', 'Latitude', 'Longitude', 'Elevation']

    decoded_fieldnames = [
        'station_id','observation_time', 'air_temp','air_temp_unit', 'dew_point','dew_point_unit', 'min_temp','min_temp_unit','max_temp','max_temp_unit','temp_change','temp_change_unit'
        'wind_indicator','wind_indicator_unit', 'wind_speed','wind_speed_unit', 'wind_direction','wind_direction_unit', 'pressure_sea_level','pressure_sea_level_unit',
        'pressure_station_level','pressure_station_level_unit'
        'pressure_change','pressure_change_unit','tendency', 'geopotential','geopotential_unit', 'height','height_unit','precipitation_indicator', 'precipitation3H','precipitation3H_unit','precipitation6H','precipitation6H_unit',
        'precipitation12H','precipitation12H_unit', 'precipitation18H','precipitation18H_unit', 'precipitation24H','precipitation24H_unit',
        'min_lowest_cloud_base','max_lowest_cloud_base','lowest_cloud_base_unit', 'visibility','visibility_unit', 'cloud_cover','cloud_cover_unit', 'cloud_type','cloud_amount','cloud_amount_unit', 'weather_phenomena', 'present_weather','TBO','TBO_unit',
        'past_weather','low_cloud_direction','mid_cloud_direction','high_cloud_direction'
    ]

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    filename = f"{timestamp}syn.txt"
    filepath = os.path.join(directory, filename)

    # Check if the file exists
    if os.path.isfile(filepath):
        print(f"Start reading data from {filename}")
        try:
            file_path = os.path.join(directory, filename)
            time_str = filename.split('.')[0][6:10] + DEFAULT_WIND_INDICATOR
            output_filename = filename.replace("syn", "").replace(".txt", ".csv")
            output_path = os.path.join(output_directory, output_filename)
            output_data = []  
            unique_synop_strings = set()

            with open(file_path, 'r') as file:
                # Read and filter lines from the current file
                lines = [line.strip() for line in file if line.strip()]
                for line in lines:
                    parts = line.split()
                    if parts and parts[0] in wmo_codes:
                        # Create the SYNOP string
                        synop_string = f"{STATION_TYPE} {time_str} {line}"
                        station_data = df[df['WMO'] == int(parts[0])]

                        if synop_string not in unique_synop_strings:
                            unique_synop_strings.add(synop_string)

                            # Decode the SYNOP string
                            decoded_synop = decode_synop_data(synop_string)

                            temperature = process_all_temperatures(decoded_synop)
                            wind_indicator, wind_indicator_unit = process_wind_indicator(decoded_synop)
                            wind_speed, wind_speed_unit = process_wind_speed(decoded_synop)
                            wind_direction, wind_direction_unit = process_wind_direction(decoded_synop)
                            pressure_sea_level, pressure_sea_level_unit = process_pressure_sea_level(decoded_synop)
                            pressure_station_level, pressure_station_level_unit = process_pressure_station_level(decoded_synop)
                            visibility, visibility_unit = process_visibility(decoded_synop)
                            cloud_cover, cloud_cover_unit = process_cloud_cover(decoded_synop)
                            pressure_change, pressure_change_unit = process_pressure_change(decoded_synop)
                            tendency = process_pressure_tendency(decoded_synop)
                            geopotential, geopotential_unit = process_geopotential(decoded_synop)
                            height, height_unit = process_height(decoded_synop)
                            precipitation3H, precipitation6H, precipitation9H, precipitation12H, precipitation15H, precipitation18H, precipitation_unit = process_complete_precipitation(decoded_synop)
                            precipitation24H = process_precipitation_24h(decoded_synop)
                            lowest_cloud_min, lowest_cloud_max, lowest_cloud_unit = process_lowest_cloud_base(decoded_synop)
                            present_weather_value, TBO, TBO_unit = process_present_weather(decoded_synop)
                            cloud_type, cloud_amount, cloud_amount_unit = process_cloud_types(decoded_synop)
                            low_cloud_direction, mid_cloud_direction, high_cloud_direction = process_cloud_drift_direction(decoded_synop)

                            decoded_data = {
                                'station_id': process_station_id(decoded_synop),
                                'observation_time': time_str,
                                'air_temp': temperature['air_temperature'][0],
                                'air_temp_unit': temperature['air_temperature'][1],
                                'dew_point': temperature['dewpoint_temperature'][0],
                                'dew_point_unit': temperature['dewpoint_temperature'][1],
                                'min_temp': temperature['minimum_temperature'][0],
                                'min_temp_unit': temperature['minimum_temperature'][1],
                                'max_temp': temperature['maximum_temperature'][0],
                                'max_temp_unit': temperature['maximum_temperature'][1],
                                'temp_change': temperature['temperature_change'][0],
                                'temp_change_unit': temperature['temperature_change'][1],
                                'wind_indicator': wind_indicator,
                                'wind_indicator_unit': wind_indicator_unit,
                                'wind_speed': wind_speed,
                                'wind_speed_unit': wind_speed_unit,
                                'wind_direction': wind_direction,
                                'wind_direction_unit': wind_direction_unit,
                                'pressure_sea_level': pressure_sea_level,
                                'pressure_sea_level_unit': pressure_sea_level_unit,
                                'pressure_station_level': pressure_station_level,
                                'pressure_station_level_unit': pressure_station_level_unit,
                                'pressure_change': pressure_change,
                                'pressure_change_unit': pressure_change_unit,
                                'tendency': tendency,
                                'geopotential': geopotential,
                                'geopotential_unit': geopotential_unit,
                                'height': height,
                                'height_unit': height_unit,
                                'precipitation_indicator': process_precipitation_indicator(decoded_synop),
                                'precipitation3H': precipitation3H,
                                'precipitation6H': precipitation6H,
                                'precipitation9H': precipitation9H,
                                'precipitation12H': precipitation12H,
                                'precipitation15H': precipitation15H,
                                'precipitation18H': precipitation18H,
                                'precipitation24H': precipitation24H,
                                'precipitation_unit': precipitation_unit,
                                'min_lowest_cloud_base': lowest_cloud_min,
                                'max_lowest_cloud_base': lowest_cloud_max,
                                'lowest_cloud_base_unit': lowest_cloud_unit,
                                'visibility': visibility,
                                'visibility_unit': visibility_unit,
                                'cloud_cover': cloud_cover,
                                'cloud_cover_unit': cloud_cover_unit,
                                'cloud_type': cloud_type,
                                'cloud_amount': cloud_amount,
                                'cloud_amount_unit': cloud_amount_unit,
                                'weather_phenomena': process_weather_indicator(decoded_synop),
                                'present_weather': present_weather_value,
                                'TBO': TBO,
                                'TBO_unit': TBO_unit,
                                'past_weather': process_past_weather(decoded_synop),
                                'low_cloud_direction': low_cloud_direction,
                                'mid_cloud_direction': mid_cloud_direction,
                                'high_cloud_direction': high_cloud_direction,
                            }
                            station_details = station_data.iloc[0][station_details_columns].to_dict()

                            combined_data = {**station_details, **decoded_data}
                            
                            output_data.append(combined_data)

            output_df = pd.DataFrame(output_data).sort_values(by=['Country'])
            output_df.to_csv(output_path, index=False, columns=output_df.columns)
            print(f"Decoded data saved to {output_path}")   

        except Exception as e:
            print(f"Error processing file {filename}: {e}")
    else:
        print(f"File {filename} does not exist in the directory {directory}")
