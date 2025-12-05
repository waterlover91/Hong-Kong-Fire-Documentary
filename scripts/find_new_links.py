#!/usr/bin/env python3
"""
Find new links in modified markdown files
"""
import re
import subprocess
import json
import os
from pathlib import Path
import glob

content_dir = 'content'

def get_modified_files():
    """Get list of modified markdown files in the last commit"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        files = [f for f in result.stdout.strip().split('\n') if f.endswith('.md') and f.startswith('docs/')]
        return files
    except subprocess.CalledProcessError:
        # If it's the first commit, get all files
        return list(Path(content_dir).rglob('*.md'))

def get_all_md():
    """Get list of all markdown files in the repo (only use this for init!)
    """
    docs_path = Path(content_dir)
    
    if not docs_path.exists():
        print(f"Warning: {content_dir} directory not found")
        return []
    
    # Recursively find all .md files in docs/
    md_files = list(docs_path.rglob('*.md'))
    md_files = [str(f) for f in md_files]
    
    return md_files

def extract_links(file_path):
    """Extract all URLs from a markdown file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match markdown links [text](url) and plain URLs
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
    plain_urls = re.findall(r'(?<!\()(https?://[^\s\)]+)(?!\))', content)
    
    links = []
    
    # markdown links
    for text, url in markdown_links:
        if url.startswith('http'):
            links.append({
                'url': url,
                'text': text,
                'type': 'markdown'
            })
    
    # plain URLs 
    markdown_urls = [url for _, url in markdown_links]
    for url in plain_urls:
        if url not in markdown_urls:
            links.append({
                'url': url,
                'text': '',
                'type': 'plain'
            })
    
    return links

def filter_new_links(file_path, current_links):
    """Compare current links with previous version to find new ones"""
    try:
        result = subprocess.run(
            ['git', 'show', f'HEAD~1:{file_path}'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # File is new, all links are new
            return current_links
        
        old_content = result.stdout
        old_urls = re.findall(r'https?://[^\s\)]+', old_content)
        
        # Filter out links that already existed
        new_links = [link for link in current_links if link['url'] not in old_urls]
        return new_links
        
    except Exception as e:
        print(f"Error comparing versions: {e}")
        return current_links

def main():
    modified_files = get_modified_files()
    
    if not modified_files:
        print("No modified markdown files found")
        with open('new_links.json', 'w') as f:
            json.dump([], f)
        return
    
    all_new_links = []
    
    for file_path in modified_files:
        if not os.path.exists(file_path):
            continue
            
        print(f"Scanning {file_path}")
        current_links = extract_links(file_path)
        # new_links = filter_new_links(file_path, current_links)
        new_links = current_links
        
        for link in new_links:
            link['file'] = file_path
            all_new_links.append(link)
        
        print(f"  Found {len(new_links)} new link(s)")
    
    # Save to JSON for next script
    with open('new_links.json', 'w') as f:
        json.dump(all_new_links, f, indent=2)
    print(all_new_links[:10])
    
    print(f"\nTotal new links found: {len(all_new_links)}")
    
    # Output for GitHub Actions
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
        f.write(f"link_count={len(all_new_links)}\n")

if __name__ == '__main__':
    main()