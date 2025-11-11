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

# Optional: Whisper for transcription
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None

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

        # Add cookies file if specified
        cookies_file = self.config.get('cookies_file')
        if cookies_file:
            cookies_path = Path(cookies_file)
            if cookies_path.exists():
                options['cookiefile'] = str(cookies_path)
                self.logger.info(f"Using cookies from: {cookies_path}")
            else:
                self.logger.warning(f"Cookies file not found: {cookies_path}")
                print(f"{Fore.YELLOW}Warning: Cookies file not found: {cookies_path}")

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

                    # Transcribe video if enabled
                    if self.config.get('transcribe', False):
                        video_path = self.get_video_path(info)
                        if video_path:
                            self.transcribe_video(video_path, info)
                        else:
                            self.logger.warning("Could not find video file for transcription")

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

    def format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt(self, segments: List, output_path: Path) -> bool:
        """Generate SRT subtitle file from Whisper segments"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, start=1):
                    start_time = self.format_timestamp(segment.start)
                    end_time = self.format_timestamp(segment.end)
                    text = segment.text.strip()

                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
            return True
        except Exception as e:
            self.logger.error(f"Error generating SRT file: {e}")
            return False

    def transcribe_video(self, video_path: Path, info: Dict) -> bool:
        """Transcribe video using Whisper and generate accurate English subtitles"""
        if not WHISPER_AVAILABLE:
            print(f"{Fore.YELLOW}Whisper not available. Install with: pip install faster-whisper")
            self.logger.warning("Transcription skipped: faster-whisper not installed")
            return False

        if not video_path.exists():
            self.logger.error(f"Video file not found: {video_path}")
            return False

        try:
            # Determine subtitle output path
            subtitle_path = video_path.with_suffix('.whisper.srt')

            print(f"{Fore.CYAN}Starting transcription with Whisper...")
            print(f"{Fore.CYAN}This may take a few minutes depending on video length...")

            # Load Whisper model
            model_size = self.config.get('whisper_model', 'base')
            device = self.config.get('whisper_device', 'auto')
            compute_type = self.config.get('whisper_compute_type', 'default')

            # Map 'auto' and 'default' to appropriate values
            if device == 'auto':
                device = 'cuda' if self._cuda_available() else 'cpu'
            if compute_type == 'default':
                compute_type = 'float16' if device == 'cuda' else 'int8'

            self.logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")
            print(f"{Fore.CYAN}Loading Whisper model: {model_size}")

            model = WhisperModel(model_size, device=device, compute_type=compute_type)

            # Transcribe audio
            self.logger.info(f"Transcribing: {video_path}")
            segments, info_whisper = model.transcribe(
                str(video_path),
                language='en',
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            # Convert generator to list and generate SRT
            segments_list = list(segments)

            if not segments_list:
                print(f"{Fore.YELLOW}No speech detected in video")
                self.logger.warning("Transcription produced no segments")
                return False

            # Generate SRT file
            if self.generate_srt(segments_list, subtitle_path):
                print(f"{Fore.GREEN}Generated accurate English subtitles: {subtitle_path.name}")
                self.logger.info(f"Transcription completed: {subtitle_path}")

                # Log transcription details
                duration = info_whisper.duration
                num_segments = len(segments_list)
                print(f"{Fore.GREEN}Transcribed {duration:.1f} seconds in {num_segments} segments")

                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            print(f"{Fore.RED}Transcription failed: {e}")
            return False

    def _cuda_available(self) -> bool:
        """Check if CUDA is available for GPU acceleration"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def get_video_path(self, info: Dict) -> Optional[Path]:
        """Get the path to the downloaded video file"""
        title = self.sanitize_filename(info.get('title', 'video'))
        output_dir = Path(self.config.get('output_dir', './downloads'))

        if self.config.get('organize_by_channel'):
            output_dir = output_dir / info.get('uploader', 'unknown')

        # Check for video file with common extensions
        for ext in ['mp4', 'mkv', 'webm']:
            video_path = output_dir / f"{title}.{ext}"
            if video_path.exists():
                return video_path

        return None

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
        'cookies_file': None,
        'transcribe': False,
        'whisper_model': 'base',
        'whisper_device': 'auto',
        'whisper_compute_type': 'default',
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
  %(prog)s --cookies cookies.txt https://youtube.com/watch?v=VIDEO_ID
  %(prog)s --transcribe https://youtube.com/watch?v=VIDEO_ID
  %(prog)s --transcribe --whisper-model medium https://youtube.com/watch?v=VIDEO_ID
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
    parser.add_argument('--cookies', help='Path to cookies.txt file (Netscape format)')
    parser.add_argument('--transcribe', action='store_true',
                       help='Generate accurate English subtitles using Whisper AI')
    parser.add_argument('--whisper-model',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size (default: base). Larger = more accurate but slower')
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
    if args.cookies:
        config['cookies_file'] = args.cookies
    if args.transcribe:
        config['transcribe'] = True
    if args.whisper_model:
        config['whisper_model'] = args.whisper_model
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
