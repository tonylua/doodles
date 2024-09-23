import os
import re
import json
import requests
from .shared import proxies, save_folder

def download_image(url, filename):
    if os.path.exists(filename): 
        print(f"skip already exists image: {filename}")
        return None
    os.makedirs(save_folder, exist_ok=True)
    response = requests.get(url=url, proxies=proxies)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Image downloaded: {filename}")
        return None
    else:
        print(f"Failed to download image: {url}")
        return { 
            'src': url, 
            'name': filename, 
            'reason': str(response.status_code) + ' ' + response.reason 
        }

def get_file_ext(url):
    match = re.search(r'\.([^./]+)$', url)
    return match.group(1) if match else None 

def sanitize_filename(filename):
    invalid_chars = r'<>:"/\\|?*'
    return re.sub(rf'[{re.escape(invalid_chars)}]', '_', filename)
