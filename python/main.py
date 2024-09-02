from download_synop import download_file
from decoding import process_synop_files
from maps import generate_map
from datetime import datetime, timedelta, timezone
import time

def main():
    now = datetime.now(timezone.utc)
    hour = now.hour
    print(hour)
    interval_start_hour = (hour // 3) * 3
    timestamp = now.replace(hour=interval_start_hour, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H")
    
    print(f"Timestamp: {timestamp}")

    
    print("Running download_synop...")
    download_success = download_file(timestamp)
    print(download_success)
    if download_success:
        # Step 2: Run the decoding file
        print("Running decoding...")
        station_codes_file = "static/WMO_stations_data.csv"
        directory = 'Synop'
        output_directory = "Decoded_Data"
        process_synop_files(station_codes_file, directory, output_directory, timestamp)
        
        print("Running maps...")
        generate_map(timestamp)
    else:
        print("Data download failed. Will retry next hour.")

def schedule_task():
    while True:
        now = datetime.now(timezone.utc)
        print(f"Current time: {now}")

        # Run the main task
        main()
        # Calculate the time until the next hour
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        time_until_next_hour = (next_hour - now).total_seconds()
        
        time_until_next_hour_minutes = int(time_until_next_hour / 60)
        
        print(f"Sleeping for {time_until_next_hour_minutes} minutes until next hour.")
        time.sleep(time_until_next_hour)

if __name__ == "__main__":
    schedule_task()
