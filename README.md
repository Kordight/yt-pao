# YT-PAO - YouTube Playlist Analyzer & Organizer

YT-PAO analyzes YouTube playlists and produces reports in multiple formats. It started as a terminal tool and now includes a simple web frontend and a FastAPI backend. This repository contains both the original CLI utilities and the web UI + API, plus Docker configuration for running the whole stack.

## Features

- Analyze playlists and extract titles, URLs, durations, uploaders, view counts, and availability status.
- Produce reports in `cmd`, `txt`, `json`, `csv`, `html` or save directly to a MySQL database.
- Work modes: `all`, `available`, `unavailable`.
- CLI utilities for one-off reports and a web interface for browsing playlists and reports.

## Current status

- Backend: FastAPI application (`api.py`) — serves API endpoints and static files.
- Frontend: React + Vite in `frontend/` (development with Vite, production build served with Nginx in Docker).
- Database: MySQL (optional in `docker-compose`, or use an external MySQL instance via environment variables).
- Docker: `Dockerfile`, `frontend/Dockerfile` and `docker-compose.yml` included for easy local deployment.

## Requirements

Python 3.11+ for the backend and Node.js (recommended 18+) for the frontend development. Install Python dependencies with:

```bash
pip install -r requirements.txt
```

For frontend development:

```bash
cd frontend
npm install
```

Docker and Docker Compose are recommended to run the full stack locally.

## Installation (quick)

```bash
git clone https://github.com/your-repo/YT-PAO.git
cd YT-PAO
pip install -r requirements.txt
```

## Usage

CLI (original terminal mode):

```bash
python main.py --playlistLink <playlist_link> --resultFormat <cmd|txt|json|csv|html|mySQL> --listMode <all|available|unavailable>
```

Web API (development):

```bash
python -m uvicorn api:app --reload --port 8000
# API examples: http://localhost:8000/api/playlists
```

Frontend (dev):

```bash
cd frontend
npm run dev
# Vite dev server: http://localhost:5173
```

## Docker (recommended for local deploy)

Copy `.env.example` to `.env` and edit if you want to use an external DB or change defaults.

If your MySQL server is outside Docker, set `DB_HOST` to that server's address. If it runs on the host machine, use `host.docker.internal` on Docker Desktop/Windows or the host's IP/DNS name on Linux.

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3002
- Backend API: http://localhost:8001
- The bundled MySQL container is not published on host port 3306 anymore, so it will not clash with a local MySQL install.

To run without the bundled MySQL, set `DB_HOST` in `.env` to your DB host and start only `backend` and `frontend`:

```bash
DB_HOST=1.2.3.4
docker compose up --build backend frontend
```

## Configuration

The project supports two configuration sources for the backend database connection:

- `config.yaml` (legacy/default) — used when present.
- Environment variables (recommended for Docker): `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

See `.env.example` for environment variable names and defaults.

## File structure (high level)

- `api.py` — FastAPI app and API endpoints
- `main.py` — original CLI entrypoint and helpers
- `mySQL_manager.py` — database utilities
- `frontend/` — React + Vite frontend
- `web_template/` — HTML templates used by CLI HTML output
- `docker-compose.yml`, `Dockerfile`, `frontend/Dockerfile` — docker configuration
- `requirements.txt` — Python dependencies

## Comparing Playlists / Detecting Missing Videos

YT-PAO can compare latest reports for playlists stored in MySQL to identify missing videos between playlists. The SQL example below demonstrates the query pattern used to compute differences between two playlist snapshots.

```mysql
WITH params AS (
   SELECT 2 AS p1, 19 AS p2 -- Replace 2 and 19 with your playlist IDs
),
last_reports AS (
   SELECT r.playlist_id, r.report_id
   FROM ytp_reports r
   INNER JOIN (
      SELECT playlist_id, MAX(report_date) AS max_date
      FROM ytp_reports, params
      WHERE playlist_id IN (SELECT p1 FROM params UNION SELECT p2 FROM params)
      GROUP BY playlist_id
   ) latest
     ON r.playlist_id = latest.playlist_id
    AND r.report_date = latest.max_date
),
videos_in_playlists AS (
   SELECT rd.video_id, v.video_title, v.video_url, r.playlist_id
   FROM ytp_report_details rd
   JOIN ytp_reports r ON rd.report_id = r.report_id
   JOIN ytp_videos v ON rd.video_id = v.video_id
   WHERE r.report_id IN (SELECT report_id FROM last_reports)
)

-- Videos in Playlist p1 missing from p2
SELECT 
   v1.video_id,
   v1.video_title,
   v1.video_url,
   (SELECT p1 FROM params) AS playlist_source
FROM (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p1 FROM params)) v1
LEFT JOIN (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p2 FROM params)) v2
      ON v1.video_id = v2.video_id
WHERE v2.video_id IS NULL

UNION

-- Videos in Playlist p2 missing from p1
SELECT 
   v2.video_id,
   v2.video_title,
   v2.video_url,
   (SELECT p2 FROM params) AS playlist_source
FROM (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p2 FROM params)) v2
LEFT JOIN (SELECT * FROM videos_in_playlists WHERE playlist_id = (SELECT p1 FROM params)) v1
      ON v2.video_id = v1.video_id
WHERE v1.video_id IS NULL;

```

## Authors

- **Kordight** - [GitHub](https://github.com/Kordight)
