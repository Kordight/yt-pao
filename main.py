import argparse
import re
import sys
from ytdlp_parser import parse_playlist

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

def main():
    args = parse_args()
    playlist_data, videos = parse_playlist(process_playlist_URL(args.playlistLink), args.listMode)
    print(f"YouTube playlist link: {args.playlistLink}")
    print(f"Report format: {args.resultFormat}")
    print(f"List mode: {args.listMode}")
    
    if args.resultFormat == "cmd":
        playlist_headers = ["Key", "Value"]
        playlist_rows = list(playlist_data.items()) 
        playlist_table = format_table(playlist_headers, playlist_rows)
        print("Playlist Data:\n")
        print(playlist_table)
        video_headers = ["Title", "URL", "Duration", "Uploader","Uploader URL", "Approximate View Count", "bValid"]
        video_rows = [[video.title, video.url, video.duration, video.uploader, video.uploader_url, video.view_count, video.valid] for video in videos]

        # Format table
        video_table = format_table(video_headers, video_rows)
        print("\nVideo Data:\n")
        print(video_table)


if __name__ == "__main__":
    main()
