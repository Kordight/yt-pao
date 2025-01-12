import yt_dlp
import json

# Get playlist link from user or argument
playlist_link = "https://www.youtube.com/playlist?list=PLuoflVrROeM0XvZ7i8YSNK3dbpuvS0Hsp"

# Fetch playlist details with the 'no-youtube-unavailable-videos' flag (this excludes unavailable videos)
ydl_opts_filtered = {
    'quiet': True,
    'extract_flat': True,
    'dump_single_json': True,
    'skip_download': True,
    'compat_opts': ['no-youtube-unavailable-videos'] # Flag to remove unavailable videos
}

# Fetch playlist details without 'no-youtube-unavailable-videos' flag (includes all videos)
ydl_opts_all = {
    'quiet': True,
    'extract_flat': True,
    'dump_single_json': True,
    'skip_download': True
}

# Fetch playlist with 'no-youtube-unavailable-videos' flag
with yt_dlp.YoutubeDL(ydl_opts_filtered) as ydl:
    playlist_dict_filtered = ydl.extract_info(playlist_link, download=False)

# Fetch playlist without 'no-youtube-unavailable-videos' flag
with yt_dlp.YoutubeDL(ydl_opts_all) as ydl:
    playlist_dict_all = ydl.extract_info(playlist_link, download=False)

# Extract video entries from both playlists
video_entries_filtered = playlist_dict_filtered['entries']
video_entries_all = playlist_dict_all['entries']

# Initialize lists for video data
video_data_filtered = {
    'titles': [],
    'links': []
}

video_data_all = {
    'titles': [],
    'links': []
}

# Collect filtered video data (excluding unavailable videos)
for entry in video_entries_filtered:
    video_title = entry['title']
    video_url = entry['url']
    video_data_filtered['titles'].append(video_title)
    video_data_filtered['links'].append(video_url)

# Collect all video data (including unavailable videos)
for entry in video_entries_all:
    video_title = entry['title']
    video_url = entry['url']
    video_data_all['titles'].append(video_title)
    video_data_all['links'].append(video_url)

# Pretty print the filtered video data (without unavailable videos)
print("\nVideo Data (Filtered - No Unavailable Videos):")
for title, url in zip(video_data_filtered['titles'], video_data_filtered['links']):
    print(f"Title: {title}, Link: {url}")

# Pretty print the full video data (including unavailable videos)
print("\nFull Video Data (With All Videos, Including Unavailable):")
for title, url in zip(video_data_all['titles'], video_data_all['links']):
    print(f"Title: {title}, Link: {url}")

# Identify and print the unavailable videos (those in full list but not in filtered list)
invalid_videos = []
for title, url in zip(video_data_all['titles'], video_data_all['links']):
    if url not in video_data_filtered['links']:
        invalid_videos.append({'title': title, 'url': url})

# Print invalid (unavailable) videos
print("\nUnavailable Videos:")
for video in invalid_videos:
    print(f"Title: {video['title']}, Link: {video['url']}")