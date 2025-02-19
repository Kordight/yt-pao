# YT-PAO - YouTube Playlist Analyzer & Organizer

YT-PAO is a tool designed to analyze and organize YouTube playlists. It allows you to efficiently extract data from playlists, archive them, track removed videos, and export data in various formats.

## Features

- **Playlist Analysis**: Extract data from YouTube playlists, including titles, URLs, durations, uploaders, view counts, and availability status.
- **Multiple Output Formats**: Generate reports in `cmd`, `txt`, `json`, `csv`, `html`, or save to a MySQL database.
- **Work Modes**: Choose between different modes: `all` (all videos), `unavailable` (only unavailable videos), `available` (only available videos).
- **Archiving**: Create local copies of reports in the `Output` folder, organized by playlist name.

## Requirements

To run YT-PAO, you need Python 3.x and several external libraries. You can install them using:

```bash
pip install -r requirements.txt
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/YT-PAO.git
   ```
2. Navigate to the project directory:
   ```bash
   cd YT-PAO
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Basic usage of the program:

```bash
python3 main.py --playlistLink <playlist_link> --resultFormat <output_format> --listMode <work_mode>
```

### Flags

- `--playlistLink`: The link to the YouTube playlist (required).
- `--resultFormat`: The output format. Available options: `cmd`, `txt`, `json`, `csv`, `html`, `mySQL`.
- `--listMode`: The work mode. Available options: `all` (all videos), `unavailable` (only unavailable videos), `available` (only available videos).

### Examples

1. Display results in the console:
   ```bash
   python3 main.py --playlistLink https://www.youtube.com/playlist?list=PL1234567890 --resultFormat cmd --listMode all
   ```

2. Generate a report in JSON format:
   ```bash
   python3 main.py --playlistLink https://www.youtube.com/playlist?list=PL1234567890 --resultFormat json --listMode unavailable
   ```

3. Save the report to a MySQL database:
   ```bash
   python3 main.py --playlistLink https://www.youtube.com/playlist?list=PL1234567890 --resultFormat mySQL --listMode all
   ```

## File Structure

- `Output/`: Folder where reports are saved. Each playlist has its own subfolder named after the playlist.
- `web_template/`: HTML and CSS templates used for generating HTML reports.
- `config.yaml`: Configuration file containing MySQL database connection details.

## Authors

- **Kordight** - [GitHub](https://github.com/Kordight)