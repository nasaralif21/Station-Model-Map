import os
import requests

def download_file(timestamp):

    url = f"http://www.pmdnmcc.net/RealTime/Data/{timestamp}syn.txt"

    # Use the shared storage path for saving the file
    current_directory = os.getcwd()
    shared_storage_path = os.path.join(current_directory, "data", "shared")
    directory = os.path.join(current_directory,shared_storage_path, "Synop")
    # directory = "Synop"
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = os.path.join(directory, f"{timestamp}syn.txt")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"File saved as {filename}")
        return True
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")
        return False

