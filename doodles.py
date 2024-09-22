import os
import re
import json
import math
import requests
import argparse
from tqdm import tqdm
from datetime import datetime
from playwright.sync_api import sync_playwright

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
args = arg_parser.parse_args()

if not args.query:
    print("Please provide a query like `topic_tags=foobar`!")
    exit(1)

proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
formatted_now = datetime.now().strftime('%Y%m%d%H%M%S')
save_folder = args.dir or f"./images/{formatted_now}/"
css_selector = '.doodle-card-img>img' + ('[src$=".gif"]' if args.only_gif else '')
page_size = 16
total_count = 0

def download_image(url, filename):
    os.makedirs(save_folder, exist_ok=True)
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
        return { 
            'src': url, 
            'name': filename, 
            'reason': str(response.status_code) + ' ' + response.reason 
        }

def get_file_ext(url):
    match = re.search(r'\.([^./]+)$', url)
    return match.group(1) if match else None 

def sanitize_filename(filename):
    invalid_chars = r'<>:"/\\|?*'
    return re.sub(rf'[{re.escape(invalid_chars)}]', '_', filename)

def replace_page(match):
    current_page = int(match.group(1))
    new_page = current_page + ((args.page_start - 1) if args.page_start else 0)
    return f"page={new_page}"

def intercept_request(route, request):
    if "/v1/doodles" in request.url:
        # url = re.subn(r'limit\=\d+', f'limit={args.limit}', request.url)[0]
        # url = re.subn(r'page\=\d+', 'page=1', url)[0]
        url = request.url
        if args.page_start and re.search(r"page\=(\d+)(?:$|\D)", url): 
            url = re.sub(r"page\=(\d+)", replace_page, url)
            print(f"Intercepted request with page: {url}")
        # print(f"Intercepted request: {url}")
        route.continue_(url=url)
    else:
        route.continue_()

def intercept_response(response):
    global total_count 
    if "/v1/doodles" in response.url:
        try:
            data = response.json()  
            if data is None:
                print("Response does not contain valid JSON data.")
            else:
                count = int(data.get('totalItems', 0)) 
                if args.page_start:
                    count += (1 - args.page_start) * page_size 
                if count > total_count:
                    total_count = count 
                    print(total_count, ' doodles total!')
        except (ValueError, TypeError, KeyError) as e:
            print('Error:', e)
    return response

def run(playwright):
    browser = playwright.chromium.launch(
        proxy={"server": proxies['http']} if proxies else None, 
        headless=not bool(args.open)
    )
    context = browser.new_context()
    page = context.new_page()
    page.route("**/*", intercept_request)
    page.on("response", intercept_response)
    page.goto(f"https://doodles.google/search/?{args.query}", timeout=args.timeout)

    with tqdm(total=100) as pbar:
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
            page.wait_for_selector(css_selector, timeout=args.timeout)  
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

                images_after = len(page.query_selector_all(css_selector))
                pbar.set_description(f"after next page, {images_after} images scanned")
                if images_after > images_before:
                    images_before = images_after 
                    pages_count += 1
            else:
                break

        if not total_count:
            raise Exception("total count not in response!")
            browser.close()
            return
        
        desired_total = min(args.limit, total_count)
        if images_before < desired_total:
            exception_msg = f"total {total_count}"
            if args.limit < total_count:
                exception_msg += f"(limit {args.limit})"
            exception_msg += f", but only {images_before} images found in page, please retry next time!"
            # raise Exception(exception_msg)
            # browser.close()
            # return
            print(exception_msg)

        images_info = []
        fail_info = []
        images = page.query_selector_all(css_selector)[0:desired_total]
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
        for image in images_info:
            file_ext = get_file_ext(image['src']) or 'jpg'
            # if (file_ext):
            fail = download_image(image['src'], f'{save_folder}{image["name"]}.{file_ext}') 
            # else:
            #     fail = { 'src': image['src'], 'name': image['name'], 'reason': 'unknown file extension' }
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
