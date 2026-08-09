import argparse
import re
import sys
from ytdlp_parser import parse_playlist, calculate_total_duration
import os
from datetime import datetime
import yaml
from mySQL_manager import repair_missing_video_thumbnails_for_report, create_cursor
from report_dispatcher import generate_reports_for_formats

def process_playlist_URL(playlist_URL):
    pattern = r'(?:list=)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, playlist_URL)
    if match:
        playlist_id = match.group(1)
        return f'https://www.youtube.com/playlist?list={playlist_id}'
    
    print("Error: URL is not YouTube playlist URL!", file=sys.stderr)
    sys.exit(1)

def get_playlist_id(playlist_URL):
    pattern = r'(?:list=)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, playlist_URL)
    if match:
        return match.group(1)
    else:
        print("Error: Unable to extract playlist ID from URL!", file=sys.stderr)
        sys.exit(1)

def parse_args():
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Interpretation of flags and YouTube playlist link.")

    # Define flags
    parser.add_argument('--playlistLink', type=str, required=False, help="The YouTube playlist link.")
    parser.add_argument('--resultFormats', nargs='+', required=False, choices=['cmd', 'txt', 'json', 'mySQL', 'csv', 'html'],
                        help="The report formats. Available options: cmd, txt, json, mySQL, csv, html.")
    parser.add_argument('--resultFormat', type=str, required=False, choices=['cmd', 'txt', 'json', 'mySQL', 'csv', 'html'],
                        help="Compatibility alias for a single report format.")
    parser.add_argument('--listMode', type=str, required=False, choices=['all', 'unavailable', 'available'],
                        help="The work mode. Available options: all, unavailable, available.")
    parser.add_argument('--repair-thumbnails', action='store_true', help="Scan and repair missing thumbnail files for a report.")
    parser.add_argument('--report-id', type=int, required=False, help="Report ID for thumbnail repair scan.")
    args = parser.parse_args()
    
    if args.repair_thumbnails:
        if args.report_id is None:
            parser.error("--report-id is required with --repair-thumbnails")
    else:
        if not args.playlistLink or not (args.resultFormats or args.resultFormat) or not args.listMode:
            parser.error("--playlistLink, --resultFormats/--resultFormat, and --listMode are required unless using --repair-thumbnails")
    
    # Return parsed arguments
    return args

def generate_config_file():
    if not os.path.exists('config.yaml'):
            print("Config file not found. Creating a new one with default settings.")
            config = {
        'database': {
            'host': 'localhost',
            'user': 'yt-pao',
            'password': 'password',
            'database': 'yt_pao_db'
        }
        }
            with open('config.yaml', 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

def load_db_config():
    # Load defaults from config file if present, then override with environment variables
    cfg = {}
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as file:
            loaded = yaml.safe_load(file) or {}
            cfg = loaded.get('database', {})

    # Environment overrides (allow using external DB or containerized DB)
    env_host = os.environ.get('DB_HOST')
    env_port = os.environ.get('DB_PORT')
    env_user = os.environ.get('DB_USER')
    env_password = os.environ.get('DB_PASSWORD')
    env_name = os.environ.get('DB_NAME')

    if env_host:
        cfg['host'] = env_host
    if env_port:
        cfg['port'] = env_port
    if env_user:
        cfg['user'] = env_user
    if env_password:
        cfg['password'] = env_password
    if env_name:
        cfg['database'] = env_name

    # sensible defaults
    cfg.setdefault('host', 'localhost')
    cfg.setdefault('user', 'yt-pao')
    cfg.setdefault('password', 'password')
    cfg.setdefault('database', 'yt_pao_db')

    return cfg

def main():
    generate_config_file()
    args = parse_args()
    
    # Handle --repair-thumbnails option
    if args.repair_thumbnails:
        db_config = load_db_config()
        db_host = db_config.get('host', 'localhost')
        db_user = db_config.get('user', 'yt-pao')
        db_password = db_config.get('password', 'password')
        db_name = db_config.get('database', 'yt_pao_db')
        db_port = int(db_config.get('port', 3306) or 3306)
        
        cursor, connection = create_cursor(db_host, db_user, db_password, db_name, db_port)
        if not cursor or not connection:
            print("[CLI] Failed to connect to database.", file=sys.stderr)
            return

        try:
            print(f"[CLI] Starting thumbnail repair scan for report_id={args.report_id}...")
            repaired, skipped = repair_missing_video_thumbnails_for_report(cursor, args.report_id)
            connection.commit()
            print(f"[CLI] Repair complete: total={repaired + skipped}, repaired={repaired}, skipped={skipped}")
        finally:
            cursor.close()
            connection.close()
        return
    
    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    playlist_data, videos = parse_playlist(process_playlist_URL(args.playlistLink), args.listMode)
    playlist_name = playlist_data['playlist_name']
    playlist_description = playlist_data['description']
    playlist_privacy = playlist_data['playlist_privacy']
    playlist_thumbnail = playlist_data.get('playlist_thumbnail', None)
    playlist_author = playlist_data.get('uploader', None)
    playlist_author_url = playlist_data.get('uploader_url', None)
    folder_path = f"Output/{playlist_name}_{get_playlist_id(playlist_data['url'])}"
    print(f"YouTube playlist link: {args.playlistLink}")
    selected_formats = args.resultFormats or ([args.resultFormat] if args.resultFormat else [])
    print(f"Report formats: {', '.join(selected_formats)}")
    print(f"List mode: {args.listMode}")
    if len(videos) == 0:
        print("No videos found in the playlist.")
        sys.exit(1)

    db_config = load_db_config()
    report_result = generate_reports_for_formats(
        formats=selected_formats,
        playlist_data=playlist_data,
        videos=videos,
        list_mode=args.listMode,
        playlist_link=args.playlistLink,
        calculate_total_duration=calculate_total_duration,
        db_config=db_config,
        output_folder=folder_path,
        date_time=date_time,
    )

    for report_format, result in report_result['results'].items():
        if result.get('status') == 'success':
            if report_format == 'cmd':
                print("Playlist Data:\n")
                print(result['playlist_table'])
                print("\nVideo Data:\n")
                print(result['video_table'])
            elif report_format == 'mySQL':
                print("Report saved to MySQL database.")
            else:
                print(f"Saved .{report_format} report to: {result.get('file_path')}")
        else:
            print(f"Failed to generate {report_format} report: {result.get('error')}", file=sys.stderr)

if __name__ == "__main__":
    main()
