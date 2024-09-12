import os
import re
import json
import math
import requests
import argparse
from playwright.sync_api import sync_playwright
from tqdm import tqdm
from datetime import datetime

now = datetime.now()
formatted_now = now.strftime('%Y%m%d%H%M%S')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--query', type=str, help='a query string of doodle')
arg_parser.add_argument('--proxy', type=str, help='proxy address', default=None) 
arg_parser.add_argument('--dir', type=str, help='output dir', default='./images/') 
arg_parser.add_argument('--timeout', type=int, help='timeout in milliseconds', default=90000) 
arg_parser.add_argument('--nextpage_timeout', type=int, help='timeout in milliseconds', default=30000) 
arg_parser.add_argument('--open', type=int, help='open browser', default=0) 
args = arg_parser.parse_args()

if not args.query:
    print("Please provide a query like `topic_tags=foobar`!")
    exit(1)

proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
timeout = args.timeout or 90000
save_folder = f"{args.dir}{formatted_now}/" if args.dir else f"./images/{formatted_now}/"
os.makedirs(save_folder, exist_ok=True)

def download_image(url, filename):
    if os.path.exists(filename): 
        print(f"skip already exists image: {filename}")
        return None
    response = requests.get(url=url, proxies=proxies)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Image downloaded: {filename}")
        return None
    else:
        print(f"Failed to download image: {url}")
        return { 'src': url, 'name': name }
        

def run(playwright):
    # browser = playwright.chromium.launch(headless=False)
    browser = playwright.chromium.launch(proxy={"server": proxies['http']}, headless=not bool(args.open))
    context = browser.new_context()
    page = context.new_page()

    with tqdm(total=100) as pbar:
        page.goto(f"https://doodles.google/search/?{args.query}", timeout=timeout)
        pbar.set_description("page loaded")
        pbar.update(5) # 5

        page.wait_for_timeout(15000)  
        search_button = page.query_selector('text=Search')
        if not search_button:
            print("未找到搜索按钮，请检查页面是否已加载完成。")
            browser.close()
            return
        search_button.click()
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        pbar.set_description("search button clicked")
        pbar.update(5) # 10 
    
        try:
            page.wait_for_selector('.doodle-card-img>img[src$=".gif"]', timeout=timeout)  
            pbar.set_description("first image found")
            pbar.update(5) # 15
        except playwright._impl._api_types.TimeoutError:
            print(f"未能在 {timeout/1000} 秒内找到匹配的元素。")
            browser.close()
            return

        images_before = 0
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            page.wait_for_timeout(3000)  

            show_more_button = page.query_selector('text=Show More')
            if show_more_button and show_more_button.is_visible():
                show_more_button.click()

                page.wait_for_timeout(args.nextpage_timeout or 30000)  

                images_after = len(page.query_selector_all('.doodle-card-img>img[src$=".gif"]'))
                pbar.set_description(f"after next page, {images_after} images scanned")
                if images_after > images_before:
                    images_before = images_after 
                else:
                    print("没有新的图片加载，停止循环。")
                    break
            else:
                break

        images_info = []
        fail_info = []
        images = page.query_selector_all('.doodle-card-img>img[src$=".gif"]')
        indexes = range(len(images))
        
        pbar.set_description(f"all images scanned, {len(images)} total")
        pbar.update(5) # 20 

        for idx, img in zip(indexes, images):
            src = re.subn(r'^\/\/', 'http://', img.get_attribute('src'))[0]
            alt = str(idx) + '-' + (img.get_attribute('alt') or 'doodle')
            images_info.append({
                'src': src,
                'name': alt
            })

        pbar.set_description("images info saved")
        pbar.update(5) # 25
        os.makedirs(save_folder, exist_ok=True)

        with open(f"{save_folder}images_info.json", 'w', encoding='utf-8') as json_file:
            json.dump(images_info, json_file, ensure_ascii=False, indent=4)
        for image in images_info:
            fail = download_image(image['src'], f'{save_folder}{image["name"]}.gif') 
            if fail:
                fail_info.append(fail)
            pbar.set_description("images downloading...")
            pbar.update(math.floor(75/len(images_info)))
        with open(f"{save_folder}fail_info.json", 'w', encoding='utf-8') as json_file:
            json.dump(fail_info, json_file, ensure_ascii=False, indent=4)

        print(f"{len(fail_info)} failed, {len(images_info)} total, download finished!")
        pbar.close()
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
