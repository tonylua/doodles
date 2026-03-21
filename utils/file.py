import os
import re
import json
import requests
from PIL import Image

def get_gif_duration(path):
    """Get GIF duration in seconds with fallback for corrupted files.
    Max duration capped at 5 seconds to prevent freeze issues."""
    try:
        img_obj = Image.open(path)
        img_obj.seek(0)  # move to the start of the gif, frame 0
        tot_duration = 0
        frame_count = 0
        while True:
            try:
                frame_duration = img_obj.info.get('duration', 100)  # returns current frame duration in milli sec.
                tot_duration += frame_duration
                img_obj.seek(img_obj.tell() + 1)  # image.tell() = current frame
                frame_count += 1
            except (EOFError, KeyError):
                break
        
        # Convert milliseconds to seconds
        duration_seconds = tot_duration / 1000.0 if tot_duration > 0 else 3.0
        # Cap at maximum 5 seconds to prevent freeze issues with GIFs
        return min(duration_seconds, 5.0)
    except Exception as e:
        # Corrupted GIF or read error - return fallback duration
        return 3.0

def is_single_frame_gif(path):
    """Check if a GIF is a single-frame (non-animated) GIF."""
    try:
        img_obj = Image.open(path)
        img_obj.seek(0)
        frame_count = 0
        while True:
            try:
                frame_count += 1
                img_obj.seek(img_obj.tell() + 1)
            except (EOFError, KeyError):
                break
        return frame_count <= 1
    except Exception as e:
        return False

def download_image(url, filename):
    import time
    from .shared import proxies, save_folder

    if os.path.exists(filename):
        print(f"skip already exists image: {filename}")
        return None

    # 确保目标目录存在
    file_dir = os.path.dirname(filename)
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)

    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url=url, proxies=proxies, timeout=10)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"Image downloaded: {filename}")
                return None
            else:
                last_error = f"{response.status_code} {response.reason}"
                print(f"Attempt {attempt + 1}/{max_retries + 1} failed: {last_error}")
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1}/{max_retries + 1} error: {last_error}")
        
        if attempt < max_retries:
            time.sleep(1)
    
    print(f"Failed to download image after {max_retries + 1} attempts: {url}")
    return {
        'src': url,
        'name': filename,
        'reason': last_error
    }

def get_file_ext(url):
    match = re.search(r'\.([^./]+)$', url)
    return match.group(1) if match else None 

def sanitize_filename(filename):
    invalid_chars = r'<>:"/\\|?*'
    return re.sub(rf'[{re.escape(invalid_chars)}]', '_', filename)