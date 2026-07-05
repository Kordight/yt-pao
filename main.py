import argparse
from html import parser
import re
import sys
from ytdlp_parser import parse_playlist, calculate_total_duration
import os
from datetime import datetime
import yaml
from html_manager import generate_html_list, read_html_template, extract_head_and_body, generate_html_list_invalid_videos
from mySQL_manager import add_report, create_database, repair_missing_video_thumbnails_for_report, create_cursor

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
    parser.add_argument('--resultFormat', type=str, required=False, choices=['cmd', 'txt', 'json', 'mySQL', 'csv', 'html'],
                        help="The report format. Available options: cmd, txt, json, mySQL, csv, html.")
    parser.add_argument('--listMode', type=str, required=False, choices=['all', 'unavailable', 'available'],
                        help="The work mode. Available options: all, unavailable, available.")
    parser.add_argument('--repair-thumbnails', action='store_true', help="Scan and repair missing thumbnail files for a report.")
    parser.add_argument('--report-id', type=int, required=False, help="Report ID for thumbnail repair scan.")
    args = parser.parse_args()
    
    if args.repair_thumbnails:
        if args.report_id is None:
            parser.error("--report-id is required with --repair-thumbnails")
    else:
        if not args.playlistLink or not args.resultFormat or not args.listMode:
            parser.error("--playlistLink, --resultFormat, and --listMode are required unless using --repair-thumbnails")
    
    # Return parsed arguments
    return args

def format_table(headers, rows):
    column_widths = [max(len(str(cell)) for cell in col) for col in zip(headers, *rows)]
    header_row = " | ".join(f"{header:{width}}" for header, width in zip(headers, column_widths))
    separator = "-+-".join("-" * width for width in column_widths)
    data_rows = "\n".join(
        " | ".join(f"{str(cell):{width}}" for cell, width in zip(row, column_widths)) for row in rows
    )
    return f"{header_row}\n{separator}\n{data_rows}"

def compose_text_table(playlist_data, videos):
    # Use playlist_duration from playlist_data if available
    total_duration_str = calculate_total_duration(playlist_data)
    # Copy playlist_data to avoid mutating the original
    playlist_data_display = dict(playlist_data)
    playlist_data_display["Total Duration"] = total_duration_str

    playlist_headers = ["Key", "Value"]
    playlist_rows = list(playlist_data_display.items())
    playlist_table = format_table(playlist_headers, playlist_rows)

    video_headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "Like Count", "bValid"]
    video_rows = []
    for index, video in enumerate(videos):
        try:
            video_row = [
                index + 1,
                getattr(video, 'title', 'N/A'),
                getattr(video, 'url', 'N/A'),
                getattr(video, 'duration', 'N/A'),
                getattr(video, 'uploader', 'N/A'),
                getattr(video, 'uploader_url', 'N/A'),
                getattr(video, 'view_count', 'N/A'),
                getattr(video, 'like_count', 'N/A'),
                getattr(video, 'valid', 'N/A')
            ]
            video_rows.append(video_row)
        except AttributeError as e:
            print(f"Missing attribute in video object: {e}")

    video_table = format_table(video_headers, video_rows)
    return playlist_table, video_table

def build_video_payload(videos):
    return {
        'video_titles': [getattr(video, 'title', 'N/A') for video in videos],
        'saved_video_links': [getattr(video, 'url', 'N/A') for video in videos],
        'video_durations': [getattr(video, 'duration', 0) for video in videos],
        'video_descriptions': [getattr(video, 'description', '') or '' for video in videos],
        'uploader': [getattr(video, 'uploader', 'Unknown') for video in videos],
        'uploader_url': [getattr(video, 'uploader_url', 'Unknown') for video in videos],
        'view_count': [getattr(video, 'view_count', 0) for video in videos],
        'like_count': [getattr(video, 'like_count', 0) for video in videos],
        'isvalid': [getattr(video, 'valid', 1) for video in videos],
        'video_thumbnails': [getattr(video, 'thumbnail', None) for video in videos],
    }

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
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    print(f"YouTube playlist link: {args.playlistLink}")
    print(f"Report format: {args.resultFormat}")
    print(f"List mode: {args.listMode}")
    if len(videos) == 0:
        print("No videos found in the playlist.")
        sys.exit(1)
    
    if args.resultFormat == "cmd":
        playlist_table, video_table = compose_text_table(playlist_data, videos)
        print("Playlist Data:\n")
        print(playlist_table)
        print("\nVideo Data:\n")
        print(video_table)
    elif args.resultFormat == "txt":
        playlist_table, video_table = compose_text_table(playlist_data, videos)
        file_path = os.path.join(folder_path, f"{args.listMode}_{date_time}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"Playlist Data:\n\n{playlist_table}\n")
            file.write(f"\nVideo Data:\n\n{video_table}")
        print(f"Saved .txt report to: {file_path}")
    elif args.resultFormat == "json":
        import json
        file_path = os.path.join(folder_path, f"{args.listMode}_{date_time}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            videos_dict = [video.__dict__ for video in videos]
            json.dump({"playlist_data": playlist_data, "videos": videos_dict}, file, indent=4)
        print(f"Saved .json report to: {file_path}")
    elif args.resultFormat == "csv":
        if len(videos) > 0:
            import csv
            file_path = os.path.join(folder_path, f"{args.listMode}_{date_time}.csv")
            with open(file_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "Like Count", "bValid"]
                writer.writerow(headers)
                
                for index, video in enumerate(videos):
                    try:
                        video_row = [
                            index + 1,
                            getattr(video, 'title', 'N/A'),  
                            getattr(video, 'url', 'N/A'),
                            getattr(video, 'duration', 'N/A'), 
                            getattr(video, 'uploader', 'N/A'), 
                            getattr(video, 'uploader_url', 'N/A'),  
                            getattr(video, 'view_count', 'N/A'), 
                            getattr(video, 'like_count', 'N/A'),
                            getattr(video, 'valid', 'N/A')
                        ]
                        writer.writerow(video_row)
                    except AttributeError as e:
                        print(f"Missing attribute in video object: {e}")
    elif args.resultFormat == "html":
            with open('web_template/script_head_template.js', 'r', encoding='utf-8') as js_file:
                js_code = js_file.read()
            with open('web_template/style_template.css', 'r', encoding='utf-8') as css_file:
                css_styles = css_file.read()
            with open('web_template/style_template.css', 'r', encoding='utf-8') as css_file:
                css_styles = css_file.read()

            import html  # Add import for HTML escaping

            if args.listMode == "unavailable":
                html_list = generate_html_list_invalid_videos(videos, playlist_name, args.playlistLink)
                html_template_path = 'web_template/html_template_backup_removed_report.html'
                page_title = f"Removed videos for Playlist: {playlist_name}"
            else:
                html_list = generate_html_list(videos, playlist_name, playlist_data['url'], playlist_data)
                html_template_path = 'web_template/html_template_backup_report.html'
                page_title = f"Report for Playlist: {playlist_name}"

            # Escape page_title to prevent HTML injection
            safe_page_title = html.escape(page_title)

            html_template = read_html_template(html_template_path)
            head, body = extract_head_and_body(html_template)

            final_html = f"""<html>
            <head>
                <title>{safe_page_title}</title>
                <script>{js_code}</script>
                <style>{css_styles}</style>
                {head}
            </head>
            <body>
                {body}
                {html_list}
                <footer>
                    <h3>Authors:</h3>
                    <div class='links'><a href='https://github.com/Kordight'><strong>Kordight</strong></a></div>
                </footer>
            </body>
            </html>"""

            file_path = os.path.join(folder_path, f"{args.listMode}_{date_time}.html")
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(final_html)
            #Latest report save
            with open (os.path.join(folder_path, f"latest_{args.listMode}.html"), "w", encoding="utf-8") as file:
                file.write(final_html)
            print(f"Saved .html report to: {file_path}")
    
    elif args.resultFormat == "mySQL":
            db_config = load_db_config()
            db_port = int(db_config.get('port', 3306) or 3306)
            create_database(db_config['host'], db_config['user'], db_config['password'], db_config['database'], db_port)
            downloaded_thumbnails_cache = {}
            video_payload = build_video_payload(videos)
            saved = add_report(db_config['host'], db_config['user'], db_config['password'], db_config['database'], db_port,
                video_payload['video_titles'], video_payload['saved_video_links'], playlist_name, args.playlistLink,
                video_payload['video_durations'], video_payload['video_descriptions'], video_payload['uploader'],
                video_payload['uploader_url'], video_payload['view_count'], video_payload['like_count'], video_payload['isvalid'],
                playlist_description, playlist_privacy, playlist_thumbnail, video_payload['video_thumbnails'],
                downloaded_thumbnails_cache, playlist_author=playlist_author, playlist_author_url=playlist_author_url)
            if saved:
                print("Report saved to MySQL database.")
            else:
                print("Report was not saved to MySQL database.")

if __name__ == "__main__":
    main()
