from datetime import datetime
from ytdlp_parser import calculate_total_duration

#Global variable to store the current date
today = datetime.today().strftime("%Y-%m-%d (%H:%M)")

# Function to generate HTML code for the list of similar songs
def generate_html_duplicate_list(songs, playlist_name, playlist_url):
    song_amount=len(songs)
    html_content = "<div class='border-box'><h1>Similar videos</h1><br><h2><a href='"+str(playlist_url)+"'>"+str(playlist_name)+"</a></h2><br><p>Found: <b>" + str(song_amount) + "</b> similar videos in this playlist.<br><i title='Y-M-D'>Date: "+str(today)+"</i></p><br><ol>"
    for song1, song2 in songs:
        html_content += f"<li><a href='{song1.url}' target='_blank'>{song1.title}</a> is similar to: <a href='{song2.url}' target='_blank'>{song2.title}</a> by: {song2.similarity if song2.similarity else ''}</li><br>"
    html_content += "</ol></div>"
    return html_content
# Function to generate HTML code for the playlist and video data
def generate_html_list(songs, playlist_name, playlist_url, playlist_data=None):
    # Sort songs alphabetically by title
    songs_sorted = sorted(songs, key=lambda song: song.title.lower())
    song_amount = len(songs_sorted)

    # Dodaj tabelę z danymi o playliście jeśli przekazano playlist_data
    playlist_overview_table = ""
    if playlist_data is not None:
        playlist_overview_table = generate_html_playlist_overview_table(playlist_data)

    html_content = (
        "<div class='border-box'>"
        "<h1>Playlist backup</h1><br>"
        "<h2><a href='"+str(playlist_url)+"'>"+str(playlist_name)+"</a></h2><br>"
        "<h3>Playlist Overview:</h3>"
        f"{playlist_overview_table}"
        "<h3>List of songs:</h3>"
        "<ol>"
    )
    for song in songs_sorted:
        html_content += f"<li><a href='{song.url}' target='_blank'>{song.title}</a></li><br>"
    html_content += "</ol></div>"
    return html_content
# Function to generate HTML code for the list of invalid videos
def generate_html_list_invalid_videos(deleted_videos, playlist_name, playlist_link):
    song_amount = len(deleted_videos)
    html_content = (
        "<div class='border-box'>"
        "<h1>Playlist backup</h1>"
        "<h2><a href='"+str(playlist_link)+"'>"+str(playlist_name)+"</a></h2><br>"
        "<p>Found: <b>" + str(song_amount) + "</b> videos in this playlist.<br>"
        "<i title='Y-M-D'>Date: "+str(today)+"</i></p><br>"
        "<table>"
        "<tr>"
        "<th>Status</th>"
        "<th>URL</th>"
        "<th>Internet Archive search</th>"
        "</tr>"
    )
    
    for video in deleted_videos:
        if "[Private video]" == video.title: 
            status = "[Private video]"
        elif "[Deleted video]" == video.title:
            status = "[Deleted video]"
        else:
            status = "[Unavailable]"
    
        html_content += f"<tr>"
        html_content += f"<td><a href='{video.url}' target='_blank'>{status}</a></td>"
        html_content += f"<td>{video.url}</td>"
        html_content += f"<td><a href='https://web.archive.org/web/20240000000000*/{video.url}' target='_blank'>Search on Wayback machine</a></td>"
        html_content += f"</tr>"
    
    html_content += "</table></div>"
    
    return html_content
# Function to read HTML template from a file
def read_html_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    return html_content
# Function that splits the HTML content into head and body sections
def extract_head_and_body(html_content):
    head_start = html_content.find('<head>') + len('<head>')
    head_end = html_content.find('</head>')
    body_start = html_content.find('<body>') + len('<body>')
    body_end = html_content.find('</body>')

    head = html_content[head_start:head_end].strip()
    body = html_content[body_start:body_end].strip()
    
    return head, body
# Function to load JavaScript code from a file 
def load_js_code_from_file(file_path): #To do: Add JS features to YT-PAO
    with open(file_path, 'r', encoding='utf-8') as file:
        js_content = file.read()
    return js_content
# Function that return HTML code for the playlist overview table
def generate_html_playlist_overview_table(playlist_data):
    # Mapo keys to labels for better readability
    key_labels = {
        "report_date": "Report Date",
        "playlist_name": "Playlist Name",
        "playlist_id": "Playlist ID",
        "description": "Description",
        "uploader": "Uploader",
        "uploader_url": "Uploader URL",
        "url": "Playlist URL",
        "playlist_duration": "Playlist Duration (s)",
        "video_entries": "Number of Videos",
        "Total Duration": "Total Duration"
    }
    # Prepare the playlist data for display
    playlist_data_display = dict(playlist_data)
    # Add total duration and report date to the playlist_data_display
    playlist_data_display["Total Duration"] = calculate_total_duration(playlist_data)
    playlist_data_display["report_date"] = today  # Set current date as report date
    playlist_headers = ["Key", "Value"]
    # Generate HTML table for playlist overview
    html = "<table class='playlist-overview'>"
    html += "<tr>" + "".join(f"<th>{header}</th>" for header in playlist_headers) + "</tr>"
    for key, value in playlist_data_display.items():
        label = key_labels.get(key, key.replace("_", " ").title())
        # Linki jako <a>
        if isinstance(value, str) and value.startswith("http"):
            value_html = f'<a href="{value}" target="_blank">{value}</a>'
        else:
            value_html = value
        html += f"<tr><td>{label}</td><td>{value_html}</td></tr>"
    html += "</table>"
    return html