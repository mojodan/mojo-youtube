#!/usr/bin/env python3
"""
YouTube Video and Subtitle Downloader
Downloads YouTube videos with English subtitles using yt-dlp
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
import yaml

try:
    import yt_dlp
    from colorama import init, Fore, Style
except ImportError as e:
    print(f"Error: Missing required dependency - {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Initialize colorama for cross-platform color support
init(autoreset=True)


class YouTubeDownloader:
    """Main class for downloading YouTube videos and subtitles"""

    def __init__(self, config: Dict):
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """Configure logging based on verbosity setting"""
        log_level = logging.DEBUG if self.config.get('verbose') else logging.INFO
        log_format = '%(asctime)s - %(levelname)s - %(message)s'

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config.get('log_file', 'youtube_downloader.log')),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

    def get_subtitle_options(self) -> Dict:
        """Configure subtitle download options with English priority"""
        subtitle_langs = self.config.get('subtitle_languages', ['en'])

        return {
            'writesubtitles': True,
            'writeautomaticsub': True,  # Fallback to auto-generated
            'subtitleslangs': subtitle_langs,
            'subtitlesformat': self.config.get('subtitle_format', 'srt'),
            'skip_download': False,
        }

    def get_download_options(self, url: str) -> Dict:
        """Build yt-dlp options based on configuration"""
        output_dir = Path(self.config.get('output_dir', './downloads'))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Output template
        output_template = str(output_dir / '%(title)s.%(ext)s')
        if self.config.get('organize_by_channel'):
            output_template = str(output_dir / '%(uploader)s' / '%(title)s.%(ext)s')

        options = {
            'format': self.config.get('quality', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'),
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'writethumbnail': self.config.get('download_thumbnail', False),
            'writeinfojson': self.config.get('save_metadata', True),
            'no_warnings': not self.config.get('verbose'),
            'ignoreerrors': False,
            'retries': self.config.get('max_retries', 3),
            'fragment_retries': self.config.get('max_retries', 3),
            'quiet': self.config.get('quiet', False),
            'no_color': False,
        }

        # Add subtitle options
        options.update(self.get_subtitle_options())

        # Progress hooks
        if not self.config.get('quiet'):
            options['progress_hooks'] = [self.progress_hook]

        return options

    def progress_hook(self, d: Dict):
        """Display download progress"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            print(f"\r{Fore.CYAN}Downloading: {percent} at {speed} - ETA: {eta}", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\n{Fore.GREEN}Download completed, now processing...")

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL"""
        youtube_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
        return any(domain in url for domain in youtube_domains)

    def check_existing_download(self, url: str) -> Optional[str]:
        """Check if video was already downloaded"""
        if not self.config.get('skip_existing', True):
            return None

        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = self.sanitize_filename(info.get('title', 'video'))

                output_dir = Path(self.config.get('output_dir', './downloads'))
                if self.config.get('organize_by_channel'):
                    output_dir = output_dir / info.get('uploader', 'unknown')

                # Check for video file
                for ext in ['mp4', 'mkv', 'webm']:
                    video_path = output_dir / f"{title}.{ext}"
                    if video_path.exists():
                        return str(video_path)
        except Exception as e:
            self.logger.debug(f"Could not check for existing download: {e}")

        return None

    def download_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """Download video with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                existing_file = self.check_existing_download(url)
                if existing_file:
                    print(f"{Fore.YELLOW}Video already downloaded: {existing_file}")
                    return True

                options = self.get_download_options(url)

                with yt_dlp.YoutubeDL(options) as ydl:
                    print(f"{Fore.CYAN}Downloading video from: {url}")
                    info = ydl.extract_info(url, download=True)

                    # Report subtitle status
                    self.report_subtitle_status(info)

                    print(f"{Fore.GREEN}Successfully downloaded: {info.get('title', 'video')}")
                    return True

            except yt_dlp.utils.DownloadError as e:
                self.logger.error(f"Download error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"{Fore.YELLOW}Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"{Fore.RED}Failed to download after {max_retries} attempts")
                    return False
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return False

        return False

    def report_subtitle_status(self, info: Dict):
        """Report which subtitles were downloaded"""
        if not info:
            return

        requested_subtitles = info.get('requested_subtitles', {})

        if not requested_subtitles:
            print(f"{Fore.YELLOW}No subtitles available for this video")
            return

        for lang, sub_info in requested_subtitles.items():
            sub_type = "auto-generated" if sub_info.get('ext') == 'vtt' else "manual"
            print(f"{Fore.GREEN}Downloaded {lang} subtitles ({sub_type})")

    def download_playlist(self, url: str) -> bool:
        """Download all videos from a playlist"""
        print(f"{Fore.CYAN}Downloading playlist: {url}")

        options = self.get_download_options(url)
        options['ignoreerrors'] = True  # Continue on errors in playlist

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                playlist_info = ydl.extract_info(url, download=False)

                if 'entries' in playlist_info:
                    total_videos = len(list(playlist_info['entries']))
                    print(f"{Fore.CYAN}Found {total_videos} videos in playlist")

                    ydl.download([url])
                    print(f"{Fore.GREEN}Playlist download completed")
                    return True
                else:
                    # Single video, not a playlist
                    return self.download_with_retry(url)

        except Exception as e:
            self.logger.error(f"Playlist download error: {e}")
            return False

    def download(self, url: str) -> bool:
        """Main download method"""
        # Validate URL
        if not self.validate_url(url):
            print(f"{Fore.RED}Error: Invalid YouTube URL")
            return False

        # Check if URL is a playlist
        if 'playlist' in url or 'list=' in url:
            return self.download_playlist(url)
        else:
            return self.download_with_retry(url, self.config.get('max_retries', 3))


def load_config(config_file: Optional[str] = None) -> Dict:
    """Load configuration from file or use defaults"""
    default_config = {
        'output_dir': './downloads',
        'quality': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'subtitle_languages': ['en'],
        'subtitle_format': 'srt',
        'max_retries': 3,
        'organize_by_channel': False,
        'download_thumbnail': False,
        'save_metadata': True,
        'skip_existing': True,
        'verbose': False,
        'quiet': False,
        'log_file': 'youtube_downloader.log'
    }

    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load config file: {e}")
            print("Using default configuration")

    return default_config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Download YouTube videos with English subtitles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://youtube.com/watch?v=VIDEO_ID
  %(prog)s -o ./videos -q 720p https://youtube.com/watch?v=VIDEO_ID
  %(prog)s -c config.yaml https://youtube.com/playlist?list=PLAYLIST_ID
  %(prog)s --quality best --subs en,es https://youtube.com/watch?v=VIDEO_ID
        """
    )

    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('-o', '--output', help='Output directory (default: ./downloads)')
    parser.add_argument('-q', '--quality',
                       help='Video quality: best, 1080p, 720p, 480p, or custom format string')
    parser.add_argument('-s', '--subs', '--subtitles',
                       help='Subtitle languages (comma-separated, e.g., en,es). Default: en')
    parser.add_argument('-f', '--subtitle-format',
                       choices=['srt', 'vtt', 'json3'],
                       help='Subtitle format (default: srt)')
    parser.add_argument('-c', '--config', help='Path to config file (YAML)')
    parser.add_argument('--organize', action='store_true',
                       help='Organize downloads by channel name')
    parser.add_argument('--thumbnail', action='store_true',
                       help='Download video thumbnail')
    parser.add_argument('--no-metadata', action='store_true',
                       help='Do not save metadata JSON file')
    parser.add_argument('--retry', type=int, metavar='N',
                       help='Maximum number of retries (default: 3)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress output except errors')

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override config with command-line arguments
    if args.output:
        config['output_dir'] = args.output
    if args.quality:
        # Map common quality presets
        quality_map = {
            'best': 'bestvideo+bestaudio/best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        }
        config['quality'] = quality_map.get(args.quality, args.quality)
    if args.subs:
        config['subtitle_languages'] = [lang.strip() for lang in args.subs.split(',')]
    if args.subtitle_format:
        config['subtitle_format'] = args.subtitle_format
    if args.organize:
        config['organize_by_channel'] = True
    if args.thumbnail:
        config['download_thumbnail'] = True
    if args.no_metadata:
        config['save_metadata'] = False
    if args.retry:
        config['max_retries'] = args.retry
    if args.verbose:
        config['verbose'] = True
    if args.quiet:
        config['quiet'] = True

    # Create downloader and download
    downloader = YouTubeDownloader(config)
    success = downloader.download(args.url)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
