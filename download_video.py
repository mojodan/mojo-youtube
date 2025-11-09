#!/usr/bin/env python3
"""
YouTube Video Downloader

This script downloads the highest quality YouTube video available using yt-dlp.
Usage: python download_video.py <YouTube_URL>
"""

import sys
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
        'cookiefile': str(Path(__file__).parent / 'cookies.txt'),  # Use local cookies.txt
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading video from: {url}")
            print(f"Saving to: {downloads_dir}")
            ydl.download([url])
            print("\nDownload completed successfully!")
            return True
    except Exception as e:
        # If this is the _parse_browser_specification signature error, retry via CLI-style call
        err_str = str(e)
        if "_parse_browser_specification" in err_str:
            print("Warning: cookies-from-browser parsing failed in this yt-dlp build. Retrying via CLI flag...")
            try:
                # Call yt-dlp CLI entrypoint with the cookies flag to avoid the parser mismatch.
                # This returns an exit code: 0 on success.
                exit_code = yt_dlp.main([
                    '--cookies-from-browser', 'chrome',
                    '--cookiefile', str(Path(__file__).parent / 'cookies.txt'),
                    '--format', 'bestvideo+bestaudio/best',
                    '--merge-output-format', 'mp4',
                    '--no-warnings',
                    '--output', str(downloads_dir / '%(title)s.%(ext)s'),
                    url,
                ])
                if exit_code == 0:
                    print("\nDownload completed successfully (CLI fallback)!")
                    return True
            except Exception:
                pass

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
