import yt_dlp

class Video:
    def __init__(self, title, url, duration, uploader, view_count=0, video_uploader_url=None, valid=1, thumbnail_url=None):
        self.title = title
        self.url = url
        self.duration = duration
        self.uploader = uploader
        self.view_count = view_count
        self.uploader_url = video_uploader_url
        self.valid = valid
        self.thumbnail = thumbnail_url

    def __eq__(self, other):
        if isinstance(other, Video):
            return self.url == other.url
        return False

    def __hash__(self):
        return hash(self.url)

def get_playlist_content(playlist_link, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            playlist_dict = ydl.extract_info(playlist_link, download=False)
        except yt_dlp.utils.DownloadError as e:
            print(f"ERROR: Cannot download playlist data: {e}")
            return None, []

    playlist_thumbnails = playlist_dict.get('thumbnails', [])
    best_playlist_thumb_url = playlist_thumbnails[-1].get('url') if playlist_thumbnails else None

    video_entries = playlist_dict.get('entries', [])
    videos = []
    
    for entry in video_entries:
        video_title = entry.get('title') or 'Unknown Title'
        video_url = entry.get('url') or 'Unknown URL'
        video_duration = entry.get('duration') or 0  
        
        # ZMIANA: YT czasami używa klucza 'channel' zamiast 'uploader'
        video_uploader = entry.get('uploader') or entry.get('channel') or 'Unknown'
        video_uploader_url = entry.get('uploader_url') or entry.get('channel_url') or 'Unknown'
        
        video_view_count = entry.get('view_count') or 0 
        
        # Szybkie wykrywanie usuniętych/prywatnych filmów na podstawie jednego pobrania
        is_valid = 1
        if video_title in ['[Deleted video]', '[Private video]'] or video_title == 'Unknown Title' or (video_uploader == 'Unknown' and video_duration == 0):
            is_valid = 0
            
        video_best_thumbnail_url = None
        if 'thumbnails' in entry and entry['thumbnails']:
            video_best_thumbnail_url = entry['thumbnails'][-1].get('url')
            
        videos.append(Video(
            title=video_title, 
            url=video_url, 
            duration=video_duration, 
            uploader=video_uploader, 
            view_count=video_view_count, 
            video_uploader_url=video_uploader_url, 
            valid=is_valid, 
            thumbnail_url=video_best_thumbnail_url
        ))

    playlist_duration = sum(
        entry['duration'] if isinstance(entry.get('duration'), (int, float)) else 0
        for entry in video_entries
    )    

    if not best_playlist_thumb_url and videos:
        first_video_thumb = videos[0].thumbnail
        if first_video_thumb:
            best_playlist_thumb_url = first_video_thumb

    playlist_data = {
        'playlist_name': playlist_dict.get('title', 'Unknown Playlist'),
        'video_entries': len(video_entries),
        'description': playlist_dict.get('description', 'No description available'),
        'playlist_id': playlist_dict.get('id', 'Unknown ID'),
        'uploader': (playlist_dict.get('uploader') or 'Unknown uploader').removeprefix('by ').strip(),    
        'uploader_url': playlist_dict.get('uploader_url', 'Unknown URL'),
        'url': playlist_dict.get('webpage_url', playlist_link),  
        'playlist_duration': playlist_duration,
        'playlist_privacy': playlist_dict.get('availability', 'public'),
        'playlist_thumbnail': best_playlist_thumb_url
    }
    return playlist_data, videos

def parse_playlist(url, listMode):
    ydl_opts_all = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'skip_download': True,
        'cachedir': False,
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt'
    }

    # Pobieramy wszystko tylko jednym żądaniem API
    playlist_data, videos = get_playlist_content(url, ydl_opts_all)

    if playlist_data is None:
        return None, []

    # Sortujemy od dostępnych do niedostępnych (tak jak w oryginalnym kodzie)
    videos.sort(key=lambda video: video.valid, reverse=True)

    if listMode == "all":
        return playlist_data, videos
    elif listMode == "unavailable":
        return playlist_data, [v for v in videos if v.valid == 0]
    elif listMode == "available":
        return playlist_data, [v for v in videos if v.valid == 1]
    else:
        raise ValueError(f"Invalid listMode: {listMode}")

def calculate_total_duration(playlist_data):
    THREE_DAYS_IN_SECONDS = 3 * 24 * 3600
    total_seconds = playlist_data.get('playlist_duration', 0)
    if not isinstance(total_seconds, int):
        try:
            total_seconds = int(total_seconds)
        except Exception:
            total_seconds = 0

    if total_seconds >= THREE_DAYS_IN_SECONDS:
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif total_seconds >= 3600:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    elif total_seconds > 0:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        return "N/A"