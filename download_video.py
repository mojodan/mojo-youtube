#!/usr/bin/env python3
"""
YouTube Video Downloader

This script downloads the highest quality YouTube video available using yt-dlp.
Usage: python download_video.py <YouTube_URL>
"""

import sys
import os
from pathlib import Path
import yt_dlp


def download_youtube_video(url):
    """
    Download a YouTube video in the highest quality available.
    
    Args:
        url (str): YouTube video URL
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    # Create downloads directory if it doesn't exist
    downloads_dir = Path(__file__).parent / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    
    # Configure yt-dlp options for highest quality
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Download best video and audio, merge if possible
        'outtmpl': str(downloads_dir / '%(title)s.%(ext)s'),  # Output template
        'merge_output_format': 'mp4',  # Prefer mp4 format after merging
        'quiet': False,  # Show download progress
        'no_warnings': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading video from: {url}")
            print(f"Saving to: {downloads_dir}")
            ydl.download([url])
            print("\nDownload completed successfully!")
            return True
    except Exception as e:
        print(f"\nError downloading video: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python download_video.py <YouTube_URL>")
        print("\nExample:")
        print("  python download_video.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL format: {url}")
        print("URL should start with http:// or https://")
        sys.exit(1)
    
    success = download_youtube_video(url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
