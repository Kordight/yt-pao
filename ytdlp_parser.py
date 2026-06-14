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
        if not entry:
            continue
            
        video_title = entry.get('title') or 'Unknown Title'
        video_url = entry.get('url') or 'Unknown URL'
        video_duration = entry.get('duration') or 0  
        
        video_uploader = entry.get('uploader') or entry.get('channel') or 'Unknown'
        video_uploader_url = entry.get('uploader_url') or entry.get('channel_url') or 'Unknown'
        video_view_count = entry.get('view_count') or 0  
        
        is_valid = 1
        vt_clean = str(video_title).strip()
        
        if '[Deleted video]' in vt_clean or '[Private video]' in vt_clean or '[Video deleted]' in vt_clean or vt_clean == 'Unknown Title':
            is_valid = 0
        elif (not video_duration or video_duration == 0) and video_uploader in ['Unknown', 'Unknown author', None]:
            is_valid = 0
            
        video_best_thumbnail_url = None
        thumbnails = entry.get('thumbnails', [])
        if thumbnails:
            video_best_thumbnail_url = thumbnails[-1].get('url')

        videos.append(Video(video_title, video_url, video_duration, video_uploader, video_view_count, video_uploader_url, is_valid, video_best_thumbnail_url))

    # Add basic playlist metadata
    playlist_data = {
        'playlist_name': playlist_dict.get('title') or 'Unknown Playlist',
        'description': playlist_dict.get('description') or '',
        'playlist_id': playlist_dict.get('id') or 'Unknown ID',
        'uploader': playlist_dict.get('uploader') or playlist_dict.get('channel') or 'Unknown',
        'uploader_url': playlist_dict.get('uploader_url') or playlist_dict.get('channel_url') or 'Unknown',
        'url': playlist_link,
        'playlist_duration': sum(v.duration for v in videos),
        'playlist_privacy': playlist_dict.get('availability') or 'unknown',
        'playlist_thumbnail': best_playlist_thumb_url
    }

    return playlist_data, videos

def parse_playlist(url, listMode):
    ydl_opts_all = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'skip_download': True,
        'cachedir': False,
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt'
    }

    ydl_opts_available = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'skip_download': True,
        'cachedir': False,
        'ignoreerrors': True,
        'cookiefile': 'cookies.txt',
        'compat_opts': set(['no-youtube-unavailable-videos'])
    }

    print("[Parser] Skan 1/2: Pobieranie struktury całej playlisty...")
    playlist_data, all_videos = get_playlist_content(url, ydl_opts_all)

    if playlist_data is None:
        return None, []

    print("[Parser] Skan 2/2: Filtrowanie dostępności przez YouTube...")
    _, available_videos = get_playlist_content(url, ydl_opts_available)

    available_urls = {v.url for v in available_videos}

    for video in all_videos:
        if video.url not in available_urls:
            if video.valid != 0:
                print(f"[OSTRZEŻENIE] Znalazłem film ukryty w Skanie 2! Zmieniam twardo status na 'Niedostępny': {video.title} ({video.url})")
            video.valid = 0

    all_videos.sort(key=lambda video: video.valid, reverse=True)

    if listMode == "all":
        return playlist_data, all_videos
    elif listMode == "unavailable":
        return playlist_data, [v for v in all_videos if v.valid == 0]
    elif listMode == "available":
        return playlist_data, [v for v in all_videos if v.valid == 1]
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
    else:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"