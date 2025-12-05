#!/usr/bin/env python3
"""
Update markdown files with IPFS links
"""
import json
import re
from pathlib import Path

def update_markdown_file(file_path, mappings):
    """Update a markdown file with IPFS links"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    updates_made = 0
    
    for mapping in mappings:
        original_url = mapping['original_url']
        ipfs_url = mapping['ipfs_url']
        cid = mapping['ipfs_cid']
        link_type = mapping.get('type', 'markdown')
        
        if link_type == 'markdown':
            # Handle markdown links [text](url)
            # Replace or append IPFS link
            pattern = re.escape(f"]({original_url})")
            
            # Option 1: Append IPFS link (keeps both)
            replacement = f"]({original_url}) ([IPFS]({ipfs_url}))"
            
            # Option 2: Replace with IPFS link (uncomment to use)
            # replacement = f"]({ipfs_url})"
            
            new_content = re.sub(pattern, replacement, content)
            
            if new_content != content:
                content = new_content
                updates_made += 1
        else:
            # Handle plain URLs
            # Make sure we don't replace URLs that are already in markdown links
            # by using negative lookbehind for ](
            pattern = f"(?<!\\]\\()({re.escape(original_url)})(?!\\))"
            
            # Option 1: Append IPFS link
            replacement = f"{original_url} ([IPFS]({ipfs_url}))"
            
            # Option 2: Replace with IPFS link (uncomment to use)
            # replacement = f"[{original_url}]({ipfs_url})"
            
            new_content = re.sub(pattern, replacement, content)
            
            if new_content != content:
                content = new_content
                updates_made += 1
    
    # Write back if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}: {updates_made} link(s)")
        return updates_made
    
    return 0

def main():
    # Load IPFS mappings
    try:
        with open('ipfs_mappings.json', 'r') as f:
            all_mappings = json.load(f)
    except FileNotFoundError:
        print("No IPFS mappings found")
        return
    
    if not all_mappings:
        print("No IPFS mappings to process")
        return
    
    # Group mappings by file
    files_to_update = {}
    for mapping in all_mappings:
        file_path = mapping['file']
        if file_path not in files_to_update:
            files_to_update[file_path] = []
        files_to_update[file_path].append(mapping)
    
    # Update each file
    total_updates = 0
    for file_path, mappings in files_to_update.items():
        if Path(file_path).exists():
            updates = update_markdown_file(file_path, mappings)
            total_updates += updates
    
    print(f"\nTotal updates made: {total_updates}")

if __name__ == '__main__':
    main()