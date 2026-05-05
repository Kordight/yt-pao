import re

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mySQL_manager import (
    create_database,
    create_cursor,
    get_all_playlists,
    get_playlist_reports,
    get_playlist_content_by_report_id,
    add_report,
)
from ytdlp_parser import parse_playlist
from main import load_db_config


db_config = load_db_config()
host = db_config['host']
user = db_config['user']
password = db_config['password']
database = db_config['database']
create_database(host, user, password, database)


class PlaylistRegisterRequest(BaseModel):
    playlist_url: str


def normalize_playlist_url(playlist_url: str):
    pattern = r'(?:list=)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, playlist_url)
    if match:
        playlist_id = match.group(1)
        return f'https://www.youtube.com/playlist?list={playlist_id}'
    return None


def generate_report_from_playlist_url(playlist_url: str):
    normalized_url = normalize_playlist_url(playlist_url)
    if not normalized_url:
        print(f"Error: Invalid playlist URL received: {playlist_url}")
        return

    playlist_data, videos = parse_playlist(normalized_url, 'all')
    if not playlist_data:
        print(f"Error: Failed to parse playlist data for {normalized_url}")
        return

    if not videos:
        print(f"Error: No videos found for {normalized_url}")
        return

    video_titles = [video.title for video in videos]
    saved_video_links = [video.url for video in videos]
    video_durations = [video.duration for video in videos]
    uploader = [video.uploader for video in videos]
    uploader_url = [video.uploader_url for video in videos]
    view_count = [video.view_count for video in videos]
    isvalid = [video.valid for video in videos]
    video_thumbnails = [video.thumbnail for video in videos]

    add_report(
        host,
        user,
        password,
        database,
        video_titles,
        saved_video_links,
        playlist_data['playlist_name'],
        normalized_url,
        video_durations,
        uploader,
        uploader_url,
        view_count,
        isvalid,
        playlist_data.get('description', ''),
        playlist_data.get('playlist_privacy', 'public'),
        playlist_data.get('playlist_thumbnail', None),
        video_thumbnails,
        {},
        playlist_author=playlist_data.get('uploader', None),
        playlist_author_url=playlist_data.get('uploader_url', None),
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development; consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")

@app.get("/api/playlists")
def read_playlists():
    cursor, conn = create_cursor(host, user, password, database)
    try:
        if not cursor or not conn:
            raise HTTPException(status_code=500, detail="Unable to open database connection")
        playlists = get_all_playlists(cursor)
        print("API endpoint '/api/playlists' called")
        return {"playlists": playlists}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.get("/api/playlists/{playlist_id}/reports")
def read_playlist_reports(playlist_id: int):
    cursor, conn = create_cursor(host, user, password, database)
    try:
        if not cursor or not conn:
            raise HTTPException(status_code=500, detail="Unable to open database connection")

        reports = get_playlist_reports(cursor, playlist_id)
        return {"playlist_id": playlist_id, "reports": reports}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.post("/api/playlists/register", status_code=202)
def register_playlist(payload: PlaylistRegisterRequest, background_tasks: BackgroundTasks):
    normalized_url = normalize_playlist_url(payload.playlist_url)
    if not normalized_url:
        raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL")

    background_tasks.add_task(generate_report_from_playlist_url, normalized_url)
    return {
        "status": "scheduled",
        "message": "Playlist registration started. Check back soon for the result.",
        "playlist_url": normalized_url,
    }


@app.post("/api/playlists/{playlist_id}/reports", status_code=202)
def run_playlist_report(playlist_id: int, background_tasks: BackgroundTasks):
    cursor, conn = create_cursor(host, user, password, database)
    try:
        if not cursor or not conn:
            raise HTTPException(status_code=500, detail="Unable to open database connection")

        cursor.execute('''
            SELECT playlist_url
            FROM ytp_playlists
            WHERE playlist_id = %s
            LIMIT 1
        ''', (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Playlist not found")

        playlist_url = row[0]
        background_tasks.add_task(generate_report_from_playlist_url, playlist_url)
        return {
            "status": "scheduled",
            "message": "Report generation started. Check back soon for the updated playlist snapshot.",
            "playlist_id": playlist_id,
        }
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.get("/api/playlists/{playlist_id}/reports/{report_id}")
def read_playlist_report(playlist_id: int, report_id: int):
    cursor, conn = create_cursor(host, user, password, database)
    try:
        if not cursor or not conn:
            raise HTTPException(status_code=500, detail="Unable to open database connection")

        cursor.execute('''
            SELECT report_id
            FROM ytp_reports
            WHERE playlist_id = %s AND report_id = %s
            LIMIT 1
        ''', (playlist_id, report_id))
        report_exists = cursor.fetchone()
        if not report_exists:
            raise HTTPException(status_code=404, detail="Report not found")

        snapshot = get_playlist_content_by_report_id(cursor, report_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Playlist snapshot not found")

        return snapshot
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()