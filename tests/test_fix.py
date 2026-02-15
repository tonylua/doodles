from utils.file import is_single_frame_gif

gif_path = r'C:\Users\lenovo\doodles\images\20260215233535\2000 Summer Olympic Games in Sydney - Cycling.gif'

print(f"Testing GIF: {gif_path}")
print(f"Is single frame? {is_single_frame_gif(gif_path)}")
