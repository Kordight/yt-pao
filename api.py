import re
import threading
import time
from datetime import datetime
from threading import Lock
from typing import Optional

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
)
from ytdlp_parser import parse_playlist
from main import load_db_config
from report_dispatcher import generate_reports_for_formats


db_config = load_db_config()
host = db_config['host']
user = db_config['user']
password = db_config['password']
database = db_config['database']
port = int(db_config.get('port', 3306) or 3306)

MAX_DB_RETRIES = 30
DB_RETRY_INTERVAL = 2  # seconds
for _attempt in range(1, MAX_DB_RETRIES + 1):
    try:
        create_database(host, user, password, database, port)
        break
    except Exception as _e:
        if _attempt == MAX_DB_RETRIES:
            raise
        print(f"[startup] DB not ready (attempt {_attempt}/{MAX_DB_RETRIES}): {_e}. Retrying in {DB_RETRY_INTERVAL}s...")
        time.sleep(DB_RETRY_INTERVAL)

# Processing status tracking
processing_status = {}
processing_lock = Lock()

def update_processing_status(task_id, status):
    with processing_lock:
        processing_status[task_id] = status

def get_processing_status(task_id):
    with processing_lock:
        return processing_status.get(task_id)


class PlaylistRegisterRequest(BaseModel):
    playlist_url: str


class PlaylistReportRequest(BaseModel):
    formats: Optional[list[str]] = None


def normalize_playlist_url(playlist_url: str):
    pattern = r'(?:list=)([a-zA-Z0-9_-]+)'
    match = re.search(pattern, playlist_url)
    if match:
        playlist_id = match.group(1)
        return f'https://www.youtube.com/playlist?list={playlist_id}'
    return None


def generate_report_from_playlist_url(playlist_url: str, task_id: str = None, formats: Optional[list[str]] = None):
    try:
        normalized_url = normalize_playlist_url(playlist_url)
        if not normalized_url:
            print(f"Error: Invalid playlist URL received: {playlist_url}")
            if task_id:
                update_processing_status(task_id, {
                    'status': 'error',
                    'message': 'Invalid playlist URL',
                    'progress': 0
                })
            return

        if task_id:
            update_processing_status(task_id, {
                'status': 'parsing',
                'message': 'Fetching playlist data...',
                'progress': 10
            })

        playlist_data, videos = parse_playlist(normalized_url, 'all')
        if not playlist_data:
            print(f"Error: Failed to parse playlist data for {normalized_url}")
            if task_id:
                update_processing_status(task_id, {
                    'status': 'error',
                    'message': 'Failed to parse playlist data',
                    'progress': 20
                })
            return

        if not videos:
            print(f"Error: No videos found for {normalized_url}")
            if task_id:
                update_processing_status(task_id, {
                    'status': 'error',
                    'message': 'No videos found in this playlist',
                    'progress': 30
                })
            return

        if task_id:
            update_processing_status(task_id, {
                'status': 'processing',
                'message': f'Processing {len(videos)} videos...',
                'progress': 40,
                'processed_videos': 0,
                'total_videos': len(videos),
                'remaining_videos': len(videos),
                'current_video_title': None,
            })

        def update_report_progress(processed_videos: int, total_videos: int, current_video_title: str = None, phase: str = 'processing'):
            if not task_id:
                return

            total_videos = max(int(total_videos or 0), 0)
            processed_videos = max(int(processed_videos or 0), 0)
            remaining_videos = max(total_videos - processed_videos, 0)

            if total_videos > 0:
                if phase == 'saving':
                    progress = 95
                    message = 'Saving processed videos to the database...'
                elif phase == 'thumbnail_repair':
                    progress = 95 + ((processed_videos / total_videos) * 4)
                    message = f'Repairing missing thumbnails {processed_videos}/{total_videos}...'
                else:
                    progress = 40 + ((processed_videos / total_videos) * 50)
                    message = f'Processing video {processed_videos}/{total_videos}...'
            else:
                progress = 40
                message = 'Processing playlist videos...'

            update_processing_status(task_id, {
                'status': phase,
                'message': message if not current_video_title else f'{message} Current: {current_video_title}',
                'progress': min(99, round(progress, 2)),
                'processed_videos': processed_videos,
                'total_videos': total_videos,
                'remaining_videos': remaining_videos,
                'current_video_title': current_video_title,
            })

        selected_formats = formats or ['mySQL']
        report_result = generate_reports_for_formats(
            formats=selected_formats,
            playlist_data=playlist_data,
            videos=videos,
            list_mode='all',
            playlist_link=normalized_url,
            calculate_total_duration=lambda payload: payload.get('playlist_duration', ''),
            db_config={
                'host': host,
                'user': user,
                'password': password,
                'database': database,
                'port': port,
            },
        )

        if task_id:
            task_results = report_result['results']
            mysql_result = task_results.get('mySQL')
            if mysql_result and mysql_result.get('status') == 'success':
                update_processing_status(task_id, {
                    'status': 'completed',
                    'message': 'Report generated successfully',
                    'progress': 100,
                    'completed_at': datetime.now().isoformat(),
                    'results': task_results,
                    'formats': selected_formats,
                })
            else:
                update_processing_status(task_id, {
                    'status': 'error',
                    'message': 'Report was not saved (rejected or failed). Check server logs for details.',
                    'progress': 100,
                    'completed_at': datetime.now().isoformat(),
                    'results': task_results,
                    'formats': selected_formats,
                })

    except Exception as e:
        print(f"Error during report generation: {e}")
        if task_id:
            update_processing_status(task_id, {
                'status': 'error',
                'message': str(e),
                'progress': 0
            })

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
    cursor, conn = create_cursor(host, user, password, database, port)
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
    cursor, conn = create_cursor(host, user, password, database, port)
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

    task_id = f"register_{int(time.time() * 1000)}"
    update_processing_status(task_id, {
        'status': 'queued',
        'message': 'Queued for processing',
        'progress': 0,
        'created_at': datetime.now().isoformat()
    })
    
    # Run in a separate thread
    thread = threading.Thread(
        target=generate_report_from_playlist_url,
        args=(normalized_url, task_id),
        daemon=True
    )
    thread.start()

    return {
        "status": "scheduled",
        "message": "Playlist registration started. Check back soon for the result.",
        "playlist_url": normalized_url,
        "task_id": task_id
    }


@app.post("/api/playlists/{playlist_id}/reports", status_code=202)
def run_playlist_report(playlist_id: int, payload: Optional[PlaylistReportRequest] = None, background_tasks: BackgroundTasks = None):
    cursor, conn = create_cursor(host, user, password, database, port)
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
        
        task_id = f"report_{playlist_id}_{int(time.time() * 1000)}"
        update_processing_status(task_id, {
            'status': 'queued',
            'message': 'Queued for processing',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'playlist_id': playlist_id
        })
        
        # Run in a separate thread
        selected_formats = payload.formats if payload and payload.formats else ['mySQL']
        thread = threading.Thread(
            target=generate_report_from_playlist_url,
            args=(playlist_url, task_id, selected_formats),
            daemon=True
        )
        thread.start()

        return {
            "status": "scheduled",
            "message": "Report generation started. Check back soon for the updated playlist snapshot.",
            "playlist_id": playlist_id,
            "task_id": task_id
            ,"formats": selected_formats
        }
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.get("/api/processing/{task_id}")
def check_processing_status(task_id: str):
    status = get_processing_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status

@app.get("/api/playlists/{playlist_id}/reports/{report_id}")
def read_playlist_report(playlist_id: int, report_id: int):
    cursor, conn = create_cursor(host, user, password, database, port)
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