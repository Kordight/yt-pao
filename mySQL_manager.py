import mysql.connector
from mysql.connector import Error
from datetime import datetime

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

            conn.commit()
            
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

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

            # Add videos and report details
            for title, link, length, uploader_row, uploader_url_row, view_count_row, isvalidl_row in zip(video_titles, saved_video_links, video_durations, uploader, uploader_url, view_count, isvalidl):
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
                    ''', (title, link, length, uploader_row, uploader_url_row, view_count_row, isvalidl_row))
                    video_id = cursor.lastrowid

                # Add report detail
                cursor.execute('''
                INSERT INTO ytp_report_details (report_id, video_id)
                VALUES (%s, %s)
                ''', (report_id, video_id))

                # Find last known playlist title for this playlist before current report
                cursor.execute('''
                    SELECT d.change_value
                    FROM ytp_reports r
                    JOIN ytp_playlist_details d ON r.report_id = d.report_id
                    WHERE r.playlist_id = %s AND d.change_type = 'title' AND r.report_id < %s
                    ORDER BY r.report_id DESC
                    LIMIT 1
                ''', (playlist_id, report_id))

                previous_title = cursor.fetchone()

                # Find last known playlist description for this playlist before current report

                cursor.execute('''
                    SELECT d.change_value
                    FROM ytp_reports r
                    JOIN ytp_playlist_details d ON r.report_id = d.report_id
                    WHERE r.playlist_id = %s AND d.change_type = 'description' AND r.report_id < %s
                    ORDER BY r.report_id DESC
                    LIMIT 1
                ''', (playlist_id, report_id))

                previous_name = cursor.fetchone()

                # If title doesn't exist or has changed, insert new title record
                if not previous_name or previous_name[0] != playlist_description:
                    cursor.execute('''
                        INSERT INTO ytp_playlist_details (report_id, change_type, change_value)
                        VALUES (%s, 'title', %s)
                    ''', (report_id, playlist_description))

            conn.commit()
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()