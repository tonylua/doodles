import os
import re
import argparse
import shutil
from datetime import datetime
from urllib.parse import unquote
import time

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
arg_parser.add_argument('--retry', type=str, help='re-download missing/incomplete images in a finished folder using its images_info.json')
arg_parser.add_argument('--download_timeout', type=int, help='per-request download timeout in seconds', default=10)
arg_parser.add_argument('--download_retries', type=int, help='number of extra download attempts after the first', default=2)

args = arg_parser.parse_args()

proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
# 使用毫秒级时间戳保证唯一性: YYYYMMDDHHMMSSmmm (17位)
formatted_now = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # 截取前3位毫秒


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


def sanitize_filename(name):
    """将字符串转换为合法的文件名（替换非法字符）"""
    # 替换 Windows/Linux/macOS 中非法的文件名字符
    illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
    return re.sub(illegal_chars, '_', name)


def get_save_folder(query, base_dir=None):
    """
    根据查询生成保存文件夹路径
    下载期间使用 _tmp 后缀，完成后重命名去掉 _tmp
    """
    if args.info_file:
        info_file_dir = os.path.dirname(os.path.abspath(args.info_file))
        return info_file_dir + os.sep
    
    # 使用指定目录或默认 images 目录
    base = args.dir or base_dir or "./images"
    
    keyword = extract_keyword_from_query(query)
    if not keyword:
        # 无法提取关键字，使用纯时间戳（带 _tmp）
        return f"{base}/{formatted_now}_tmp/"
    
    # URL 解码（把 %20 之类还原成空格），再规范化为合法的文件夹名
    safe_keyword = sanitize_filename(unquote(keyword))
    return f"{base}/{formatted_now}_{safe_keyword}_tmp/"


def finalize_folder(save_folder):
    """把下载完成的文件夹从 ..._tmp 重命名为最终名（去掉 _tmp、URL 解码）。

    返回最终文件夹的绝对路径。若无需重命名或重命名失败，返回原文件夹的绝对路径。
    """
    norm_save_folder = os.path.normpath(save_folder).rstrip(os.sep).rstrip('/')
    parent_dir = os.path.dirname(norm_save_folder) or "."
    folder_name = os.path.basename(norm_save_folder)

    if not folder_name.endswith('_tmp'):
        return os.path.abspath(norm_save_folder)

    # 去掉 _tmp 并对整名做 URL 解码（历史遗留的 %20 也一并还原）
    final_folder_name = sanitize_filename(unquote(folder_name[:-4]))
    final_save_folder = os.path.join(parent_dir, final_folder_name)

    # 避免重名冲突
    counter = 1
    final_path = final_save_folder
    norm_final = os.path.normpath(final_path)
    while os.path.exists(final_path) and norm_final != norm_save_folder:
        final_path = os.path.join(parent_dir, f"{final_folder_name}_{counter}")
        norm_final = os.path.normpath(final_path)
        counter += 1

    if norm_final == norm_save_folder:
        return os.path.abspath(norm_save_folder)

    try:
        os.rename(norm_save_folder, final_path)
        print(f"\n✅ 文件夹已重命名: {folder_name} -> {os.path.basename(final_path)}")
        return os.path.abspath(final_path)
    except Exception as e:
        print(f"\n⚠️  重命名失败: {e}")
        return os.path.abspath(norm_save_folder)


def cleanup_tmp_folders(base_dir=None):
    """
    清理所有 orphaned _tmp 文件夹（不完整的下载）
    
    Args:
        base_dir: 要清理的基础目录，默认为 ./images
    
    Returns:
        dict: 包含清理统计信息的字典
    """
    base = base_dir or "./images"
    
    if not os.path.exists(base):
        return {'deleted': 0, 'kept': 0, 'errors': []}
    
    deleted = 0
    kept = 0
    errors = []
    
    try:
        entries = os.listdir(base)
    except Exception as e:
        return {'deleted': 0, 'kept': 0, 'errors': [str(e)]}
    
    for entry in entries:
        dir_path = os.path.join(base, entry)
        
        # 只处理目录
        if not os.path.isdir(dir_path):
            continue
        
        # 检查是否是 _tmp 文件夹（以 _tmp 结尾）
        if entry.endswith('_tmp'):
            # 检查文件夹是否包含 images_info.json 或图片文件
            has_images_info = os.path.exists(os.path.join(dir_path, 'images_info.json'))
            has_images = any(
                f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'))
                for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))
            ) if os.path.exists(dir_path) else False
            
            # 如果没有任何内容，或者是空的/不完整的，删除它
            if not has_images_info and not has_images:
                try:
                    shutil.rmtree(dir_path)
                    deleted += 1
                except Exception as e:
                    errors.append(f"Failed to delete {dir_path}: {e}")
            else:
                kept += 1
    
    return {'deleted': deleted, 'kept': kept, 'errors': errors}


def cleanup_old_tmp_folders(base_dir=None, max_age_hours=24):
    """
    清理所有超过指定时间的 _tmp 文件夹（防止长时间残留）
    
    Args:
        base_dir: 要清理的基础目录
        max_age_hours: 最大保留时间（小时），默认24小时
    
    Returns:
        dict: 包含清理统计信息的字典
    """
    base = base_dir or "./images"
    
    if not os.path.exists(base):
        return {'deleted': 0, 'kept': 0, 'errors': []}
    
    deleted = 0
    kept = 0
    errors = []
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        entries = os.listdir(base)
    except Exception as e:
        return {'deleted': 0, 'kept': 0, 'errors': [str(e)]}
    
    for entry in entries:
        dir_path = os.path.join(base, entry)
        
        if not os.path.isdir(dir_path):
            continue
        
        if entry.endswith('_tmp'):
            try:
                mtime = os.path.getmtime(dir_path)
                age_seconds = now - mtime
                
                if age_seconds > max_age_seconds:
                    shutil.rmtree(dir_path)
                    deleted += 1
                else:
                    kept += 1
            except Exception as e:
                errors.append(f"Failed to process {dir_path}: {e}")
    
    return {'deleted': deleted, 'kept': kept, 'errors': errors}


# 如果使用 --info_file，自动使用 info_file 所在的目录作为 save_folder
if args.info_file:
    info_file_dir = os.path.dirname(os.path.abspath(args.info_file))
    save_folder = info_file_dir + os.sep
else:
    # 使用新的 get_save_folder 函数生成带 _tmp 后缀的文件夹
    save_folder = get_save_folder(args.query, "./images")

page_size = 16