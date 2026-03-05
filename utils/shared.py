import os
import argparse
from datetime import datetime

def get_default_browser():
    browser_paths = [
        (r'C:\Program Files\Google\Chrome\Application\chrome.exe', 'chrome'),
        (r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe', 'chromium'),
        (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', 'msedge'),
        (r'C:\Program Files\Microsoft\Edge\Application\msedge.exe', 'msedge'),
    ]
    for exe_path, browser_type in browser_paths:
        if os.path.exists(exe_path):
            return (browser_type, exe_path)
    return (None, None)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--query', type=str, help='a query string of doodle')
arg_parser.add_argument('--proxy', type=str, help='proxy address', default=None) 
arg_parser.add_argument('--dir', type=str, help='output dir') 
arg_parser.add_argument('--timeout', type=int, help='timeout in milliseconds', default=90000) 
arg_parser.add_argument('--nextpage_timeout', type=int, help='timeout in milliseconds', default=30000) 
arg_parser.add_argument('--open', type=int, help='open browser', default=0) 
arg_parser.add_argument('--only_gif', type=int, help='only gif', default=0) 
arg_parser.add_argument('--limit', type=int, help='total limit', default=999) 
arg_parser.add_argument('--page_start', type=int, help='start page') 
arg_parser.add_argument('--info_file', type=str, help='direct download from json file, skip browser') 
arg_parser.add_argument('--edge', type=int, help='use MS Edge browser', default=0) 
arg_parser.add_argument('--browser_path', type=str, help='browser executable path') 
arg_parser.add_argument('--anonymous', type=int, help='use anonymous mode', default=0)
arg_parser.add_argument('--default-browser', type=int, help='use system default browser', default=0) 

args = arg_parser.parse_args()

proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
formatted_now = datetime.now().strftime('%Y%m%d%H%M%S')
save_folder = args.dir or f"./images/{formatted_now}/"
page_size = 16
