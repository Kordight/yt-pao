import mysql.connector
from mysql.connector import Error
from datetime import datetime

def normalize_view_count(view_count):
    try:
        return int(view_count)
    except (TypeError, ValueError):
        return 0

def create_database(host, user, password, database):
    conn = None  # Initialize conn to None
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306)
        if conn.is_connected():
            cursor = conn.cursor()

            # Create tables if not exists
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ytp_playlists (
                playlist_id INT AUTO_INCREMENT PRIMARY KEY,
                playlist_name VARCHAR(255) NOT NULL,
                playlist_url VARCHAR(255) NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ytp_videos (
                video_id INT AUTO_INCREMENT PRIMARY KEY,
                video_title VARCHAR(255) NOT NULL,
                video_url VARCHAR(255) NOT NULL UNIQUE,
                video_duration INT NOT NULL,
                uploader VARCHAR(255),
                uploader_url VARCHAR(255),
                view_count BIGINT,
                valid BOOLEAN
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ytp_reports (
                report_id INT AUTO_INCREMENT PRIMARY KEY,
                report_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                playlist_id INT NOT NULL,
                FOREIGN KEY (playlist_id) REFERENCES ytp_playlists(playlist_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ytp_report_details (
                detail_id INT AUTO_INCREMENT PRIMARY KEY,
                report_id INT NOT NULL,
                video_id INT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES ytp_reports(report_id) ON DELETE CASCADE,
                FOREIGN KEY (video_id) REFERENCES ytp_videos(video_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ytp_playlist_details (
                    change_id INT AUTO_INCREMENT PRIMARY KEY,
                    report_id INT,
                    change_type ENUM('description', 'title') NOT NULL,
                    change_value TEXT NOT NULL,
                    FOREIGN KEY (report_id) REFERENCES ytp_reports(report_id)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ytp_video_details (
                    change_id INT AUTO_INCREMENT PRIMARY KEY,
                    video_id INT NOT NULL,
                    report_id INT NOT NULL,
                    change_type ENUM('title', 'views', 'availability') NOT NULL,
                    change_value TEXT NOT NULL,
                    FOREIGN KEY (video_id) REFERENCES ytp_videos(video_id)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (report_id) REFERENCES ytp_reports(report_id)
                        ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')

            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'ytp_video_details' AND TABLE_SCHEMA = DATABASE()
            """)
            columns = {row[0] for row in cursor.fetchall()}

            # List of required columns
            # If any of these columns are missing, they will be added
            required_columns = {
                'report_id': "ADD COLUMN report_id INT",
                'change_type': "MODIFY COLUMN change_type ENUM('title', 'views', 'availability') NOT NULL",
                'change_value': "MODIFY COLUMN change_value TEXT NOT NULL"
            }

            # Execute ALTER TABLE statements for each required column
            for col_name, alter_sql in required_columns.items():
                if col_name not in columns:
                    print(f"Adding or modifying column: {col_name}")
                    cursor.execute(f"ALTER TABLE ytp_video_details {alter_sql}")

            conn.commit()
            
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
def update_playlist_metadata_if_changed(cursor, playlist_id, report_id, playlist_name, playlist_description):
    # Previous palylist title and description
                cursor.execute('''
                    SELECT d.change_value
                    FROM ytp_reports r
                    JOIN ytp_playlist_details d ON r.report_id = d.report_id
                    WHERE r.playlist_id = %s AND d.change_type = 'title' AND r.report_id < %s
                    ORDER BY r.report_id DESC
                    LIMIT 1
                ''', (playlist_id, report_id))
                previous_title = cursor.fetchone()

                cursor.execute('''
                    SELECT d.change_value
                    FROM ytp_reports r
                    JOIN ytp_playlist_details d ON r.report_id = d.report_id
                    WHERE r.playlist_id = %s AND d.change_type = 'description' AND r.report_id < %s
                    ORDER BY r.report_id DESC
                    LIMIT 1
                ''', (playlist_id, report_id))
                previous_description = cursor.fetchone()

                # If title has changed, insert a new record
                if not previous_title or previous_title[0] != playlist_name:
                    cursor.execute('''
                        INSERT INTO ytp_playlist_details (report_id, change_type, change_value)
                        VALUES (%s, 'title', %s)
                    ''', (report_id, playlist_name))

                # If description has changed, insert a new record
                if not previous_description or previous_description[0] != playlist_description:
                    cursor.execute('''
                        INSERT INTO ytp_playlist_details (report_id, change_type, change_value)
                        VALUES (%s, 'description', %s)
                    ''', (report_id, playlist_description))

def update_video_metadata_if_changed(cursor, video_id, video_title, view_count, availability, report_id):
    # Check if the video title has changed
    cursor.execute('''
        SELECT change_value 
        FROM ytp_video_details 
        WHERE video_id = %s AND change_type = 'title'
        ORDER BY change_id DESC 
        LIMIT 1
    ''', (video_id,))
    last_title = cursor.fetchone()
    
    if not last_title or last_title[0] != video_title:
        cursor.execute('''
            INSERT INTO ytp_video_details (video_id, report_id, change_type, change_value)
            VALUES (%s, %s, %s, %s)
        ''', (video_id, report_id, 'title', video_title))
    
    normalized_view_count = int(normalize_view_count(view_count))

    # Check if view count changed
    cursor.execute('''
        SELECT change_value 
        FROM ytp_video_details 
        WHERE video_id = %s AND change_type = 'views'
        ORDER BY change_id DESC 
        LIMIT 1
    ''', (video_id,))
    last_view_count = cursor.fetchone()

    # If last_view_count is None, it means this is the first time we're inserting a view count for this video
    if not last_view_count or not last_view_count[0].isdigit() or int(last_view_count[0]) != normalized_view_count:
        cursor.execute('''
            INSERT INTO ytp_video_details (video_id, report_id, change_type, change_value)
            VALUES (%s, %s, %s, %s)
        ''', (video_id, report_id, 'views', normalized_view_count))
        #print(f"Updated view count for video {video_id} to {normalized_view_count}, because it changed from {last_view_count[0] if last_view_count else 'None'} to {normalized_view_count}; last_view_count: {last_view_count[0] if last_view_count else 'None'}")

    # Check if availability changed
    cursor.execute('''
        SELECT change_value 
        FROM ytp_video_details 
        WHERE video_id = %s AND change_type = 'availability'
        ORDER BY change_id DESC 
        LIMIT 1
    ''', (video_id,))
    last_availability = cursor.fetchone()
    
    if not last_availability or last_availability[0] != str(availability):
        cursor.execute('''
            INSERT INTO ytp_video_details (video_id, report_id, change_type, change_value)
            VALUES (%s, %s, %s, %s)
        ''', (video_id, report_id, 'availability', str(availability)))



    
def add_report(host, user, password, database, video_titles, saved_video_links, playlist_name, playlist_url, video_durations, uploader, uploader_url, view_count, isvalidl, playlist_description):
    conn = None  # Initialize conn to None
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306,
            auth_plugin='mysql_native_password'
        )
        if conn.is_connected():
            cursor = conn.cursor()

            # Check if playlist already exists
            cursor.execute('''
            SELECT playlist_id FROM ytp_playlists WHERE playlist_url = %s
            ''', (playlist_url,))
            result = cursor.fetchone()

            if result:
                playlist_id = result[0]
            else:
                # Add playlist
                cursor.execute('''
                INSERT INTO ytp_playlists (playlist_name, playlist_url)
                VALUES (%s, %s)
                ''', (playlist_name, playlist_url))
                conn.commit()  # Commit after inserting the playlist
                playlist_id = cursor.lastrowid

            # Add report
            report_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO ytp_reports (report_date, playlist_id)
            VALUES (%s, %s)
            ''', (report_date, playlist_id))
            report_id = cursor.lastrowid
            update_playlist_metadata_if_changed(cursor, playlist_id, report_id, playlist_name, playlist_description)

            # Add videos and report details
            for title, link, length, uploader_row, uploader_url_row, view_count_row, isvalid_row in zip(video_titles, saved_video_links, video_durations, uploader, uploader_url, view_count, isvalidl):
                if length is None:
                    length = 0 

                # Check if video already exists
                cursor.execute('''
                SELECT video_id FROM ytp_videos WHERE video_url = %s
                ''', (link,))
                video_result = cursor.fetchone()

                if video_result:
                    video_id = video_result[0]
                else:
                    # Add video
                    cursor.execute('''
                    INSERT INTO ytp_videos (video_title, video_url, video_duration, uploader, uploader_url, view_count, valid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (title, link, length, uploader_row, uploader_url_row, view_count_row, isvalid_row))
                    video_id = cursor.lastrowid

                # Add report detail
                cursor.execute('''
                INSERT INTO ytp_report_details (report_id, video_id)
                VALUES (%s, %s)
                ''', (report_id, video_id))
                # Update video metadata if it has changed
                update_video_metadata_if_changed(cursor, video_id, title, view_count_row, isvalid_row, report_id)

            conn.commit()
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()