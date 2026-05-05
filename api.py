from fastapi import FastAPI
from mySQL_manager import create_database, create_cursor, get_all_playlists
from main import load_db_config


db_config = load_db_config()
host = db_config['host']
user = db_config['user']
password = db_config['password']
database = db_config['database']
create_database(host, user, password, database)

# Create cursor and connection

cursor, conn = create_cursor(host, user, password, database)
playlists = []
playlists = get_all_playlists(cursor)
print(playlists)


app = FastAPI()

@app.get("/api/playlists")
def read_playlists():
    print("API endpoint '/api/playlists' called")
    return {"playlists": playlists}