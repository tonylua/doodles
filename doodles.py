import os
import re
import json
import math
import random
import hashlib
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from scrapling import StealthyFetcher
from utils.shared import args, proxies, save_folder, page_size
from utils.file import sanitize_filename, get_file_ext, download_image
from utils.interceptor import intercept_request, intercept_response, TotalCounter

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

def extract_keyword_from_query(query):
    """从查询字符串中提取 topic_tags 或 title_like 的 value 部分"""
    if not query:
        return None
    
    # 分割查询参数（可能多个参数用&连接）
    parts = query.split('&')
    
    # 优先查找 topic_tags
    for part in parts:
        if part.startswith('topic_tags='):
            return part.split('=', 1)[1]
    
    # 其次查找 title_like
    for part in parts:
        if part.startswith('title_like='):
            return part.split('=', 1)[1]
    
    return None

def run():
    images_info = []
    fail_info = []

    try:
        with tqdm(total=100) as pbar:
            if args.info_file:
                with open(args.info_file, 'r', encoding='utf-8') as json_file:
                    images_info = json.load(json_file)
                pbar.update(25)
            else:
                # Initialize Scrapling fetcher with built-in anti-detection
                fetcher = StealthyFetcher()

                pbar.update(5)

                def page_action(page):
                    """Callback function to interact with the page - all page operations must be here"""
                    # Set up request/response interception on the page
                    page.route("**/*", intercept_request)
                    page.on("response", intercept_response)

                    page.wait_for_timeout(random.randint(1500, 3000))
                    page.wait_for_timeout(1000)

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
                            cookie_btn.click()
                            page.wait_for_timeout(500)
                            pbar.update(1)
                    except Exception:
                        pass

                    # Try to capture /v1/doodles response
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
                    if search_button and not has_images_before_cookie:
                        search_button.click()
                        search_button = None
                        pbar.update(3)

                        page.wait_for_timeout(5000)

                        # 检查是否有内容加载
                        has_images = False
                        try:
                            images = page.query_selector_all(IMAGE_SELECTOR)
                            has_images = len(images) > 0 if images else False
                        except Exception:
                            pass

                        # 重试一次
                        if not has_images:
                            try:
                                temp_search_btn = None
                                for sel in ['button.search-doodle__box-button_search', '.search-doodle__box-button_search']:
                                    try:
                                        temp_search_btn = page.query_selector(sel)
                                        if temp_search_btn and temp_search_btn.is_visible():
                                            btn_classes = temp_search_btn.get_attribute('class') or ''
                                            if 'search-doodle__box-button_search' in btn_classes:
                                                break
                                            temp_search_btn = None
                                    except Exception:
                                        pass

                                if temp_search_btn and temp_search_btn.is_visible():
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
                        return

                    # Pagination
                    pages_count = args.page_start or 1
                    images_before = 0
                    while True:
                        page.wait_for_timeout(2000)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        page.wait_for_timeout(1500)

                        show_more_button = page.query_selector('button.search-doodle__results-button')

                        if show_more_button and show_more_button.is_visible():
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

                # Navigate to search page using Scrapling with page_action
                try:
                    response = fetcher.fetch(
                        url=f"{DOODLES_URL}?{args.query}",
                        headless=not bool(args.open),
                        proxy=proxies['http'] if proxies else None,
                        timeout=args.timeout,
                        page_action=page_action
                    )
                except Exception as e:
                    print(f"Failed to fetch page: {e}")
                    return

                pbar.update(5)

                # Extract images from the response HTML using Scrapling's CSS selector
                images_elements = response.css(IMAGE_SELECTOR)
                desired_total = args.limit if args.limit else len(images_elements)
                images_elements = images_elements[0:desired_total]

                for idx, img in enumerate(images_elements):
                    # Get src attribute from Scrapling element
                    src = img.attrib.get('src', '')
                    if not src:  # Skip images with empty src
                        continue
                    src = re.subn(r'^\/\/', 'http://', src)[0]
                    idx_offset = ((args.page_start or 1) - 1) * page_size
                    alt = img.attrib.get('alt', f'doodle_{str(idx_offset + idx)}')
                    images_info.append({
                        'src': src,
                        'name': sanitize_filename(alt)
                    })

                pbar.update(5)
                os.makedirs(save_folder, exist_ok=True)

                with open(f"{save_folder}images_info.json", 'w', encoding='utf-8') as json_file:
                    json.dump(images_info, json_file, ensure_ascii=False, indent=4)

            # 找出所有已存在的文件（用于断点续传）
            existing_files = set()
            last_existing_file = None
            for image in images_info:
                file_ext = get_file_ext(image['src']) or 'jpg'
                if args.info_file:
                    filename = image["name"]
                else:
                    filename = f'{save_folder}{image["name"]}.{file_ext}'

                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    existing_files.add(filename)
                    last_existing_file = filename

            for image in images_info:
                file_ext = get_file_ext(image['src']) or 'jpg'
                # 如果使用 --info-file，name 已经是完整路径，不需要再拼接
                if args.info_file:
                    filename = image["name"]
                else:
                    filename = f'{save_folder}{image["name"]}.{file_ext}'

                # 跳过已存在的文件（最后一张除外，因为可能下载不完整）
                if filename in existing_files and filename != last_existing_file:
                    print(f"跳过已存在: {os.path.basename(filename)}")
                    pbar.update(math.floor(75/len(images_info)) if images_info else 0)
                    continue

                fail = download_image(image['src'], filename)
                if fail:
                    fail_info.append(fail)

                # 如果使用 --info-file，每次下载后立即更新文件（移除成功的，保留失败的）
                if args.info_file and 'fail_info' in args.info_file:
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

            # 重命名文件夹：移除 _tmp 后缀
            norm_save_folder = os.path.normpath(save_folder).rstrip(os.sep).rstrip('/')
            parent_dir = os.path.dirname(norm_save_folder)
            folder_name = os.path.basename(norm_save_folder)
            
            # 确保 parent_dir 不为空（如果是相对路径可能导致空字符串）
            if not parent_dir:
                parent_dir = "."
            
            # 如果文件夹名以 _tmp 结尾，移除它
            if folder_name.endswith('_tmp'):
                final_folder_name = folder_name[:-4]  # 移除 _tmp
                final_save_folder = os.path.join(parent_dir, final_folder_name)
                
                # 避免重名冲突
                counter = 1
                final_path = final_save_folder
                norm_final = os.path.normpath(final_path)
                while os.path.exists(final_path) and norm_final != norm_save_folder:
                    final_path = os.path.join(parent_dir, f"{final_folder_name}_{counter}")
                    norm_final = os.path.normpath(final_path)
                    counter += 1
                
                if norm_final != norm_save_folder:
                    try:
                        os.rename(norm_save_folder, final_path)
                        abs_save_folder = os.path.abspath(final_path)
                        print(f"\n✅ 文件夹已重命名: {folder_name} -> {os.path.basename(final_path)}")
                    except Exception as e:
                        print(f"\n⚠️  重命名失败: {e}")
                        abs_save_folder = os.path.abspath(norm_save_folder)
                else:
                    abs_save_folder = os.path.abspath(norm_save_folder)
            else:
                # 没有 _tmp 后缀（可能是 --info_file 情况），直接使用
                abs_save_folder = os.path.abspath(norm_save_folder)

            # 输出保存结果的目录位置
            print(f"\n{'='*60}")
            print(f"✅ 任务完成：{len(images_info)} 张图片，{len(fail_info)} 张失败")
            print(f"📁 {abs_save_folder}")
            print(f"{'='*60}")
    except Exception as e:
        print(f"\n" + "="*60)
        print(f"❌ 出错: {e}")
        print(f"="*60)
        raise e

run()