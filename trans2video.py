import os
import re
import sys
import glob
import subprocess
import shutil
import math
import platform
import json
import argparse
import hashlib
from tqdm import tqdm
from utils.file import get_gif_duration, is_single_frame_gif
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TMP_FOLDER = "./tmp/"
FONT_FILE = os.path.abspath("./sounso.ttf")  # Use absolute path
MIN_DURATION = 3 
RESOLUTION = 1280, 720

def compute_md5(file_path):
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_topics_aggregated():
    """Load topics_aggregated.json file."""
    topics_file = os.path.join(os.path.dirname(__file__), "topics_aggregated.json")
    if os.path.exists(topics_file):
        with open(topics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def flatten_topics(aggregate_name, topics_data):
    """Flatten nested topic structure to get all topic names under an aggregate."""
    topics_set = set()
    
    # Add the aggregate name itself
    topics_set.add(aggregate_name)
    
    # If the aggregate exists in the data and is a dict, add all its children
    if aggregate_name in topics_data and isinstance(topics_data[aggregate_name], dict):
        for child_topic in topics_data[aggregate_name].keys():
            topics_set.add(child_topic)
    
    return topics_set

def find_matching_directories(images_dir, topics_set):
    """Find all directories in images_dir that match any topic in topics_set."""
    matching_dirs = []
    
    if not os.path.exists(images_dir):
        return matching_dirs
    
    for item in os.listdir(images_dir):
        item_path = os.path.join(images_dir, item)
        if os.path.isdir(item_path):
            # Extract topic name from directory name: {timestamp}_{topic}
            match = re.match(r'^\d+_(.+)$', item)
            if match:
                topic_name = match.group(1)
                if topic_name in topics_set:
                    matching_dirs.append(item_path)
    
    return matching_dirs

def add_text_to_image(image_path, text, output_path):
    """Add text overlay to image using PIL.
    More reliable than FFmpeg's drawtext filter on Windows.
    Text is added AFTER scaling to final resolution."""
    try:
        img = Image.open(image_path)
        # 先转 RGBA 再处理：调色板图（P 模式）带透明度时直接 convert('RGB')
        # 会触发 PIL 的 "Palette images with Transparency..." 警告
        if img.mode != 'RGB':
            img = img.convert('RGBA')

        w, h = RESOLUTION  # 1280x720

        # First: scale and pad to final resolution
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        # Create white background at final resolution
        final_img = Image.new('RGB', (w, h), 'white')
        # Paste scaled image centered（用 alpha 作蒙版，透明区域变白）
        x = (w - img.width) // 2
        y = (h - img.height) // 2
        mask = img.split()[3] if img.mode == 'RGBA' else None
        final_img.paste(img, (x, y), mask)
        
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
            img = img.convert('RGBA')
        w, h = RESOLUTION
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        final_img = Image.new('RGB', (w, h), 'white')
        x = (w - img.width) // 2
        y = (h - img.height) // 2
        mask = img.split()[3] if img.mode == 'RGBA' else None
        final_img.paste(img, (x, y), mask)
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
    
    # Check if it's a single-frame GIF (treat as static image)
    treat_as_static = not is_gif or (is_gif and is_single_frame_gif(image_path))
    
    # For static images: create scaled+padded version with text
    image_to_convert = image_path
    if treat_as_static:
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

        # 显式指定 fontfile，绕开 fontconfig：
        # Windows 上 drawtext 默认走 fontconfig 找字体，找不到配置文件会报
        # "Fontconfig error: Cannot load default config file" 导致 GIF 转换失败。
        # 路径要转成正斜杠并转义盘符冒号（C\:/...）以符合 filter 语法。
        font_arg = FONT_FILE.replace('\\', '/').replace(':', '\\:')

        # Add drawtext to final scaled video for GIFs
        drawtext = (
            f"drawtext=fontfile='{font_arg}':text='{escaped_text}':fontsize=20:fontcolor=white:"
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
    # 显式用 UTF-8 解码 FFmpeg 输出：默认会用系统区域编码（中文 Windows 为 GBK），
    # 而 FFmpeg 日志里含非 GBK 字节（如 doodle 标题里的 é/ñ），会触发 UnicodeDecodeError
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    
    # Return temp_video_name only if:
    # 1. FFmpeg succeeded (return code 0)
    # 2. File was created and is not empty (>50KB)
    if result.returncode == 0 and os.path.exists(temp_video_name) and os.path.getsize(temp_video_name) > 50000:
        return temp_video_name
    else:
        # 记录失败原因（FFmpeg 的 stderr 尾部），供上层汇总时查看
        err_tail = (result.stderr or '').strip().splitlines()[-3:]
        convert_image_to_video.last_error = ' | '.join(err_tail) if err_tail else f"returncode={result.returncode}"
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

def main(directory, output_video_name, aggregate=None, dedupe_cache=None):
    # 规范化目录路径：去掉首尾引号和结尾的斜杠/反斜杠
    # （PowerShell 的目录补全会在末尾加反斜杠，配合引号会破坏参数解析）
    directory = directory.strip().strip('"').rstrip('\\/')
    if not os.path.isdir(directory):
        print(f"错误：目录不存在: {directory}")
        sys.exit(1)

    delete_files_with_pattern(directory, "*.Zone.Identifier")

    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)
    os.makedirs(TMP_FOLDER, exist_ok=True)

    image_files = glob.glob(os.path.join(directory, "*"))
    # Filter image files
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]

    if not image_files:
        print(f"错误：目录中没有找到图片: {directory}")
        sys.exit(1)

    # Sort by year (descending), then by filename
    image_files.sort(key=lambda x: (-extract_year_from_filename(x)[0], extract_year_from_filename(x)[1]))
    
    temp_video_files = []
    failed_files = []
    for image_file in tqdm(image_files, desc="Converting images to video"):
        # Deduplication check
        if dedupe_cache is not None:
            file_hash = compute_md5(image_file)
            if file_hash in dedupe_cache:
                continue  # Skip duplicate
            dedupe_cache.add(file_hash)
        
        is_gif = image_file.lower().endswith('.gif')
        video_file = convert_image_to_video(image_file, output_video_name, is_gif)
        if video_file and os.path.exists(video_file):
            temp_video_files.append(video_file)
        else:
            reason = getattr(convert_image_to_video, 'last_error', '')
            failed_files.append((os.path.basename(image_file), reason))

    print(f"\nConversion complete: {len(temp_video_files)}/{len(image_files)} videos generated")
    if failed_files:
        print(f"Conversion failed: {len(failed_files)} files")
        for fname, reason in failed_files[:5]:
            print(f"   - {fname}  =>  {reason}")
        if len(failed_files) > 5:
            print(f"   ... and {len(failed_files) - 5} more files")
    print(f"Merging videos...")
    merge_videos(temp_video_files, output_video_name)
    print(f"Video saved to: {os.path.abspath(output_video_name)}")
    # shutil.rmtree(TMP_FOLDER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert images to video')
    parser.add_argument('output', nargs='?', help='output video name')
    parser.add_argument('directory', nargs='?', help='directory containing images')
    parser.add_argument('--aggregate', help='aggregate topic name from topics_aggregated.json')
    
    args = parser.parse_args()
    
    # Determine operating mode
    if args.aggregate:
        # Aggregate mode: --aggregate=<topic> <output>
        if not args.output:
            print("Error: output video name is required when using --aggregate")
            sys.exit(1)
        
        # Load topics and find matching directories
        topics_data = load_topics_aggregated()
        if not topics_data:
            print("Error: topics_aggregated.json not found or empty")
            sys.exit(1)
        
        # Validate aggregate exists
        if args.aggregate not in topics_data:
            print(f"Error: aggregate '{args.aggregate}' not found in topics_aggregated.json")
            print(f"Available aggregates: {', '.join(sorted(topics_data.keys()))}")
            sys.exit(1)
        
        # Flatten topics to get all topic names under this aggregate
        topics_set = flatten_topics(args.aggregate, topics_data)
        
        # Find matching directories in images folder
        images_base_dir = os.path.join(os.path.dirname(__file__), "images")
        matching_dirs = find_matching_directories(images_base_dir, topics_set)
        
        if not matching_dirs:
            print(f"Error: no directories found matching topics in aggregate '{args.aggregate}'")
            sys.exit(1)
        
        print(f"Aggregate mode: '{args.aggregate}' includes topics: {', '.join(sorted(topics_set))}")
        print(f"Found {len(matching_dirs)} directories to process")
        
        # Use the first matching directory as the processing directory
        # But we'll collect images from all matching directories
        all_image_files = []
        for dir_path in matching_dirs:
            images = glob.glob(os.path.join(dir_path, "*"))
            images = [f for f in images if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
            all_image_files.extend(images)
        
        # Sort by year (descending), then by filename
        all_image_files.sort(key=lambda x: (-extract_year_from_filename(x)[0], extract_year_from_filename(x)[1]))
        
        # Create a temporary directory with symlinks/copies? No, we'll modify main to accept a list
        # Actually, let's just create a wrapper that processes the collected files directly
        
        # We'll modify the flow: instead of using main's directory scanning, we'll process directly here
        if os.path.exists(TMP_FOLDER):
            shutil.rmtree(TMP_FOLDER)
        os.makedirs(TMP_FOLDER, exist_ok=True)
        
        dedupe_cache = set()
        temp_video_files = []
        failed_files = []
        
        print(f"Processing {len(all_image_files)} images from {len(matching_dirs)} directories...")
        for image_file in tqdm(all_image_files, desc="Converting images to video"):
            # Deduplication
            file_hash = compute_md5(image_file)
            if file_hash in dedupe_cache:
                continue
            dedupe_cache.add(file_hash)
            
            is_gif = image_file.lower().endswith('.gif')
            video_file = convert_image_to_video(image_file, args.output, is_gif)
            if video_file and os.path.exists(video_file):
                temp_video_files.append(video_file)
            else:
                reason = getattr(convert_image_to_video, 'last_error', '')
                failed_files.append((os.path.basename(image_file), reason))

        print(f"\nConversion complete: {len(temp_video_files)}/{len(all_image_files)} videos generated")
        if failed_files:
            print(f"Conversion failed: {len(failed_files)} files")
            for fname, reason in failed_files[:5]:
                print(f"   - {fname}  =>  {reason}")
            if len(failed_files) > 5:
                print(f"   ... and {len(failed_files) - 5} more files")
        print(f"Merging videos...")
        merge_videos(temp_video_files, args.output)
        print(f"Video saved to: {os.path.abspath(args.output)}")
        
    elif args.directory and args.output:
        # Original mode: python trans2video.py <directory> <output>
        # Note: argparse order is (output, directory), so we need to swap
        if platform.system() == "Windows":
            os.environ["FONTCONFIG_PATH"] = "fonts.conf"
        dedupe_cache = set()
        main(args.output, args.directory, dedupe_cache=dedupe_cache)
    else:
        parser.print_help()
        sys.exit(1)