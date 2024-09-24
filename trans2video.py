import os
import glob
import subprocess
import shutil
import math
from tqdm import tqdm
from utils.file import get_gif_duration 

TMP_FOLDER = "./tmp/"
FONT_FILE = "./ukai.ttc"
MIN_DURATION = 3 

def convert_image_to_video(image_path, output_video_name, is_gif):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    video_name = base_name.replace(TMP_FOLDER, "") + '.mp4'

    os.makedirs(TMP_FOLDER, exist_ok=True)
    temp_video_name = f"{TMP_FOLDER}{video_name}"
    

    if os.path.exists(temp_video_name): 
        print(f"skip already exists file: {temp_video_name}")
        return video_name
    
    if is_gif:
        duration = get_gif_duration(image_path) or 0.016
        if duration < MIN_DURATION:
            loop_times = math.ceil(MIN_DURATION / duration)
            tmp_loop_gif = f"{TMP_FOLDER}{base_name}_loop.gif"
            cmd = (
                f"ffmpeg "
                f"-loglevel panic "
                f"-stream_loop {loop_times} -t {MIN_DURATION} "
                f"-i \"{image_path}\" "
                f"\"{tmp_loop_gif}\""
            )
            subprocess.run(cmd, shell=True)
            image_path = tmp_loop_gif
        cmd = (
            f"ffmpeg -i \"{image_path}\" "
            f"-loglevel panic "
            f"-ignore_loop 0 -pix_fmt yuv420p "
            f"-vf \"fps=fps=v,scale=1280:-2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=dar=16:9\" "
            f"-vf \"drawtext=fontfile={FONT_FILE}:text='{base_name}':x=10:y=10:fontsize=24:fontcolor=white@0.5\" "
            f"-loop 1 -c:v libx264 -c:a copy \"{temp_video_name}\""
        )
    else:
        cmd = (
            f"ffmpeg -loop 1 -i \"{image_path}\" "
            f"-loglevel panic "
            f"-c:v libx264 -t {MIN_DURATION} "
            f"-r 30 -pix_fmt yuv420p "
            f"-vf \"fps=fps=v,scale=1280:-2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=dar=16:9\" "
            f"-vf \"drawtext=fontfile={FONT_FILE}:text='{base_name}':x=10:y=10:fontsize=24:fontcolor=white@0.5\" "
            f"-shortest \"{temp_video_name}\""
        )
    subprocess.run(cmd, shell=True)
    return video_name

def merge_videos(video_files, output_video_name):
    with open(f"{TMP_FOLDER}merge.txt", "w") as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")
    try:
        cmd = f"ffmpeg -f concat -safe 0 -i {TMP_FOLDER}merge.txt -c copy {output_video_name}"
    except Exception as e:
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

def main(directory, output_video_name):
    delete_files_with_pattern(directory, "*.Zone.Identifier")

    image_files = glob.glob(os.path.join(directory, "*"))
    temp_video_files = []
    for image_file in tqdm(image_files):
        if image_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            is_gif = image_file.lower().endswith('.gif')
            video_file = convert_image_to_video(image_file, output_video_name, is_gif)
            temp_video_files.append(video_file)
    merge_videos(temp_video_files, output_video_name)
    # shutil.rmtree(TMP_FOLDER)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python trans2video.py <directory> <output_video_name>")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_video_name = sys.argv[2]
    main(directory, output_video_name)
