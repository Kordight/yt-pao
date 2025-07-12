import argparse
import re
import sys
from ytdlp_parser import parse_playlist, calculate_total_duration
import os
from datetime import datetime
import yaml
from html_manager import generate_html_list, read_html_template, extract_head_and_body, generate_html_list_invalid_videos
from mySQL_manager import add_report, create_database

def process_playlist_URL(playlist_URL):
    pattern = r'(?:list=)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, playlist_URL)
    if match:
        playlist_id = match.group(1)
        return f'https://www.youtube.com/playlist?list={playlist_id}'
    
    print("Error: URL is not YouTube playlist URL!", file=sys.stderr)
    sys.exit(1)

def parse_args():
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Interpretation of flags and YouTube playlist link.")

    # Define flags
    parser.add_argument('--playlistLink', type=str, required=True, help="The YouTube playlist link.")
    parser.add_argument('--resultFormat', type=str, required=True, choices=['cmd', 'txt', 'json', 'mySQL', 'csv', 'html'],
                        help="The report format. Available options: cmd, txt, json, mySQL, csv, html.")
    parser.add_argument('--listMode', type=str, required=True, choices=['all', 'unavailable', 'available'],
                        help="The work mode. Available options: all, unavailable, available.")
    # Parse arguments
    args = parser.parse_args()
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

    video_headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "bValid"]
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
                getattr(video, 'valid', 'N/A')
            ]
            video_rows.append(video_row)
        except AttributeError as e:
            print(f"Missing attribute in video object: {e}")

    video_table = format_table(video_headers, video_rows)
    return playlist_table, video_table
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
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return config['database']

def main():
    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    args = parse_args()
    playlist_data, videos = parse_playlist(process_playlist_URL(args.playlistLink), args.listMode)
    playlist_name = playlist_data['playlist_name']
    playlist_description = playlist_data['description']
    folder_path = f"Output/{playlist_name}"
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
                headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "bValid"]
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

            print(f"Saved .html report to: {file_path}")
    
    elif args.resultFormat == "mySQL":
            db_config = load_db_config()
            create_database(db_config['host'], db_config['user'], db_config['password'], db_config['database'])
            video_titles = [video.title for video in videos]
            saved_video_links = [video.url for video in videos]
            video_durations = [video.duration for video in videos]
            uploader = [video.uploader for video in videos]
            uploader_url = [video.uploader_url for video in videos]
            view_count = [video.view_count for video in videos]
            isvalid = [video.valid for video in videos]
            add_report(db_config['host'], db_config['user'], db_config['password'], db_config['database'],
                    video_titles, saved_video_links, playlist_name, args.playlistLink, video_durations, uploader, uploader_url,view_count, isvalid, playlist_description)
            print("Report saved to MySQL database.")

if __name__ == "__main__":
    main()