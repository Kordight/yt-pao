from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from mySQL_manager import create_database, create_cursor, get_all_playlists
from main import load_db_config


db_config = load_db_config()
host = db_config['host']
user = db_config['user']
password = db_config['password']
database = db_config['database']
create_database(host, user, password, database)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development; consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/playlists")
def read_playlists():
    cursor, conn = create_cursor(host, user, password, database)
    try:
        playlists = get_all_playlists(cursor)
        print("API endpoint '/api/playlists' called")
        return {"playlists": playlists}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()