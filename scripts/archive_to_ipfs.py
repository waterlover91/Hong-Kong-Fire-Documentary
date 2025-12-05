#!/usr/bin/env python3
"""
Download content from URLs and upload to IPFS
"""
import json
import os
import subprocess
import requests
from pathlib import Path
import hashlib
import mimetypes
from urllib.parse import urlparse, urljoin
import yt_dlp

class IPFSUploader:
    def __init__(self):
        self.downloads_dir = Path('downloads')
        self.downloads_dir.mkdir(exist_ok=True)
        self.pinata_api_key = os.environ.get('PINATA_API_KEY')
        self.pinata_secret = os.environ.get('PINATA_SECRET_KEY')
        self.web3_token = os.environ.get('WEB3_STORAGE_TOKEN')
        
    def is_video_url(self, url):
        """Check if URL is a video platform"""
        video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com', 
                        'twitch.tv', 'facebook.com/watch', 'twitter.com', 'x.com']
        return any(domain in url.lower() for domain in video_domains)
    
    def download_video(self, url):
        """Download video using yt-dlp"""
        try:
            print(f"  Downloading video from {url}")
            
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            output_template = str(self.downloads_dir / f'{url_hash}.%(ext)s')
            
            ydl_opts = {
                'format': 'best[height<=720]',  # Limit to 720p to save space
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
            return Path(filename)
            
        except Exception as e:
            print(f"  Error downloading video: {e}")
            return None
    
    def download_webpage(self, url):
        """Download webpage and its assets"""
        try:
            print(f"  Downloading webpage from {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Generate filename from URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            
            # Determine file extension
            content_type = response.headers.get('content-type', '').split(';')[0]
            ext = mimetypes.guess_extension(content_type) or '.html'
            
            filename = self.downloads_dir / f'{url_hash}{ext}'
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            return filename
            
        except Exception as e:
            print(f"  Error downloading webpage: {e}")
            return None
    
    def upload_to_ipfs_local(self, file_path):
        """Upload file to local IPFS node"""
        try:
            result = subprocess.run(
                ['ipfs', 'add', '-Q', str(file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            cid = result.stdout.strip()
            return cid
        except subprocess.CalledProcessError as e:
            print(f"  Error uploading to IPFS: {e}")
            return None
    
    def upload_to_pinata(self, file_path, metadata=None):
        """Upload file to Pinata pinning service"""
        if not self.pinata_api_key or not self.pinata_secret:
            return None
            
        try:
            url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
            
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret
            }
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                
                if metadata:
                    data = {'pinataMetadata': json.dumps(metadata)}
                    response = requests.post(url, files=files, headers=headers, data=data)
                else:
                    response = requests.post(url, files=files, headers=headers)
            
            response.raise_for_status()
            result = response.json()
            return result['IpfsHash']
            
        except Exception as e:
            print(f"  Error uploading to Pinata: {e}")
            return None
    
    def upload_to_web3storage(self, file_path):
        """Upload file to Web3.Storage"""
        if not self.web3_token:
            return None
            
        try:
            url = "https://api.web3.storage/upload"
            
            headers = {
                'Authorization': f'Bearer {self.web3_token}'
            }
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                response = requests.post(url, files=files, headers=headers)
            
            response.raise_for_status()
            result = response.json()
            return result['cid']
            
        except Exception as e:
            print(f"  Error uploading to Web3.Storage: {e}")
            return None
    
    def process_link(self, link_data):
        """Download content and upload to IPFS"""
        url = link_data['url']
        print(f"\nProcessing: {url}")
        
        # Download content
        if self.is_video_url(url):
            file_path = self.download_video(url)
        else:
            file_path = self.download_webpage(url)
        
        if not file_path or not file_path.exists():
            return None
        
        print(f"  Downloaded to: {file_path}")
        print(f"  File size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Upload to IPFS (try multiple methods)
        cid = None
        
        # Try Pinata first if credentials available
        if self.pinata_api_key:
            metadata = {
                'name': file_path.name,
                'keyvalues': {
                    'original_url': url
                }
            }
            cid = self.upload_to_pinata(file_path, metadata)
            if cid:
                print(f"  Uploaded to Pinata: {cid}")
        
        # Try Web3.Storage if Pinata failed
        if not cid and self.web3_token:
            cid = self.upload_to_web3storage(file_path)
            if cid:
                print(f"  Uploaded to Web3.Storage: {cid}")
        
        # Fall back to local IPFS
        if not cid:
            cid = self.upload_to_ipfs_local(file_path)
            if cid:
                print(f"  Uploaded to local IPFS: {cid}")
        
        # Clean up downloaded file
        try:
            file_path.unlink()
        except:
            pass
        
        return cid

def main():
    # Load new links
    try:
        with open('new_links.json', 'r') as f:
            links = json.load(f)
    except FileNotFoundError:
        print("No new links to process")
        with open('ipfs_mappings.json', 'w') as f:
            json.dump([], f)
        return
    
    if not links:
        print("No new links to process")
        with open('ipfs_mappings.json', 'w') as f:
            json.dump([], f)
        return
    
    uploader = IPFSUploader()
    mappings = []
    
    for link in links:
        cid = uploader.process_link(link)
        
        if cid:
            mappings.append({
                'file': link['file'],
                'original_url': link['url'],
                'ipfs_cid': cid,
                'ipfs_url': f'https://ipfs.io/ipfs/{cid}',
                'text': link.get('text', ''),
                'type': link.get('type', 'markdown')
            })
    
    # Save mappings for next script
    with open('ipfs_mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)
    
    print(f"\n\nSuccessfully uploaded {len(mappings)} out of {len(links)} links to IPFS")

if __name__ == '__main__':
    main()