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

## Comparing Playlists / Detecting Missing Videos

### mySQL
yt-pao allows you to compare the latest reports of multiple playlists to identify which videos are missing from one playlist relative to another. This is useful if you want to track differences between playlists over time or across similar playlists.

The comparison works by selecting the latest reports for each playlist and then performing a set difference on the videos. For example, the following SQL snippet demonstrates how the database identifies videos present in Playlist `2` but missing in Playlist `19`, and vice versa:
```mysql
WITH params AS (
    SELECT 2 AS p1, 19 AS p2 -- Replace 2 and 19 with your playlist IDs
),
last_reports AS (
    SELECT r.playlist_id, r.report_id
    FROM ytp_reports r
    INNER JOIN (
        SELECT playlist_id, MAX(report_date) AS max_date
        FROM ytp_reports, params
        WHERE playlist_id IN (SELECT p1 FROM params UNION SELECT p2 FROM params)
        GROUP BY playlist_id
    ) latest
      ON r.playlist_id = latest.playlist_id
     AND r.report_date = latest.max_date
),
videos_in_playlists AS (
    SELECT rd.video_id, v.video_title, v.video_url, r.playlist_id
    FROM ytp_report_details rd
    JOIN ytp_reports r ON rd.report_id = r.report_id
    JOIN ytp_videos v ON rd.video_id = v.video_id
    WHERE r.report_id IN (SELECT report_id FROM last_reports)
)

-- Videos in Playlist p1 missing from p2
SELECT 
    v1.video_id,
    v1.video_title,
    v1.video_url,
    (SELECT p1 FROM params) AS playlist_source
FROM (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p1 FROM params)) v1
LEFT JOIN (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p2 FROM params)) v2
       ON v1.video_id = v2.video_id
WHERE v2.video_id IS NULL

UNION

-- Videos in Playlist p2 missing from p1
SELECT 
    v2.video_id,
    v2.video_title,
    v2.video_url,
    (SELECT p2 FROM params) AS playlist_source
FROM (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p2 FROM params)) v2
LEFT JOIN (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p1 FROM params)) v1
       ON v2.video_id = v1.video_id
WHERE v1.video_id IS NULL;

```

This feature essentially performs a diff between playlists, giving you a clear overview of which videos are unique to each playlist.

## Authors

- **Kordight** - [GitHub](https://github.com/Kordight)
