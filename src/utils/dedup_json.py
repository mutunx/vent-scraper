#!/usr/bin/env python3
"""
Script to remove duplicate entries from jandan scraped data JSON files.
Identifies duplicates based on post ID and keeps only the first occurrence.
"""

import json
import os
import sys
from collections import defaultdict

def dedup_json_file(filepath):
    """
    Remove duplicate entries from a JSON file containing an array of posts.
    Identifies duplicates based on post ID.
    
    Args:
        filepath: Path to the JSON file to deduplicate
    
    Returns:
        Tuple of (number_of_original_entries, number_of_unique_entries)
    """
    print(f"Processing file: {filepath}")
    
    # Read the JSON data
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print("Error: Expected JSON file to contain an array")
        return None
    
    original_count = len(data)
    print(f"Original entry count: {original_count}")
    
    # Track unique post IDs
    seen_ids = set()
    unique_entries = []
    
    # Keep stats on duplicates
    duplicate_count = 0
    duplicate_ids = defaultdict(int)
    
    for item in data:
        # Get the post ID if it exists
        post_id = None
        if 'post' in item and isinstance(item['post'], dict) and 'id' in item['post']:
            post_id = item['post']['id']
        
        if post_id:
            if post_id in seen_ids:
                duplicate_count += 1
                duplicate_ids[post_id] += 1
                continue
            seen_ids.add(post_id)
            unique_entries.append(item)
        else:
            # If there's no post ID, just include it (these might be incomplete entries)
            unique_entries.append(item)
    
    # Write the deduplicated data back to the file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(unique_entries, f, ensure_ascii=False, indent=2)
    
    print(f"Removed {duplicate_count} duplicate entries")
    print(f"New entry count: {len(unique_entries)}")
    
    # Print some info about duplicates
    if duplicate_ids:
        print("\nTop duplicated entries:")
        sorted_dupes = sorted(duplicate_ids.items(), key=lambda x: x[1], reverse=True)
        for post_id, count in sorted_dupes[:10]:
            print(f"Post ID {post_id}: {count + 1} occurrences")
    
    return original_count, len(unique_entries)

def main():
    if len(sys.argv) < 2:
        print("Usage: python dedup_json.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    result = dedup_json_file(filepath)
    if result:
        original_count, unique_count = result
        print(f"\nSummary: Reduced entries from {original_count} to {unique_count}")
        print(f"Eliminated {original_count - unique_count} duplicates")

if __name__ == "__main__":
    main()