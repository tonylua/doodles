import os
import glob
import subprocess
import shutil

TMP_FOLDER = "./tmp/"
    
def convert_image_to_video(image_path, output_video_name, is_gif):
    base_name = os.path.splitext(os.path.basename(image_path))[0]

    os.makedirs(TMP_FOLDER, exist_ok=True)
    temp_video_name = f"{TMP_FOLDER}{base_name}_temp.mp4"

    if os.path.exists(temp_video_name): 
        print(f"skip already exists file: {temp_video_name}")
        return temp_video_name
    
    if is_gif:
        cmd = (
            f"ffmpeg -i \"{image_path}\" "
            f"-ignore_loop 0 -pix_fmt yuv420p "
            f"-vf \"fps=fps=v,scale=1280:-2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=dar=16:9\" "
            f"-vf \"drawtext=text='{base_name}':x=10:y=10:fontsize=24:fontcolor=white@0.5\" "
            f"-loop 1 -t 3 -c:v libx264 -c:a copy \"{temp_video_name}\""
        )
    else:
        cmd = (
            f"ffmpeg -loop 1 -i \"{image_path}\" "
            f"-c:v libx264 -t 3 "
            f"-vf \"scale=1280:-2,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=16:9\" "
            f"-r 30 -pix_fmt yuv420p "
            f"-vf \"drawtext=text='{base_name}':x=10:y=10:fontsize=24:fontcolor=white@0.5\" "
            f"-shortest \"{temp_video_name}\""
        )
    
    subprocess.run(cmd, shell=True)
    
    return temp_video_name

def merge_videos(video_files, output_video_name):
    with open(f"{TMP_FOLDER}merge.txt", "w") as f:
        for video_file in video_files:
            f.write(f"file '{video_file}'\n")
    cmd = f"ffmpeg -f concat -i f'{TMP_FOLDER}merge.txt' -c copy {output_video_name}"
    subprocess.run(cmd, shell=True)

def main(directory, output_video_name):
    image_files = glob.glob(os.path.join(directory, "*"))
    temp_video_files = []
    
    for image_file in image_files:
        if image_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            is_gif = image_file.lower().endswith('.gif')
            video_file = convert_image_to_video(image_file, output_video_name, is_gif)
            temp_video_files.append(video_file)
    
    merge_videos(temp_video_files, output_video_name)
    
    shutil.rmtree(TMP_FOLDER)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python trans2video.py <directory> <output_video_name>")
        sys.exit(1)
    
    directory = sys.argv[1]
    output_video_name = sys.argv[2]
    main(directory, output_video_name)