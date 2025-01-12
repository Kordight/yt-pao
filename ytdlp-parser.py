import re
import yt_dlp

def get_playlist_content(playlist_link, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_dict = ydl.extract_info(playlist_link, download=False)

    video_entries = playlist_dict['entries']
    playlist_data = {
        'playlist_name': playlist_dict['title'],
        'video_entries': len(playlist_dict['entries']),
        'playlist_id': playlist_dict['id'],
        'description': playlist_dict['description'],
        'uploader': playlist_dict['uploader'],
        'url': playlist_dict['url']
    }

    class Video:
        def __init__(self, title, url, duration, uploader):
            self.title = title
            self.url = url
            self.duration = duration
            self.uploader = uploader

    videos = []

    for entry in video_entries:
        video_title = entry['title']
        video_url = entry['url']
        video_duration = entry['duration'] if entry['duration'] is not None else 0
        video_uploader = entry['uploader'] if 'uploader' in entry else 'Unknown'
        video = Video(video_title, video_url, video_duration, video_uploader)
        videos.append(video)

    return playlist_data, videos

def parse_playlist(url, listMode):
    ydl_opts = {}
    videos = []
    playlist_data = []

    if listMode == "all":
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'dump_single_json': True,
            'skip_download': True
        }
        playlist_data, videos = get_playlist_content(url, ydl_opts)

    elif listMode == "unavailable":
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'dump_single_json': True,
            'skip_download': True,
            'compat_opts': ['no-youtube-unavailable-videos']
        }
        playlist_data_hidden, videos_hidden = get_playlist_content(url, ydl_opts)

        ydl_opts['compat_opts'] = []
        playlist_data_full, videos_full = get_playlist_content(url, ydl_opts)

        # Usuwanie wideo dostępnych z listy pełnej, pozostawiając tylko niedostępne
        videos_unavailable = [video for video in videos_full if video not in videos_hidden]
        playlist_data = playlist_data_hidden

        videos = videos_unavailable

    elif listMode == "available":
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'dump_single_json': True,
            'skip_download': True,
            'compat_opts': ['no-youtube-unavailable-videos']
        }
        playlist_data, videos = get_playlist_content(url, ydl_opts)

    return playlist_data, videos

# Przykładowe wywołanie funkcji
url = "https://www.youtube.com/playlist?list=PL..."  # Zastąp rzeczywistym linkiem do playlisty
resultFormat = "json"
listMode = "all"
parse_playlist(url, resultFormat, listMode)
