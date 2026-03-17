import os
import argparse
from datetime import datetime

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
arg_parser.add_argument('--dedupe', type=str, help='deduplicate images in specified directory by MD5 hash')

args = arg_parser.parse_args()

proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
formatted_now = datetime.now().strftime('%Y%m%d%H%M%S')

# 如果使用 --info_file，自动使用 info_file 所在的目录作为 save_folder
if args.info_file:
    info_file_dir = os.path.dirname(os.path.abspath(args.info_file))
    save_folder = info_file_dir + os.sep
else:
    save_folder = args.dir or f"./images/{formatted_now}/"

page_size = 16
