#!/usr/bin/env python3
"""
清理 Chrome 用户数据临时目录
删除所有 chrome_user_* 开头的目录
"""
import os
import shutil
import re
import time
from pathlib import Path

def cleanup_chrome_profiles(verbose=True):
    """删除所有 chrome_user_* 目录"""
    current_dir = os.getcwd()
    deleted_count = 0
    failed_dirs = []
    
    if verbose:
        print(f"扫描目录: {current_dir}")
        print(f"查找: chrome_user_* 目录...")
        print("-" * 60)
    
    # 扫描当前目录下的所有项
    try:
        items = os.listdir(current_dir)
    except Exception as e:
        if verbose:
            print(f"无法读取目录: {e}")
        return deleted_count, len(failed_dirs)
    
    # 找出所有匹配的目录
    chrome_dirs = [
        item for item in items 
        if os.path.isdir(os.path.join(current_dir, item)) and re.match(r'chrome_user_\w+', item)
    ]
    
    if not chrome_dirs:
        if verbose:
            print("未找到任何 chrome_user_* 目录")
        return 0, 0
    
    if verbose:
        print(f"找到 {len(chrome_dirs)} 个目录:")
        for dirname in sorted(chrome_dirs):
            print(f"  - {dirname}")
        print("-" * 60)
    
    # 删除每个目录，带重试机制
    for dirname in chrome_dirs:
        dir_path = os.path.join(current_dir, dirname)
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # 尝试删除目录中的所有文件/子目录
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path, ignore_errors=True)
                    # 再检查一次是否真的删除了
                    if not os.path.exists(dir_path):
                        if verbose:
                            print(f"✓ 已删除: {dirname}")
                        deleted_count += 1
                        break
                else:
                    deleted_count += 1
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    if verbose:
                        print(f"✗ 删除失败: {dirname} (尝试 {max_retries} 次)")
                    failed_dirs.append(dirname)
                    break
    
    if verbose:
        print("-" * 60)
        print(f"总计: 成功删除 {deleted_count} 个目录", end="")
        if failed_dirs:
            print(f", 失败 {len(failed_dirs)} 个")
            print(f"失败的目录: {', '.join(failed_dirs)}")
        else:
            print()
    
    return deleted_count, len(failed_dirs)

if __name__ == "__main__":
    cleanup_chrome_profiles(verbose=True)
