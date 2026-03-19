import os
import sys
import json
import argparse
import subprocess
import re
import shutil
from datetime import datetime
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description='Batch download doodles for multiple topics')
    parser.add_argument('--type', type=str, default='topic',
                        help='Type of batch download (currently only "topic" is supported)')
    return parser.parse_args()

def load_topics():
    """Load topics from topics.json"""
    topics_file = Path(__file__).parent / 'topics.json'
    if not topics_file.exists():
        print(f"Error: topics.json not found at {topics_file}")
        sys.exit(1)
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics = json.load(f)
    
    return topics

def is_already_downloaded(folder_path, topic_key):
    """
    Check if a topic has already been downloaded.
    Looks for a folder with pattern: {timestamp}_{topic_key} where timestamp is 14 consecutive digits (YYYYMMDDHHMMSS).
    """
    if not os.path.exists(folder_path):
        return False
    
    # Get the parent directory of the base folder
    parent_dir = Path(folder_path).parent
    
    # Build regex pattern: 14 digits followed by underscore and topic_key
    # Escape topic_key for regex
    escaped_key = re.escape(topic_key)
    pattern = re.compile(rf'^\d{{14}}_{escaped_key}$')
    
    try:
        for item in parent_dir.iterdir():
            if item.is_dir():
                # Check if name matches the pattern
                if pattern.match(item.name):
                    # Check if it's a valid doodle folder (contains images or images_info.json)
                    if (item / 'images_info.json').exists() or any(f.suffix in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'} for f in item.iterdir() if f.is_file()):
                        return True
    except Exception:
        pass
    
    return False

def cleanup_invalid_folders(images_folder, topics):
    """
    Delete directories that look like timestamped folders but are invalid.
    Scans: (1) parent of images_folder for timestamped folders, and (2) images_folder itself if it exists.
    Never deletes the 'images' folder or any valid doodle folders.
    """
    base_dir = Path(__file__).parent
    deleted = 0
    kept = 0
    
    # Precompile regex for valid doodle folders
    topic_keys = list(topics.keys())
    valid_patterns = {}
    for key in topic_keys:
        escaped_key = re.escape(key)
        valid_patterns[key] = re.compile(rf'^\d{{14}}_{escaped_key}$')
    
    def scan_and_clean(directory, is_nested=False):
        nonlocal deleted, kept
        if not directory.exists():
            return
        
        dir_name = directory.name
        
        # Check if directory name starts with 14 digits (timestamp format)
        if re.match(r'^\d{14}', dir_name):
            # This is a timestamped folder - check if valid
            is_valid = False
            for key, pattern in valid_patterns.items():
                if pattern.match(dir_name):
                    # Verify content
                    if (directory / 'images_info.json').exists() or any(f.suffix in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'} for f in directory.iterdir() if f.is_file()):
                        is_valid = True
                        break
            
            if is_valid:
                kept += 1
            else:
                # Delete the invalid folder
                try:
                    shutil.rmtree(directory)
                    print(f"  Deleted invalid folder: {directory}")
                    deleted += 1
                except Exception as e:
                    print(f"  Failed to delete {directory}: {e}")
            return  # Don't recurse into a timestamped folder (it's either kept or deleted)
        
        # If not a timestamped folder, and it's a directory, scan its contents
        # But skip 'images' folder at top level from being deleted (we still recurse into it)
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    # At top level, skip the 'images' folder itself from deletion, but still recurse into it
                    if not is_nested and item.name == 'images':
                        scan_and_clean(item, is_nested=True)  # Recurse into images but don't delete it
                    else:
                        scan_and_clean(item, is_nested=False)
        except Exception:
            pass
    
    # Determine where to start scanning
    if images_folder.exists():
        print(f"Cleaning up: scanning {images_folder.parent} and {images_folder}")
        # Scan the parent directory (where renamed folders live)
        scan_and_clean(images_folder.parent, is_nested=False)
        # Also scan inside images folder itself (in case there are nested timestamped subfolders)
        scan_and_clean(images_folder, is_nested=False)
    else:
        # If images doesn't exist, scan the project directory
        parent_dir = base_dir
        print(f"Images folder not found, scanning project directory: {parent_dir}")
        scan_and_clean(parent_dir, is_nested=False)
    
    print(f"Cleanup: {deleted} invalid timestamped folders deleted, {kept} valid folders kept")
    print("="*60)

def main():
    args = parse_args()
    
    if args.type != 'topic':
        print(f"Error: Unsupported type '{args.type}'. Currently only 'topic' is supported.")
        sys.exit(1)
    
    # Load topics
    topics = load_topics()
    total_topics = len(topics)
    
    print(f"Found {total_topics} topics to process")
    print("="*60)
    
    # Get the directory where bunch.py is located
    base_dir = Path(__file__).parent
    doodles_script = base_dir / 'doodles.py'
    images_folder = base_dir / 'images'
    
    if not doodles_script.exists():
        print(f"Error: doodles.py not found at {doodles_script}")
        sys.exit(1)
    
    # Perform cleanup before starting batch
    cleanup_invalid_folders(images_folder, topics)
    
    # Track statistics
    skipped = 0
    completed = 0
    
    # Iterate through topics (English keys)
    for idx, topic_key in enumerate(topics.keys(), 1):
        topic_chinese = topics[topic_key]
        print(f"\n[{idx}/{total_topics}] Processing: {topic_key} ({topic_chinese})")
        
        # Construct query
        query = f"topic_tags={topic_key}"
        
        # Check if already downloaded
        if is_already_downloaded(images_folder, topic_key):
            print(f"  ⏭️  Skipping: Already downloaded (found existing folder with keyword '{topic_key}')")
            skipped += 1
            continue
        
        # Execute: python doodles.py --query={query}
        cmd = [sys.executable, str(doodles_script), '--query', query]
        
        print(f"  Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, cwd=base_dir, check=False)
            
            if result.returncode == 0:
                print(f"  ✅ Completed: {topic_key}")
                completed += 1
            else:
                print(f"  ❌ Failed with exit code {result.returncode}")
                # Continue with next topic even if this one fails
        except Exception as e:
            print(f"  ❌ Error executing command: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"Batch processing complete!")
    print(f"  Total topics: {total_topics}")
    print(f"  Skipped (already downloaded): {skipped}")
    print(f"  Completed this run: {completed}")
    print("="*60)

if __name__ == "__main__":
    main()