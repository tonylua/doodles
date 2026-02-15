from PIL import Image

gif_path = r'C:\Users\lenovo\doodles\images\20260215233535\2000 Summer Olympic Games in Sydney - Cycling.gif'

img = Image.open(gif_path)
print('Frame count:', img.n_frames if hasattr(img, 'n_frames') else 'Unknown')
print('Duration (ms):', img.info.get('duration', 'Not found'))

img.seek(0)
total_duration = 0
frame_count = 0

while True:
    try:
        frame_duration = img.info.get('duration', 100)
        total_duration += frame_duration
        frame_count += 1
        img.seek(img.tell() + 1)
    except (EOFError, KeyError):
        break

print(f'Total frames: {frame_count}')
print(f'Total duration: {total_duration}ms = {total_duration/1000}s')
