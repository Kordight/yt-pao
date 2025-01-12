import argparse
import re
import sys
from ytdlp_parser import parse_playlist
import os
from datetime import datetime

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
    parser.add_argument('--resultFormat', type=str, required=True, choices=['cmd', 'txt', 'json', 'mySQL', 'csv'],
                        help="The report format. Available options: cmd, txt, json, mySQL, csv.")
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
        # Ensure playlist_data is a dictionary and playlist_data.items() works
        playlist_headers = ["Key", "Value"]
        playlist_rows = list(playlist_data.items())  # Assuming playlist_data is a dictionary
        playlist_table = format_table(playlist_headers, playlist_rows)


        # Ensure videos is a list of objects with required attributes
        video_headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "bValid"]
        
        # Safely access video attributes and handle missing ones
        video_rows = []
        for index, video in enumerate(videos):
            try:
                # Gather required fields from the video object
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
        
        # Format table for videos
        video_table = format_table(video_headers, video_rows)
        return playlist_table, video_table

def main():
    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    args = parse_args()
    playlist_data, videos = parse_playlist(process_playlist_URL(args.playlistLink), args.listMode)
    playlist_name = playlist_data['playlist_name']
    folder_path = f"Output/{playlist_name}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    print(f"YouTube playlist link: {args.playlistLink}")
    print(f"Report format: {args.resultFormat}")
    print(f"List mode: {args.listMode}")
    if args.resultFormat == "cmd":
        playlist_table, video_table = compose_text_table(playlist_data, videos)
        print("Playlist Data:\n")
        print(playlist_table)
        print("\nVideo Data:\n")
        print(video_table)
    elif args.resultFormat == "txt":
        playlist_table, video_table = compose_text_table(playlist_data, videos)
        file_path = os.path.join(folder_path, f"{date_time}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"Playlist Data:\n\n{playlist_table}\n")
            file.write(f"\nVideo Data:\n\n{video_table}")
        print(f"Saved .txt report to: {file_path}")
if __name__ == "__main__":
    main()
