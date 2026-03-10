import os
import re
import json
import math
import tempfile
import shutil
import random
import time
import hashlib
from pathlib import Path
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from utils.shared import args, proxies, save_folder, page_size, get_default_browser
from utils.file import sanitize_filename, get_file_ext, download_image
from utils.interceptor import intercept_request, intercept_response, TotalCounter
from cleanup_chrome_profiles import cleanup_chrome_profiles

# 如果指定了 --dedupe 参数，只执行去重操作
if args.dedupe:
    def deduplicate_images(folder_path):
        """按 MD5 去重图片文件"""
        if not os.path.exists(folder_path):
            print(f"错误：目录不存在: {folder_path}")
            exit(1)

        print(f"开始检查重复图片: {os.path.abspath(folder_path)}")
        md5_dict = {}
        duplicates = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

        # 遍历目录中的所有图片文件
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue

            # 检查是否是图片文件
            ext = os.path.splitext(filename)[1].lower()
            if ext not in image_extensions:
                continue

            # 计算 MD5
            try:
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

                if file_hash in md5_dict:
                    # 发现重复
                    duplicates.append({
                        'original': md5_dict[file_hash],
                        'duplicate': file_path
                    })
                else:
                    md5_dict[file_hash] = file_path
            except Exception as e:
                print(f"无法读取文件 {filename}: {e}")

        # 删除重复文件
        if duplicates:
            print(f"发现 {len(duplicates)} 个重复图片，正在删除...")
            for dup in duplicates:
                try:
                    os.remove(dup['duplicate'])
                    print(f"  删除: {os.path.basename(dup['duplicate'])} (与 {os.path.basename(dup['original'])} 重复)")
                except Exception as e:
                    print(f"  删除失败 {os.path.basename(dup['duplicate'])}: {e}")
            print(f"\n{'='*60}")
            print(f"✅ 去重完成，删除了 {len(duplicates)} 个重复文件")
            print(f"📁 {os.path.abspath(folder_path)}")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("✅ 未发现重复图片")
            print(f"📁 {os.path.abspath(folder_path)}")
            print(f"{'='*60}")

    deduplicate_images(args.dedupe)
    exit(0)

if not args.query:
    print("Please provide a query like `topic_tags=foobar`!")
    exit(1)

DOODLES_URL = "https://doodles.google/search/"
IMAGE_SELECTOR = '.doodle-card-img>img' + ('[src$=".gif"]' if args.only_gif else '')

def make_user_data():
    # 动态创建临时子目录
    temp_dir = tempfile.mkdtemp(prefix='chrome_user_', dir=os.getcwd())
    abs_path = os.path.abspath(temp_dir)
    return abs_path 

def cleanup_user_data(user_data_dir):
    """删除用户数据目录的函数 (with retry)"""
    if not user_data_dir or not os.path.exists(user_data_dir):
        return

    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            # Give Chrome time to fully release file locks
            time.sleep(0.5)
            shutil.rmtree(user_data_dir)
            print(f"已成功删除临时用户数据目录: {user_data_dir}")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"删除临时目录失败 (尝试 {attempt + 1}/{max_retries}), {retry_delay} 秒后重试: {str(e)[:50]}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Last attempt failed, just log it
                print(f"警告：无法删除临时用户数据目录 {user_data_dir}: {str(e)[:100]}")
                print(f"请手动删除: {user_data_dir}")

def deduplicate_images(folder_path):
    """按 MD5 去重图片文件"""
    if not os.path.exists(folder_path):
        return

    print(f"\n开始检查重复图片...")
    md5_dict = {}
    duplicates = []
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    # 遍历目录中的所有图片文件
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue

        # 检查是否是图片文件
        ext = os.path.splitext(filename)[1].lower()
        if ext not in image_extensions:
            continue

        # 计算 MD5
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            if file_hash in md5_dict:
                # 发现重复
                duplicates.append({
                    'original': md5_dict[file_hash],
                    'duplicate': file_path
                })
            else:
                md5_dict[file_hash] = file_path
        except Exception as e:
            print(f"无法读取文件 {filename}: {e}")

    # 删除重复文件
    if duplicates:
        print(f"发现 {len(duplicates)} 个重复图片，正在删除...")
        for dup in duplicates:
            try:
                os.remove(dup['duplicate'])
                print(f"  删除: {os.path.basename(dup['duplicate'])} (与 {os.path.basename(dup['original'])} 重复)")
            except Exception as e:
                print(f"  删除失败 {os.path.basename(dup['duplicate'])}: {e}")
        print(f"去重完成，删除了 {len(duplicates)} 个重复文件")
    else:
        print("未发现重复图片")

def human_like(page):
    """Simulate human-like behavior: mouse moves, scrolls, pauses"""
    try:
        w, h = 1366, 768
        # random mouse moves
        for _ in range(random.randint(2, 3)):
            x = random.randint(100, w-100)
            y = random.randint(100, h-100)
            steps = random.randint(5, 10)
            try:
                page.mouse.move(x, y, steps=steps)
            except Exception:
                pass
            page.wait_for_timeout(random.randint(100, 300))
        # gentle scroll
        page.evaluate('window.scrollBy(0, Math.floor(window.innerHeight*0.2));')
        page.wait_for_timeout(random.randint(200, 500))
    except Exception:
        pass

def run(playwright):
    # Clean up old Chrome profile directories at startup
    cleanup_chrome_profiles(verbose=False)
    
    images_info = []
    fail_info = []
    temp_dir = make_user_data()

    try:
        with tqdm(total=100) as pbar:
            if args.info_file:
                with open(args.info_file, 'r', encoding='utf-8') as json_file:
                    images_info = json.load(json_file)
                pbar.update(25)
            else:
                # Determine which browser to use
                use_edge = args.edge
                browser_path = args.browser_path
                
                if not use_edge and args.default_browser:
                    browser_type, browser_path = get_default_browser()
                    if browser_path:
                        print(f"使用系统默认浏览器: {browser_path}")
                    else:
                        print("未找到系统默认浏览器，将使用 Chromium")
                
                launch_options = {
                    "proxy": {"server": proxies['http']} if proxies else None,
                    "headless": not bool(args.open),
                    # 禁用许多自动化指标
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-default-browser-check",
                        "--no-first-run",
                        "--disable-default-apps",
                        "--disable-plugins",
                        "--disable-extensions",
                        "--disable-sync",
                        "--metrics-recording-only",
                        "--mute-audio",
                        "--no-service-autorun",
                    ]
                }
                if use_edge:
                    launch_options["channel"] = 'msedge'
                if browser_path:
                    launch_options["executable_path"] = browser_path

                if args.anonymous:
                    browser = playwright.chromium.launch(**launch_options)
                    context = browser.new_context(
                        viewport={"width": 1366, "height": 768},
                        locale="en-US",
                        timezone_id="America/Los_Angeles"
                    )
                    page = context.new_page()
                else: 
                    launch_options["user_data_dir"] = temp_dir
                    launch_options["bypass_csp"] = True
                    launch_options["ignore_default_args"] = ['--enable-automation']
                    # launch_persistent_context() returns a BrowserContext directly
                    context = playwright.chromium.launch_persistent_context(**launch_options)
                    page = context.new_page()
                    browser = context  # alias for compatibility with browser.close()
                
                # Set client hints for real browser fingerprint
                try:
                    context.set_extra_http_headers({
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'accept-language': 'en-US,en;q=0.9',
                        'accept-encoding': 'gzip, deflate, br',
                        'cache-control': 'max-age=0',
                        'dnt': '1',
                        'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120", "Not:A-Brand";v="99"',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'none',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1'
                    })
                except Exception:
                    pass
                
                # Load cookies if present (returning user behavior)
                cookies_file = os.path.join(temp_dir, 'cookies.json')
                if os.path.exists(cookies_file):
                    try:
                        with open(cookies_file, 'r', encoding='utf-8') as f:
                            cookies = json.load(f)
                        context.add_cookies(cookies)
                    except Exception:
                        pass
    
                # 反反爬 prevent window.navigator.webdriver
                with open('./utils/stealth.min.js', 'r') as f:
                    js = f.read()
                page.add_init_script(js)
                
                # 添加额外的隐形脚本，隐藏window.chrome.webstore
                page.add_init_script("""
                    Object.defineProperty(navigator, 'vendor', {
                        value: 'Google Inc.',
                        enumerable: true
                    });
                    Object.defineProperty(navigator, 'platform', {
                        value: 'Win32',
                        enumerable: true
                    });
                    // 隐藏更多的自动化标志
                    if (window.chrome) {
                        Object.defineProperty(window.chrome, 'webstore', {
                            value: undefined,
                            writable: false
                        });
                    }
                """)
    
                page.route("**/*", intercept_request)
                page.on("response", intercept_response)
                
                # 直接访问搜索页面
                try:
                    page.goto(f"{DOODLES_URL}?{args.query}", timeout=args.timeout, wait_until='load')
                    page.wait_for_timeout(random.randint(1500, 3000))
                except Exception as e:
                    pass
                
                pbar.update(5)
    
                page.wait_for_timeout(1000)
                human_like(page)
                
                # 首先检查并点击 cookie 通知按钮（如果存在）
                has_images_before_cookie = False
                try:
                    initial_images = page.query_selector_all(IMAGE_SELECTOR)
                    initial_count = len(initial_images) if initial_images else 0
                    has_images_before_cookie = initial_count > 0
                except Exception:
                    pass
                
                try:
                    cookie_btn = page.query_selector('.glue-cookie-notification-bar__accept')
                    if cookie_btn and cookie_btn.is_visible():
                        human_like(page)
                        cookie_btn.click()
                        page.wait_for_timeout(500)
                        pbar.update(1)
                except Exception:
                    pass
                
                # Try to capture /v1/doodles response
                # Try to capture /v1/doodles response (for debugging)
                try:
                    page.wait_for_response(
                        lambda r: '/v1/doodles' in r.url and r.status == 200, 
                        timeout=10000
                    )
                except Exception:
                    pass
                
                # 查找搜索按钮 - 使用特定的class优先，避免误匹配其他按钮
                search_button = None
                search_selectors = [
                    # 最具体的选择器优先，直接匹配右上方搜索框旁的搜索按钮
                    'button.search-doodle__box-button_search',
                    '.search-doodle__box-button_search',
                    'button:has-text("Search")',
                    'text=Search',
                    '[data-qa*="search"]',
                    '.search-button',
                    '#search-button',
                ]
                
                for sel in search_selectors:
                    try:
                        elem = page.query_selector(sel)
                        if elem and elem.is_visible():
                            search_button = elem
                            break
                    except Exception:
                        pass
                
                # 第一次点击搜索按钮 - 若cookie前已有内容则跳过
                retry_count = 0
                max_retries = 1  # 最多只重试一次
                search_clicked = False
                
                if search_button and not has_images_before_cookie:
                    human_like(page)
                    search_button.click()
                    search_clicked = True
                    search_button = None  # 清除搜索按钮引用，防止分页循环中被重新点击
                    pbar.update(3)
                    
                    # 等待更长时间，允许页面加载
                    page.wait_for_timeout(5000)  # 等待5秒
                    
                    # 检查是否有内容加载 (防护机制：检查多个条件)
                    has_images = False
                    images_count = 0
                    try:
                        images = page.query_selector_all(IMAGE_SELECTOR)
                        images_count = len(images) if images else 0
                        has_images = images_count > 0
                    except Exception:
                        pass
                    
                    # 只有当确实没有任何内容且还未重试时，才重新点击
                    if not has_images and retry_count < max_retries:
                        retry_count += 1
                        try:
                            # 重新查询搜索按钮，避免使用已清除的引用
                            temp_search_btn = None
                            for sel in ['button.search-doodle__box-button_search', '.search-doodle__box-button_search']:
                                try:
                                    temp_search_btn = page.query_selector(sel)
                                    if temp_search_btn and temp_search_btn.is_visible():
                                        # 确认这确实是搜索按钮
                                        btn_classes = temp_search_btn.get_attribute('class') or ''
                                        if 'search-doodle__box-button_search' in btn_classes:
                                            break
                                        temp_search_btn = None
                                except Exception:
                                    pass
                            
                            if temp_search_btn and temp_search_btn.is_visible():
                                human_like(page)
                                temp_search_btn.click()
                                page.wait_for_timeout(3000)
                        except Exception:
                            pass
                    
                    pbar.update(2)
                else:
                    pbar.update(5) 
            
                try:
                    page.wait_for_selector(IMAGE_SELECTOR, timeout=args.timeout)  
                    pbar.update(5)
                except Exception:
                    try:
                        browser.close()
                    except Exception:
                        pass
                    cleanup_user_data(temp_dir)
                    return
    
                pages_count = args.page_start or 1
                images_before = 0
                while True:
                    page.wait_for_timeout(2000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    human_like(page)
                    page.wait_for_timeout(1500)  
    
                    show_more_button = page.query_selector('button.search-doodle__results-button')
                    
                    if show_more_button and show_more_button.is_visible():
                        # Check if we've reached the limit
                        images_now = len(page.query_selector_all(IMAGE_SELECTOR))
                        if args.limit and images_now >= args.limit:
                            break
                        
                        try:
                            show_more_button.click()
                            page.wait_for_timeout(args.nextpage_timeout or 30000)  
                            
                            images_after = len(page.query_selector_all(IMAGE_SELECTOR))
                            if images_after > images_before:
                                images_before = images_after 
                                pages_count += 1
                            else:
                                break
                        except Exception:
                            break
                    else:
                        break
    
                # API返回null是unfixable (server端reCAPTCHA)，直接用args.limit
                desired_total = args.limit if args.limit else len(page.query_selector_all(IMAGE_SELECTOR))
                if images_before < desired_total:
                    exception_msg = f"total {TotalCounter.total_count}"
                    if args.limit < TotalCounter.total_count:
                        exception_msg += f"(limit {args.limit})"
                    exception_msg += f", but only {images_before} images found in page, please retry next time!"
                    # raise Exception(exception_msg)
                    print(exception_msg)
    
                images = page.query_selector_all(IMAGE_SELECTOR)[0:desired_total]
                indexes = range(len(images))
                pbar.update(5) 
    
                for idx, img in zip(indexes, images):
                    src = re.subn(r'^\/\/', 'http://', img.get_attribute('src'))[0]
                    idx_offset = ((args.page_start or 1) - 1) * page_size
                    alt = img.get_attribute('alt') or f'doodle_{str(idx_offset + idx)}'
                    images_info.append({
                        'src': src,
                        'name': sanitize_filename(alt)
                    })
    
                pbar.update(5)
                os.makedirs(save_folder, exist_ok=True)
    
                with open(f"{save_folder}images_info.json", 'w', encoding='utf-8') as json_file:
                    json.dump(images_info, json_file, ensure_ascii=False, indent=4)
                
                # Save cookies for next run (returning user behavior)
                try:
                    cookies = context.cookies()
                    cookies_file = os.path.join(temp_dir, 'cookies.json')
                    with open(cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                
                browser.close()
                cleanup_user_data(temp_dir)
    
            for image in images_info:
                file_ext = get_file_ext(image['src']) or 'jpg'
                # 如果使用 --info-file，name 已经是完整路径，不需要再拼接
                if args.info_file:
                    filename = image["name"]
                else:
                    filename = f'{save_folder}{image["name"]}.{file_ext}'
                fail = download_image(image['src'], filename)
                if fail:
                    fail_info.append(fail)

                # 如果使用 --info-file，每次下载后立即更新文件（移除成功的，保留失败的）
                if args.info_file:
                    with open(args.info_file, 'w', encoding='utf-8') as json_file:
                        # 计算剩余未处理的图片（当前失败的 + 还未处理的）
                        remaining = fail_info + images_info[images_info.index(image) + 1:]
                        json.dump(remaining, json_file, ensure_ascii=False, indent=4)

                pbar.update(math.floor(75/len(images_info)) if images_info else 0)

            # 保存最终的 fail_info（如果不是使用 --info-file，或者作为备份）
            with open(f"{save_folder}fail_info.json", 'w', encoding='utf-8') as json_file:
                json.dump(fail_info, json_file, ensure_ascii=False, indent=4)

            pbar.close()

            # 去重图片
            deduplicate_images(save_folder)

            # 输出保存结果的目录位置
            abs_save_folder = os.path.abspath(save_folder)
            print(f"\n{'='*60}")
            print(f"✅ 任务完成：{len(images_info)} 张图片，{len(fail_info)} 张失败")
            print(f"📁 {abs_save_folder}")
            print(f"{'='*60}")
    except Exception as e:
        cleanup_user_data(temp_dir)
        print(f"\n" + "="*60)
        print(f"❌ 出错: {e}")
        print(f"="*60)

with sync_playwright() as playwright:
    run(playwright)
