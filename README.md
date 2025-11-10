# mojo-youtube
Download and transcribe YouTube videos

## Overview
This project provides a simple Python script to download the highest quality YouTube videos available using the `yt-dlp` library.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mojodan/mojo-youtube.git
cd mojo-youtube
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Download a YouTube video by providing its URL:

```bash
python download_video.py <YouTube_URL>
```

### Example:
```bash
python download_video.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

The video will be downloaded to the `downloads/` folder in the project directory.

## Features

- Downloads the highest quality video available
- Automatically merges best video and audio streams
- Outputs to MP4 format when possible
- Creates a `downloads/` folder automatically
- Shows download progress

## Requirements

- Python 3.6+
- yt-dlp (installed via requirements.txt)
