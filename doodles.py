import os
import re
import json
import math
import requests
from tqdm import tqdm
from datetime import datetime
from playwright.sync_api import sync_playwright
from utils.shared import args, proxies, save_folder, page_size, total_count 
from utils.interceptor import intercept_request, intercept_response

if not args.query:
    print("Please provide a query like `topic_tags=foobar`!")
    exit(1)

DOODLES_URL = "https://doodles.google/search/"
IMAGE_SELECTOR = '.doodle-card-img>img' + ('[src$=".gif"]' if args.only_gif else '')

def run(playwright):
    images_info = []
    fail_info = []

    with tqdm(total=100) as pbar:
        if args.info_file:
            with open(args.info_file, 'r', encoding='utf-8') as json_file:
                images_info = json.load(json_file)
            pbar.update(25)
        else:
            browser = playwright.chromium.launch(
                proxy={"server": proxies['http']} if proxies else None, 
                headless=not bool(args.open)
            )
            context = browser.new_context()
            page = context.new_page()
            page.route("**/*", intercept_request)
            page.on("response", intercept_response)
            page.goto(f"{DOODLES_URL}?{args.query}", timeout=args.timeout)

            pbar.set_description("page loaded")
            pbar.update(5) # 5

            page.wait_for_timeout(20000)  
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
                page.wait_for_selector(IMAGE_SELECTOR, timeout=args.timeout)  
                pbar.set_description("first image found in page")
                pbar.update(5) # 15
            except playwright._impl._api_types.TimeoutError:
                print(f"未能在 {args.timeout/1000} 秒内找到匹配的元素。")
                browser.close()
                return

            pages_count = args.page_start or 1
            images_before = 0
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(3000)  

                show_more_button = page.query_selector('text=Show More')
                if show_more_button and show_more_button.is_visible() and args.limit > images_before:
                    show_more_button.click()

                    page.wait_for_timeout(args.nextpage_timeout or 30000)  

                    images_after = len(page.query_selector_all(IMAGE_SELECTOR))
                    pbar.set_description(f"after next page, {images_after} images scanned")
                    if images_after > images_before:
                        images_before = images_after 
                        pages_count += 1
                else:
                    break

            if not total_count:
                raise Exception("total count not in response!")
            
            desired_total = min(args.limit, total_count)
            if images_before < desired_total:
                exception_msg = f"total {total_count}"
                if args.limit < total_count:
                    exception_msg += f"(limit {args.limit})"
                exception_msg += f", but only {images_before} images found in page, please retry next time!"
                # raise Exception(exception_msg)
                print(exception_msg)

            images = page.query_selector_all(IMAGE_SELECTOR)[0:desired_total]
            indexes = range(len(images))
            
            pbar.set_description(f"all {len(images)} images scanned from {pages_count} pages")
            pbar.update(5) # 20 

            for idx, img in zip(indexes, images):
                src = re.subn(r'^\/\/', 'http://', img.get_attribute('src'))[0]
                idx_offset = ((args.page_start or 1) - 1) * page_size
                alt = img.get_attribute('alt') or f'doodle_{str(idx_offset + idx)}'
                images_info.append({
                    'src': src,
                    'name': sanitize_filename(alt)
                })

            pbar.set_description("images info saved")
            pbar.update(5) # 25
            os.makedirs(save_folder, exist_ok=True)

            with open(f"{save_folder}images_info.json", 'w', encoding='utf-8') as json_file:
                json.dump(images_info, json_file, ensure_ascii=False, indent=4)
            
            browser.close()

        for image in images_info:
            file_ext = get_file_ext(image['src']) or 'jpg'
            fail = download_image(image['src'], f'{save_folder}{image["name"]}.{file_ext}') 
            if fail:
                fail_info.append(fail)
            pbar.set_description(f"downloading...{image['src']}")
            pbar.update(math.floor(75/len(images_info)))
        with open(f"{save_folder}fail_info.json", 'w', encoding='utf-8') as json_file:
            json.dump(fail_info, json_file, ensure_ascii=False, indent=4)

        print(f"{len(fail_info)} failed, {len(images_info)} total, download finished!")
        pbar.close()

with sync_playwright() as playwright:
    run(playwright)
