import yt_dlp

class Video:

    def __init__(self, title, url, duration, uploader, view_count=0, video_uploader_url=None, valid=1):
        self.title = title
        self.url = url
        self.duration = duration
        self.uploader = uploader
        self.view_count = view_count
        self.uploader_url = video_uploader_url
        self.valid = valid

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

    video_entries = playlist_dict.get('entries', [])
    playlist_data = {
        'playlist_name': playlist_dict.get('title', 'Unknown Playlist'),
        'video_entries': len(video_entries),
        'description': playlist_dict.get('description', 'No description available'),
        'playlist_id': playlist_dict.get('id', 'Unknown ID'),
        'uploader': playlist_dict.get('uploader', 'Unknown uploader'),
        'uploader_url': playlist_dict.get('uploader_url', 'Unknown uploader'),
        'url': playlist_dict.get('webpage_url', playlist_link)  
    }

    videos = []
    for entry in video_entries:
        video_title = entry.get('title', 'Unknown Title')
        video_url = entry.get('url', 'Unknown URL')
        video_duration = entry.get('duration', 0)  
        video_uploader = entry.get('uploader', 'Unknown')
        video_uploader_url = entry.get('uploader_url', 'Unknown')
        video_view_count = entry.get('view_count', 0)  
        videos.append(Video(video_title, video_url, video_duration, video_uploader, video_view_count, video_uploader_url))

    return playlist_data, videos


def find_unavailable_videos(playlist_link):

    # Skip invalid videos
    ydl_opts_filtered = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'skip_download': True,
        'compat_opts': ['no-youtube-unavailable-videos']
    }

    # Include all videos
    ydl_opts_all = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'skip_download': True
    }

    # Download valid videos data from playlist
    playlist_data_filtered, videos_filtered = get_playlist_content(playlist_link, ydl_opts_filtered)
    if playlist_data_filtered is None:
        return None, []

    #  Download all videos data from playlist
    playlist_data_all, videos_all = get_playlist_content(playlist_link, ydl_opts_all)
    if playlist_data_all is None:
        return None, []

    # Identify invalid videos
    filtered_urls = {video.url for video in videos_filtered}
    unavailable_videos = [video for video in videos_all if video.url not in filtered_urls]
    for video in unavailable_videos:
        video.valid = 0
    return playlist_data_all, unavailable_videos


def parse_playlist(url, listMode):

    ydl_opts_all = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'skip_download': True
    }
    ydl_opts_no_unavailable = {
        'quiet': True,
        'extract_flat': True,
        'dump_single_json': True,
        'skip_download': True,
        'compat_opts': ['no-youtube-unavailable-videos']
    }

    if listMode == "all":
        # Download full playlist data
        playlist_data, videos = get_playlist_content(url, ydl_opts_all)

        # Find invalid videos and replace the corresponding entries in 'videos'
        playlist_data, unavailable_videos = find_unavailable_videos(url)
        
        # Zastępujemy tylko te wideo, które są niedostępne
        for unavailable_video in unavailable_videos:
            for idx, video in enumerate(videos):
                if video.url == unavailable_video.url:  
                    videos[idx] = unavailable_video
        videos.sort(key=lambda video: video.valid)
        return playlist_data, videos

    elif listMode == "unavailable":
        # Find invalid videos
        playlist_data, unavailable_videos = find_unavailable_videos(url)
        return playlist_data, unavailable_videos

    elif listMode == "available":
        # Download only valid videos
        playlist_data, videos = get_playlist_content(url, ydl_opts_no_unavailable)
        return playlist_data, videos

    else:
        raise ValueError(f"Invalid listMode: {listMode}")
