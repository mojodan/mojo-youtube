# mojo-youtube

A robust YouTube video downloader with automatic English subtitle extraction using yt-dlp.

## Features

- Download YouTube videos in high quality (up to 1080p/4K)
- Automatic English subtitle download with intelligent fallback
  - Prioritizes manual/community captions over auto-generated
  - Falls back to auto-generated subtitles when manual unavailable
  - Supports multiple subtitle languages
- **AI-powered transcription** using OpenAI's Whisper for highly accurate English subtitles
  - State-of-the-art speech recognition
  - Multiple model sizes for speed/accuracy tradeoff
  - GPU acceleration support
  - Generates accurate timestamps and text
- Smart retry logic with exponential backoff
- Playlist and channel download support
- Skip already downloaded videos
- Progress tracking and detailed logging
- Flexible configuration via CLI or config file
- Organize downloads by channel
- Download video metadata and thumbnails
- Cookie support for accessing age-restricted and members-only content

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/mojodan/mojo-youtube.git
cd mojo-youtube
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (optional, Linux/Mac):
```bash
chmod +x youtube_downloader.py
```

## Quick Start

Download a video with English subtitles:
```bash
python youtube_downloader.py "https://youtube.com/watch?v=VIDEO_ID"
```

The video and subtitles will be saved in the `./downloads` directory.

## Usage

### Basic Usage

```bash
python youtube_downloader.py [OPTIONS] URL
```

### Command-Line Options

```
positional arguments:
  url                   YouTube video or playlist URL

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory (default: ./downloads)
  -q QUALITY, --quality QUALITY
                        Video quality: best, 1080p, 720p, 480p, or custom format
  -s SUBS, --subs SUBS, --subtitles SUBS
                        Subtitle languages (comma-separated, e.g., en,es). Default: en
  -f {srt,vtt,json3}, --subtitle-format {srt,vtt,json3}
                        Subtitle format (default: srt)
  -c CONFIG, --config CONFIG
                        Path to config file (YAML)
  --cookies COOKIES     Path to cookies.txt file (Netscape format)
  --transcribe          Generate accurate English subtitles using Whisper AI
  --whisper-model {tiny,base,small,medium,large}
                        Whisper model size (default: base). Larger = more accurate but slower
  --organize            Organize downloads by channel name
  --thumbnail           Download video thumbnail
  --no-metadata         Do not save metadata JSON file
  --retry N             Maximum number of retries (default: 3)
  -v, --verbose         Enable verbose logging
  --quiet               Suppress output except errors
```

### Examples

#### Download a single video
```bash
python youtube_downloader.py "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

#### Download in 720p quality
```bash
python youtube_downloader.py -q 720p "https://youtube.com/watch?v=VIDEO_ID"
```

#### Download with custom output directory
```bash
python youtube_downloader.py -o ~/Videos/YouTube "https://youtube.com/watch?v=VIDEO_ID"
```

#### Download with English and Spanish subtitles
```bash
python youtube_downloader.py -s en,es "https://youtube.com/watch?v=VIDEO_ID"
```

#### Download entire playlist
```bash
python youtube_downloader.py "https://youtube.com/playlist?list=PLAYLIST_ID"
```

#### Download and organize by channel
```bash
python youtube_downloader.py --organize "https://youtube.com/watch?v=VIDEO_ID"
```

#### Download with thumbnail and custom retry count
```bash
python youtube_downloader.py --thumbnail --retry 5 "https://youtube.com/watch?v=VIDEO_ID"
```

#### Use configuration file
```bash
python youtube_downloader.py -c config.yaml "https://youtube.com/watch?v=VIDEO_ID"
```

#### Download age-restricted video with cookies
```bash
python youtube_downloader.py --cookies cookies.txt "https://youtube.com/watch?v=VIDEO_ID"
```

#### Generate AI transcription with Whisper
```bash
python youtube_downloader.py --transcribe "https://youtube.com/watch?v=VIDEO_ID"
```

#### Use larger Whisper model for maximum accuracy
```bash
python youtube_downloader.py --transcribe --whisper-model medium "https://youtube.com/watch?v=VIDEO_ID"
```

## Configuration File

For repeated use with consistent settings, create a configuration file:

1. Copy the example config:
```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` with your preferences:
```yaml
output_dir: ./downloads
quality: 720p
subtitle_languages:
  - en
  - es
organize_by_channel: true
download_thumbnail: true
```

3. Use the config file:
```bash
python youtube_downloader.py -c config.yaml "https://youtube.com/watch?v=VIDEO_ID"
```

## Subtitle Handling

The downloader implements intelligent subtitle handling:

1. **Priority**: Tries to download manual/community captions first
2. **Fallback**: If manual captions unavailable, downloads auto-generated
3. **Format**: Downloads in SRT format by default (most compatible)
4. **Languages**: Defaults to English but supports multiple languages
5. **Notification**: Reports which subtitle type was downloaded

## AI-Powered Transcription with Whisper

Generate highly accurate English subtitles using OpenAI's Whisper speech recognition model. This is ideal for:
- Videos without existing subtitles
- Improving accuracy of auto-generated captions
- Creating professional-quality transcriptions
- Podcasts and interviews with multiple speakers

### How It Works

The transcription feature:
1. Downloads the video
2. Extracts audio automatically
3. Uses Whisper AI to transcribe speech to text
4. Generates SRT subtitle file with accurate timestamps
5. Saves as `[video_title].whisper.srt`

### Whisper Model Sizes

Choose the right model for your needs:

| Model  | Size  | Speed       | Accuracy | Use Case |
|--------|-------|-------------|----------|----------|
| tiny   | 39M   | Very Fast   | Good     | Quick transcriptions, testing |
| base   | 74M   | Fast        | Better   | Default, balanced performance |
| small  | 244M  | Moderate    | Great    | High quality on CPU |
| medium | 769M  | Slow        | Excellent| Professional transcriptions |
| large  | 1550M | Very Slow   | Best     | Maximum accuracy needed |

**Recommendation**: Use `base` for most cases, `medium` for professional work, `small` if you have time constraints.

### GPU Acceleration

Whisper can utilize NVIDIA GPUs for significant speed improvements:
- **CPU**: 5-10x realtime (a 10-minute video takes 50-100 minutes)
- **GPU**: 1-2x realtime (a 10-minute video takes 10-20 minutes)

The downloader automatically detects and uses GPU if available (CUDA-enabled GPU + PyTorch with CUDA support).

### Installation for Transcription

Basic installation (CPU only):
```bash
pip install faster-whisper
```

For GPU acceleration (NVIDIA GPUs):
```bash
pip install faster-whisper torch --index-url https://download.pytorch.org/whl/cu118
```

### Usage Examples

**Basic transcription:**
```bash
python youtube_downloader.py --transcribe "https://youtube.com/watch?v=VIDEO_ID"
```

**High-accuracy transcription:**
```bash
python youtube_downloader.py --transcribe --whisper-model medium "https://youtube.com/watch?v=VIDEO_ID"
```

**Enable in config file:**
```yaml
transcribe: true
whisper_model: base
whisper_device: auto  # Uses GPU if available
```

### Output Files

When transcription is enabled, you'll get:
- `video_title.mp4` - The video file
- `video_title.en.srt` - YouTube's subtitles (if available)
- `video_title.whisper.srt` - AI-generated transcription

### Transcription Tips

1. **Start with base model**: It provides good accuracy and reasonable speed
2. **Use GPU if available**: 5-10x faster than CPU
3. **Try medium for important content**: Noticeable accuracy improvement
4. **Larger models need more RAM**: Ensure you have enough system memory
5. **Processing time varies**: Depends on video length, model size, and hardware

## Using Cookies for Restricted Content

Some videos require authentication to access:
- Age-restricted content
- Members-only videos
- Region-locked content
- Private/unlisted videos requiring account access

To download these videos, you need to provide browser cookies in Netscape format.

### Exporting Cookies from Your Browser

1. **Install a browser extension**:
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Export cookies**:
   - Log in to YouTube in your browser
   - Navigate to YouTube.com
   - Click the extension icon
   - Click "Export" to save as `cookies.txt`

3. **Use cookies with the downloader**:
```bash
python youtube_downloader.py --cookies cookies.txt "https://youtube.com/watch?v=VIDEO_ID"
```

**Security Note**: Keep your `cookies.txt` file secure. It contains authentication tokens that grant access to your YouTube account. Never share or commit this file to version control (it's excluded in `.gitignore`).

## Quality Options

Available quality presets:
- `best`: Best available quality (default)
- `1080p`: Full HD (1920x1080)
- `720p`: HD (1280x720)
- `480p`: SD (854x480)

You can also use custom yt-dlp format strings for advanced control.

## File Organization

Downloaded files are organized as follows:

### Default structure:
```
downloads/
├── Video Title 1.mp4
├── Video Title 1.en.srt
├── Video Title 1.info.json
├── Video Title 2.mp4
└── Video Title 2.en.srt
```

### With `--organize` flag:
```
downloads/
├── Channel Name 1/
│   ├── Video Title 1.mp4
│   ├── Video Title 1.en.srt
│   └── Video Title 1.info.json
└── Channel Name 2/
    ├── Video Title 2.mp4
    └── Video Title 2.en.srt
```

## Error Handling

The downloader includes robust error handling:

- **Automatic retries**: Failed downloads retry up to 3 times (configurable)
- **Exponential backoff**: Waits 1s, 2s, 4s between retries
- **URL validation**: Checks for valid YouTube URLs before attempting download
- **Duplicate detection**: Skips already downloaded videos by default
- **Detailed logging**: All errors logged to `youtube_downloader.log`

## Logging

Logs are written to `youtube_downloader.log` by default. Use `-v` for verbose output:

```bash
python youtube_downloader.py -v "https://youtube.com/watch?v=VIDEO_ID"
```

## Troubleshooting

### Video download fails
- Check your internet connection
- Verify the YouTube URL is accessible
- Try updating yt-dlp: `pip install --upgrade yt-dlp`
- Use `--retry` to increase retry attempts

### Age-restricted or members-only video fails
- Export fresh cookies from your browser (cookies expire)
- Ensure you're logged in to YouTube when exporting cookies
- Use the `--cookies` option with the path to your cookies.txt file
- Verify the cookies.txt file is in Netscape format

### No subtitles downloaded
- Not all videos have subtitles available
- Check the video on YouTube to confirm subtitles exist
- Try requesting auto-generated subtitles explicitly

### Permission errors
- Ensure you have write permissions to the output directory
- Try using a different output directory with `-o`

### Transcription fails or is very slow
- Install faster-whisper: `pip install faster-whisper`
- For GPU acceleration: Install PyTorch with CUDA support
- Start with a smaller model (tiny or base) to test
- Check available RAM - larger models need more memory
- Ensure video file downloaded successfully before transcription

### Import errors
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (requires 3.7+)

## Advanced Usage

### Custom yt-dlp Format Strings

For advanced users, you can specify custom format strings:

```bash
python youtube_downloader.py -q "bestvideo[height<=1080][fps<=30]+bestaudio/best" URL
```

### Batch Downloads

Create a file with URLs (one per line) and use a script:

```bash
while read url; do
    python youtube_downloader.py "$url"
done < urls.txt
```

## Dependencies

- **yt-dlp**: Modern YouTube downloader (fork of youtube-dl)
- **requests**: HTTP library
- **tqdm**: Progress bar library
- **pyyaml**: YAML configuration parser
- **colorama**: Cross-platform colored terminal output
- **faster-whisper**: (Optional) AI transcription using OpenAI's Whisper model

## License

[Your chosen license]

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Inspired by the need for reliable YouTube archival with subtitles

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review existing issues on GitHub
- Create a new issue with details about your problem
