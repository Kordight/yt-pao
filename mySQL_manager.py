import mysql.connector
from mysql.connector import Error
from datetime import datetime, timezone
from thumbnail_parser import download_image, calculate_sha256, save_image

def normalize_view_count(view_count):
    try:
        return int(view_count)
    except (TypeError, ValueError):
        return 0

def normalize_text(value, default=''):
    if value is None:
        return default
    return str(value)

def get_cached_thumbnail_id(cursor, thumbnail_url):
    if not thumbnail_url:
        return None

    cursor.execute('''
        SELECT thumbnail_id
        FROM ytp_thumbnails
        WHERE source_url = %s
        ORDER BY thumbnail_id DESC
        LIMIT 1
    ''', (thumbnail_url,))
    result = cursor.fetchone()
    return result[0] if result else None

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                CREATE TABLE IF NOT EXISTS ytp_thumbnails (
                    thumbnail_id INT AUTO_INCREMENT PRIMARY KEY,
                    file_name VARCHAR(255) NOT NULL,
                    source_url VARCHAR(1024),
                    sha256_hash VARCHAR(64) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ytp_playlist_details (
                    change_id INT AUTO_INCREMENT PRIMARY KEY,
                    report_id INT,
                    thumbnail_id INT,
                    change_type ENUM('description', 'title', 'thumbnail', 'privacy') NOT NULL,
                    change_value TEXT, 
                    FOREIGN KEY (report_id) REFERENCES ytp_reports(report_id) ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (thumbnail_id) REFERENCES ytp_thumbnails(thumbnail_id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ytp_video_details (
                    change_id INT AUTO_INCREMENT PRIMARY KEY,
                    video_id INT NOT NULL,
                    report_id INT NOT NULL,
                    thumbnail_id INT,
                    change_type ENUM('title', 'views', 'availability', 'thumbnail') NOT NULL,
                    change_value TEXT,
                    FOREIGN KEY (video_id) REFERENCES ytp_videos(video_id)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (report_id) REFERENCES ytp_reports(report_id)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY (thumbnail_id) REFERENCES ytp_thumbnails(thumbnail_id) ON DELETE CASCADE ON UPDATE CASCADE    
                )
            ''')

            def update_collumnns_in_table(table_name, required_columns, expected_types, expected_nullable=None):
                cursor.execute(f"""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = DATABASE()
                """)

                columns_obj = cursor.fetchall()
                columns = {row[0] for row in columns_obj}
                column_types = {row[0]: row[1] for row in columns_obj}
                column_nullable = {row[0]: row[2] for row in columns_obj}
                if expected_nullable is None:
                    expected_nullable = {}

                # Execute ALTER TABLE statements for each required column
                for col_name, alter_sql in required_columns.items():
                    if col_name not in columns:
                        print(f"Adding or modifying column: {col_name}")
                        cursor.execute(f"ALTER TABLE {table_name} {alter_sql}")
                    else:
                        is_add_column_sql = alter_sql.strip().upper().startswith('ADD COLUMN')
                        existing_type = column_types.get(col_name, '').lower()
                        expected_type = expected_types[col_name].lower()
                        existing_nullable = column_nullable.get(col_name, 'YES')
                        expected_nullable_value = expected_nullable.get(col_name)
                        nullable_mismatch = (
                            not is_add_column_sql
                            and
                            expected_nullable_value is not None
                            and ((expected_nullable_value and existing_nullable != 'YES') or (not expected_nullable_value and existing_nullable != 'NO'))
                        )
                        if existing_type != expected_type or nullable_mismatch:
                            print(
                                f"Modifying column: {col_name} "
                                f"(type {existing_type} -> {expected_type}, nullable {existing_nullable})"
                            )
                            cursor.execute(f"ALTER TABLE {table_name} {alter_sql}")

            # Update video details
            
            required_columns = {
                'report_id': "ADD COLUMN report_id INT",
                'change_type': "MODIFY COLUMN change_type ENUM('title', 'views', 'availability', 'thumbnail') NOT NULL",
                'change_value': "MODIFY COLUMN change_value TEXT",
                'thumbnail_id': "ADD COLUMN thumbnail_id INT, ADD CONSTRAINT fk_video_details_thumbnail FOREIGN KEY (thumbnail_id) REFERENCES ytp_thumbnails(thumbnail_id) ON DELETE CASCADE ON UPDATE CASCADE"
            }
            expected_types = {
                'report_id': 'int',
                'change_type': "enum('title','views','availability','thumbnail')",
                'change_value': 'text',
                'thumbnail_id': 'int'
            }
            expected_nullable = {
                'report_id': True,
                'change_type': False,
                'change_value': True,
                'thumbnail_id': False
            }

            update_collumnns_in_table('ytp_video_details', required_columns, expected_types, expected_nullable)

            required_columns = {
                'source_url': "ADD COLUMN source_url VARCHAR(1024)"
            }
            expected_types = {
                'source_url': 'varchar(1024)'
            }
            expected_nullable = {
                'source_url': True
            }

            update_collumnns_in_table('ytp_thumbnails', required_columns, expected_types, expected_nullable)

            # Update playlist details

            required_columns = {
                'report_id': "ADD COLUMN report_id INT",
                'change_type': "MODIFY COLUMN change_type ENUM('title', 'description', 'privacy', 'thumbnail')",
                'change_value': "MODIFY COLUMN change_value TEXT"
            }
            expected_types = {
                'report_id': 'int',
                'change_type': "enum('title','description','privacy','thumbnail')",
                'change_value': 'text'
            }
            expected_nullable = {
                'report_id': True,
                'change_type': False,
                'change_value': True
            }

            update_collumnns_in_table('ytp_playlist_details', required_columns, expected_types, expected_nullable)

            # Ensure thumbnail_id and its constraint exist in ytp_playlist_details
            cursor.execute(f"""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'ytp_playlist_details' AND COLUMN_NAME = 'thumbnail_id' AND TABLE_SCHEMA = DATABASE()
            """)
            if not cursor.fetchone():
                try:
                    cursor.execute("""
                        ALTER TABLE ytp_playlist_details 
                        ADD COLUMN thumbnail_id INT,
                        ADD CONSTRAINT fk_playlist_details_thumbnail 
                        FOREIGN KEY (thumbnail_id) REFERENCES ytp_thumbnails(thumbnail_id) 
                        ON DELETE CASCADE ON UPDATE CASCADE
                    """)
                    print("Added thumbnail_id column to ytp_playlist_details")
                except Error as e:
                    print(f"Info: thumbnail_id column already exists or constraint exists: {e}")

            conn.commit()
            
    except Error as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_playlist_metadata_if_changed(cursor, playlist_id, report_id, playlist_name, playlist_description, playlist_privacy, playlist_thumbnail, downloaded_thumbnails_cache=None):
    playlist_name = normalize_text(playlist_name, default='Unknown Playlist')
    playlist_description = normalize_text(playlist_description, default='')
    playlist_privacy = normalize_text(playlist_privacy, default='unknown')

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

    cursor.execute('''
        SELECT d.change_value
        FROM ytp_reports r
        JOIN ytp_playlist_details d ON r.report_id = d.report_id
        WHERE r.playlist_id = %s AND d.change_type = 'privacy' AND r.report_id < %s
        ORDER BY r.report_id DESC
        LIMIT 1
    ''', (playlist_id, report_id))
    previous_privacy = cursor.fetchone()

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

    # If privacy has changed, insert a new record
    if not previous_privacy or previous_privacy[0] != playlist_privacy:
        cursor.execute('''
            INSERT INTO ytp_playlist_details (report_id, change_type, change_value)
            VALUES (%s, 'privacy', %s)
        ''', (report_id, playlist_privacy))
    
    # If thumbnail has changed, insert a new record
    # Use cache to avoid downloading the same thumbnail multiple times in one session
    if downloaded_thumbnails_cache is None:
        downloaded_thumbnails_cache = {}
    
    # First, calculate the SHA256 hash of the new thumbnail URL
    if playlist_thumbnail:
        cached_thumbnail_id = get_cached_thumbnail_id(cursor, playlist_thumbnail)
        if cached_thumbnail_id:
            print(f"[Playlist] Thumbnail already in database (id: {cached_thumbnail_id})")
            cursor.execute('''
                SELECT t.sha256_hash
                FROM ytp_reports r
                JOIN ytp_playlist_details d ON r.report_id = d.report_id
                JOIN ytp_thumbnails t ON d.thumbnail_id = t.thumbnail_id
                WHERE r.playlist_id = %s AND d.change_type = 'thumbnail' AND r.report_id < %s
                ORDER BY r.report_id DESC
                LIMIT 1
            ''', (playlist_id, report_id))
            last_thumbnail_hash_result = cursor.fetchone()
            last_thumbnail_hash = last_thumbnail_hash_result[0] if last_thumbnail_hash_result else None
            if last_thumbnail_hash is None:
                cursor.execute('''
                    INSERT INTO ytp_playlist_details (report_id, change_type, change_value, thumbnail_id)
                    VALUES (%s, 'thumbnail', %s, %s)
                ''', (report_id, playlist_thumbnail, cached_thumbnail_id))
            return

        # Check if we already have this thumbnail in cache or database
        incoming_image_hash = None
        incoming_image_content = None
        
        # Check local cache first
        if playlist_thumbnail in downloaded_thumbnails_cache:
            incoming_image_hash, incoming_image_content = downloaded_thumbnails_cache[playlist_thumbnail]
            print(f"[Playlist] Using cached thumbnail")
        else:
            # Download the thumbnail
            incoming_image_content = download_image(playlist_thumbnail)
            if incoming_image_content:
                incoming_image_hash = calculate_sha256(incoming_image_content)
                # Cache it for reuse in this session
                if incoming_image_hash:
                    downloaded_thumbnails_cache[playlist_thumbnail] = (incoming_image_hash, incoming_image_content)
        
        if incoming_image_hash and incoming_image_content:
            # Check if the hash already exists in the ytp_thumbnails table
            cursor.execute('''
                SELECT thumbnail_id FROM ytp_thumbnails WHERE sha256_hash = %s
            ''', (incoming_image_hash,))
            thumbnail_result = cursor.fetchone()

            if thumbnail_result:
                thumbnail_id = thumbnail_result[0]
                print(f"[Playlist] Thumbnail already in database (id: {thumbnail_id})")
            else:
                # Save the image to disk and insert a new record into ytp_thumbnails
                file_name = save_image(incoming_image_content)
                if file_name:
                    cursor.execute('''
                        INSERT INTO ytp_thumbnails (file_name, source_url, sha256_hash)
                        VALUES (%s, %s, %s)
                    ''', (file_name, playlist_thumbnail, incoming_image_hash))
                    thumbnail_id = cursor.lastrowid
                    print(f"[Playlist] Saved new thumbnail: {file_name}")
                else:
                    print("Warning: Failed to save playlist thumbnail to disk")
                    thumbnail_id = None

            # Get the last recorded thumbnail hash for this playlist
            cursor.execute('''
                SELECT t.sha256_hash
                FROM ytp_reports r
                JOIN ytp_playlist_details d ON r.report_id = d.report_id
                JOIN ytp_thumbnails t ON d.thumbnail_id = t.thumbnail_id
                WHERE r.playlist_id = %s AND d.change_type = 'thumbnail' AND r.report_id < %s
                ORDER BY r.report_id DESC
                LIMIT 1
            ''', (playlist_id, report_id))
            last_thumbnail_hash_result = cursor.fetchone()
            last_thumbnail_hash = last_thumbnail_hash_result[0] if last_thumbnail_hash_result else None

            # If the thumbnail has changed, insert a new record into ytp_playlist_details
            if incoming_image_hash != last_thumbnail_hash and thumbnail_id:
                cursor.execute('''
                    INSERT INTO ytp_playlist_details (report_id, change_type, change_value, thumbnail_id)
                    VALUES (%s, 'thumbnail', %s, %s)
                ''', (report_id, playlist_thumbnail, thumbnail_id))
        else:
            print("Warning: Failed to download or process playlist thumbnail")

def update_video_metadata_if_changed(cursor, video_id, video_title, view_count, availability, report_id, video_thumbnail, downloaded_thumbnails_cache=None):
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
    
    if video_thumbnail:
        cached_thumbnail_id = get_cached_thumbnail_id(cursor, video_thumbnail)
        if cached_thumbnail_id:
            print(f"[Video {video_id}] Thumbnail already in database (id: {cached_thumbnail_id})")
            cursor.execute('''
                SELECT t.sha256_hash
                FROM ytp_video_details d
                JOIN ytp_thumbnails t ON d.thumbnail_id = t.thumbnail_id
                WHERE d.video_id = %s AND d.change_type = 'thumbnail' AND d.report_id < %s
                ORDER BY d.report_id DESC
                LIMIT 1
            ''', (video_id, report_id))
            last_thumbnail_hash_result = cursor.fetchone()
            last_thumbnail_hash = last_thumbnail_hash_result[0] if last_thumbnail_hash_result else None
            if last_thumbnail_hash is None:
                cursor.execute('''
                    INSERT INTO ytp_video_details (video_id, report_id, change_type, change_value, thumbnail_id)
                    VALUES (%s, %s, 'thumbnail', %s, %s)
                ''', (video_id, report_id, video_thumbnail, cached_thumbnail_id))
            return

        # Use cache to avoid downloading the same thumbnail multiple times
        if downloaded_thumbnails_cache is None:
            downloaded_thumbnails_cache = {}
        
        # Check if we already have this thumbnail in cache
        incoming_image_hash = None
        incoming_image_content = None
        
        if video_thumbnail in downloaded_thumbnails_cache:
            incoming_image_hash, incoming_image_content = downloaded_thumbnails_cache[video_thumbnail]
        else:
            # Download the thumbnail
            incoming_image_content = download_image(video_thumbnail)
            if incoming_image_content:
                incoming_image_hash = calculate_sha256(incoming_image_content)
                # Cache it for reuse in this session
                if incoming_image_hash:
                    downloaded_thumbnails_cache[video_thumbnail] = (incoming_image_hash, incoming_image_content)
        
        if incoming_image_hash and incoming_image_content:
            # Check if the hash already exists in the ytp_thumbnails table
            cursor.execute('''
                SELECT thumbnail_id FROM ytp_thumbnails WHERE sha256_hash = %s
            ''', (incoming_image_hash,))
            thumbnail_result = cursor.fetchone()

            if thumbnail_result:
                thumbnail_id = thumbnail_result[0]
            else:
                # Save the image to disk and insert a new record into ytp_thumbnails
                file_name = save_image(incoming_image_content)
                if file_name:
                    cursor.execute('''
                        INSERT INTO ytp_thumbnails (file_name, source_url, sha256_hash)
                        VALUES (%s, %s, %s)
                    ''', (file_name, video_thumbnail, incoming_image_hash))
                    thumbnail_id = cursor.lastrowid
                else:
                    print("Warning: Failed to save thumbnail image to disk")
                    thumbnail_id = None

            # Get the last recorded thumbnail hash for this video
            cursor.execute('''
                SELECT t.sha256_hash
                FROM ytp_video_details d
                JOIN ytp_thumbnails t ON d.thumbnail_id = t.thumbnail_id
                WHERE d.video_id = %s AND d.change_type = 'thumbnail' AND d.report_id < %s
                ORDER BY d.report_id DESC
                LIMIT 1
            ''', (video_id, report_id))
            last_thumbnail_hash_result = cursor.fetchone()
            last_thumbnail_hash = last_thumbnail_hash_result[0] if last_thumbnail_hash_result else None

            # If the thumbnail has changed, insert a new record into ytp_video_details
            if incoming_image_hash != last_thumbnail_hash and thumbnail_id:
                cursor.execute('''
                    INSERT INTO ytp_video_details (video_id, report_id, change_type, change_value, thumbnail_id)
                    VALUES (%s, %s, 'thumbnail', %s, %s)
                ''', (video_id, report_id, video_thumbnail, thumbnail_id))



    
def add_report(host, user, password, database, video_titles, saved_video_links, playlist_name, playlist_url, video_durations, uploader, uploader_url, view_count, isvalidl, playlist_description, playlist_privacy, playlist_thumbnail, video_thumbnails=None, downloaded_thumbnails_cache=None, batch_size=50):
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
            report_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute('''
            INSERT INTO ytp_reports (report_date, playlist_id)
            VALUES (%s, %s)
            ''', (report_date, playlist_id))
            report_id = cursor.lastrowid
            update_playlist_metadata_if_changed(cursor, playlist_id, report_id, playlist_name, playlist_description, playlist_privacy, playlist_thumbnail, downloaded_thumbnails_cache)

            total_videos = len(video_titles)

            # Add videos and report details
            for index, (title, link, length, uploader_row, uploader_url_row, view_count_row, isvalid_row) in enumerate(zip(video_titles, saved_video_links, video_durations, uploader, uploader_url, view_count, isvalidl)):
                print(f"[Video {index + 1}/{total_videos}] Processing {title}")
                if length is None:
                    length = 0 

                # Check if video already exists
                cursor.execute('''
                SELECT video_id FROM ytp_videos WHERE video_url = %s
                ''', (link,))
                video_result = cursor.fetchone()

                if video_result:
                    video_id = video_result[0]
                    print(f"[Video {index + 1}/{total_videos}] Duplicate video in playlist (or already in DB), reusing ID: {video_id}")
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
                video_thumbnail = video_thumbnails[index] if video_thumbnails and index < len(video_thumbnails) else None
                update_video_metadata_if_changed(cursor, video_id, title, view_count_row, isvalid_row, report_id, video_thumbnail, downloaded_thumbnails_cache)

                if batch_size and (index + 1) % batch_size == 0:
                    conn.commit()
                    print(f"[DB] Committed batch through video {index + 1}/{total_videos}")

            conn.commit()
            return True
    except Error as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()