import os
import re
import glob
import subprocess
import shutil
import math
import platform
from tqdm import tqdm
from utils.file import get_gif_duration
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TMP_FOLDER = "./tmp/"
FONT_FILE = os.path.abspath("./sounso.ttf")  # Use absolute path
MIN_DURATION = 3 
RESOLUTION = 1280, 720

def add_text_to_image(image_path, text, output_path):
    """Add text overlay to image using PIL.
    More reliable than FFmpeg's drawtext filter on Windows.
    Text is added AFTER scaling to final resolution."""
    try:
        img = Image.open(image_path)
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        w, h = RESOLUTION  # 1280x720
        
        # First: scale and pad to final resolution
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        # Create white background at final resolution
        final_img = Image.new('RGB', (w, h), 'white')
        # Paste scaled image centered
        x = (w - img.width) // 2
        y = (h - img.height) // 2
        final_img.paste(img, (x, y))
        
        # Now add text to the final-resolution image
        draw = ImageDraw.Draw(final_img)
        
        # Try to load font with larger size for final resolution
        try:
            font = ImageFont.truetype(FONT_FILE, size=24)
        except:
            font = ImageFont.load_default()
        
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position text at bottom center
        text_x = (w - text_width) // 2
        text_y = h - text_height - 15
        
        # Draw text with outline for visibility
        outline_width = 2
        outline_color = 'black'
        text_color = 'white'
        
        # Draw outline
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text((text_x + adj_x, text_y + adj_y), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((text_x, text_y), text, font=font, fill=text_color)
        
        final_img.save(output_path)
        return output_path
    except Exception as e:
        # If text overlay fails, just copy original and scale it
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        w, h = RESOLUTION
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        final_img = Image.new('RGB', (w, h), 'white')
        x = (w - img.width) // 2
        y = (h - img.height) // 2
        final_img.paste(img, (x, y))
        final_img.save(output_path)
        return output_path

def convert_image_to_video(image_path, output_video_name, is_gif):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    base_name = re.sub(r"['\\\"]", " ", base_name) # fix concat issue with special chars
    # Use sanitized name for temp file
    safe_base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)[:50]
    video_name = safe_base_name + '.mp4'

    os.makedirs(TMP_FOLDER, exist_ok=True)
    temp_video_name = os.path.abspath(f"{TMP_FOLDER}{video_name}")
    
    if os.path.exists(temp_video_name) and os.path.getsize(temp_video_name) > 50000:
        return temp_video_name  # Return absolute path if already exists and is valid (>50KB)

    w, h = RESOLUTION 
    # Simplified filter: scale then pad (works reliably on Windows)
    scale_filter = f"scale={w}:{h},pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=white"
    
    # For static images: create scaled+padded version with text
    image_to_convert = image_path
    if not is_gif:
        # Add text to static image (at final resolution)
        temp_image_with_text = os.path.abspath(f"{TMP_FOLDER}{safe_base_name}_text.jpg")
        add_text_to_image(image_path, base_name, temp_image_with_text)
        image_to_convert = temp_image_with_text
        # Don't apply scale filter since image is already at 1280x720
        cmd = (
            f"ffmpeg -loop 1 -i \"{image_to_convert}\" "
            f"-c:v mpeg4 -q:v 2 "
            f"-t {MIN_DURATION} -r 30 "
            f"-pix_fmt yuv420p "
            f"-shortest \"{temp_video_name}\" "
        )
    else:
        # For GIFs: add text using FFmpeg drawtext on the scaled output
        duration = get_gif_duration(image_path) or MIN_DURATION
        if duration < MIN_DURATION:
            loop_times = math.ceil(MIN_DURATION / duration)
            tmp_loop_gif = os.path.abspath(f"{TMP_FOLDER}{base_name}_loop.gif")
            cmd = (
                f"ffmpeg -loglevel error "
                f"-stream_loop {loop_times} -t {MIN_DURATION} "
                f"-i \"{image_path}\" "
                f"\"{tmp_loop_gif}\""
            )
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            image_to_convert = tmp_loop_gif
        
        # Escape text for drawtext filter (only basic escaping needed)
        escaped_text = base_name.replace("'", "'\\''")
        
        # Add drawtext to final scaled video for GIFs
        drawtext = (
            f"drawtext=text='{escaped_text}':fontsize=20:fontcolor=white:"
            f"shadowcolor=black:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=h-text_h-15"
        )
        
        # Combine scale, pad, and drawtext
        combined_filter = f"{scale_filter},{drawtext}"
        
        # GIFs: use -r 30 to normalize to 30fps output
        cmd = (
            f"ffmpeg -i \"{image_to_convert}\" "
            f"-ignore_loop 0 -pix_fmt yuv420p "
            f"-vf \"{combined_filter}\" "
            f"-r 30 -c:v mpeg4 -q:v 2 \"{temp_video_name}\""
        )
    
    # Run FFmpeg and check return code
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Return temp_video_name only if:
    # 1. FFmpeg succeeded (return code 0)
    # 2. File was created and is not empty (>50KB)
    if result.returncode == 0 and os.path.exists(temp_video_name) and os.path.getsize(temp_video_name) > 50000:
        return temp_video_name
    else:
        # Clean up failed file if it exists
        if os.path.exists(temp_video_name):
            try:
                os.remove(temp_video_name)
            except:
                pass
        return None

def merge_videos(video_files, output_video_name):
    mergePath = os.path.abspath(f"{TMP_FOLDER}merge.txt") 
    with open(mergePath, "w", encoding='utf-8') as f:
        for video_file in video_files:
            # Use absolute paths and escape properly for ffmpeg concat
            abs_path = os.path.abspath(video_file).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
    try:
        # Use -fflags +genpts to regenerate timestamps and fix Non-monotonic DTS errors
        # caused by videos with different frame rates
        cmd = (
            f"ffmpeg -fflags +genpts -f concat -safe 0 -i \"{mergePath}\" "
            f"-c:v mpeg4 -q:v 2 -vsync cfr \"{output_video_name}\""
        )
    except Exception as e:
        print('mergePath exception', mergePath)
        raise e 
    subprocess.run(cmd, shell=True)

def delete_files_with_pattern(directory, pattern):
    path_pattern = os.path.join(directory, pattern)
    for file_path in glob.glob(path_pattern, recursive=True):
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

def extract_year_from_filename(filename):
    """Extract year from filename for sorting. Returns (year, filename) tuple."""
    basename = os.path.basename(filename)
    # Look for 4-digit year in the filename (capture entire year, not just 19/20)
    years = re.findall(r'\b((?:19|20)\d{2})\b', basename)
    if years:
        year = int(years[-1])  # Use the last year found
        return (year, basename)
    # Default: no year found
    return (0, basename)

def main(directory, output_video_name):
    delete_files_with_pattern(directory, "*.Zone.Identifier")

    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)
    image_files = glob.glob(os.path.join(directory, "*"))
    # Filter image files
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    # Sort by year (descending), then by filename
    image_files.sort(key=lambda x: (-extract_year_from_filename(x)[0], extract_year_from_filename(x)[1]))
    
    temp_video_files = []
    failed_files = []
    for image_file in tqdm(image_files, desc="Converting images to video"):
        is_gif = image_file.lower().endswith('.gif')
        video_file = convert_image_to_video(image_file, output_video_name, is_gif)
        if video_file and os.path.exists(video_file):
            temp_video_files.append(video_file)
        else:
            failed_files.append(os.path.basename(image_file))
    
    print(f"\nConversion complete: {len(temp_video_files)}/{len(image_files)} videos generated")
    if failed_files:
        print(f"Conversion failed: {len(failed_files)} files")
        for fname in failed_files[:5]:
            print(f"   - {fname}")
        if len(failed_files) > 5:
            print(f"   ... and {len(failed_files) - 5} more files")
    print(f"Merging videos...")
    merge_videos(temp_video_files, output_video_name)
    print(f"Video saved to: {os.path.abspath(output_video_name)}")
    # shutil.rmtree(TMP_FOLDER)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python trans2video.py <directory> <output_video_name>")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_video_name = sys.argv[2]
    if platform.system() == "Windows":
        os.environ["FONTCONFIG_PATH"] = "fonts.conf"
    main(directory, output_video_name)
