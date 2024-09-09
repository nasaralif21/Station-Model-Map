import os
import re
from datetime import datetime, timezone

def delete_file(directory):
    current_time = datetime.now(timezone.utc)
    timestamp_pattern = re.compile(r'\d{10}')  
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
    
        match = timestamp_pattern.search(filename)
        print(match)
        if match:
            timestamp_str = match.group()
            try:
                file_time = datetime.strptime(timestamp_str, "%Y%m%d%H").replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"Skipping file with invalid timestamp: {filename}")
                continue
        else:
            print(f"Skipping file with no valid timestamp: {filename}")
            continue
        
        time_difference_days = (current_time - file_time).days
        
        if time_difference_days > 10:
            print("Removing file:", file_path)
            os.remove(file_path)

