import os
import sys
import json
import argparse
import subprocess
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
    Looks for a folder with pattern: timestamp_{topic_key} or any subfolder that matches.
    """
    if not os.path.exists(folder_path):
        return False
    
    # Get the base folder name (e.g., 'images' from 'images/')
    parent_dir = Path(folder_path).parent
    base_name = Path(folder_path).name
    
    # Check for folders with pattern: {timestamp}_{topic_key}
    pattern_prefix = f"_{topic_key}"
    try:
        for item in parent_dir.iterdir():
            if item.is_dir() and item.name.startswith('2') and item.name.endswith(pattern_prefix):
                # Check if it's a valid doodle folder (contains images or images_info.json)
                if (item / 'images_info.json').exists() or any(f.suffix in {'.jpg', '.jpeg', '.png', '.gif', '.webp'} for f in item.iterdir() if f.is_file()):
                    return True
    except Exception:
        pass
    
    return False

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
    
    if not doodles_script.exists():
        print(f"Error: doodles.py not found at {doodles_script}")
        sys.exit(1)
    
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
        # We need to determine the potential save folder path
        # The save folder is usually 'images/' by default (from utils/shared.py)
        # But we can't know exactly until doodles.py runs. We'll check the common pattern.
        potential_base_folder = base_dir / 'images'
        if is_already_downloaded(potential_base_folder, topic_key):
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