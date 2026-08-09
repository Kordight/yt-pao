import csv
import html
import json
import os
from datetime import datetime

from html_manager import generate_html_list, generate_html_list_invalid_videos, read_html_template, extract_head_and_body
from mySQL_manager import add_report, create_database


SUPPORTED_REPORT_FORMATS = {'cmd', 'txt', 'json', 'csv', 'html', 'mySQL'}


def build_output_folder(playlist_name, playlist_id):
    folder_path = f"Output/{playlist_name}_{playlist_id}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def _compose_text_table(playlist_data, videos, calculate_total_duration):
    total_duration_str = calculate_total_duration(playlist_data)
    playlist_data_display = dict(playlist_data)
    playlist_data_display["Total Duration"] = total_duration_str

    def format_table(headers, rows):
        column_widths = [max(len(str(cell)) for cell in col) for col in zip(headers, *rows)]
        header_row = " | ".join(f"{header:{width}}" for header, width in zip(headers, column_widths))
        separator = "-+-".join("-" * width for width in column_widths)
        data_rows = "\n".join(
            " | ".join(f"{str(cell):{width}}" for cell, width in zip(row, column_widths)) for row in rows
        )
        return f"{header_row}\n{separator}\n{data_rows}"

    playlist_headers = ["Key", "Value"]
    playlist_rows = list(playlist_data_display.items())
    playlist_table = format_table(playlist_headers, playlist_rows)

    video_headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "bValid"]
    video_rows = []
    for index, video in enumerate(videos):
        video_rows.append([
            index + 1,
            getattr(video, 'title', 'N/A'),
            getattr(video, 'url', 'N/A'),
            getattr(video, 'duration', 'N/A'),
            getattr(video, 'uploader', 'N/A'),
            getattr(video, 'uploader_url', 'N/A'),
            getattr(video, 'view_count', 'N/A'),
            getattr(video, 'valid', 'N/A'),
        ])

    video_table = format_table(video_headers, video_rows)
    return playlist_table, video_table


def _save_cmd_report(playlist_data, videos, calculate_total_duration):
    playlist_table, video_table = _compose_text_table(playlist_data, videos, calculate_total_duration)
    return {
        'status': 'success',
        'playlist_table': playlist_table,
        'video_table': video_table,
    }


def _save_txt_report(folder_path, list_mode, date_time, playlist_data, videos, calculate_total_duration):
    playlist_table, video_table = _compose_text_table(playlist_data, videos, calculate_total_duration)
    file_path = os.path.join(folder_path, f"{list_mode}_{date_time}.txt")
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(f"Playlist Data:\n\n{playlist_table}\n")
        file.write(f"\nVideo Data:\n\n{video_table}")
    return {'status': 'success', 'file_path': file_path}


def _save_json_report(folder_path, list_mode, date_time, playlist_data, videos):
    file_path = os.path.join(folder_path, f"{list_mode}_{date_time}.json")
    with open(file_path, 'w', encoding='utf-8') as file:
        videos_dict = [video.__dict__ for video in videos]
        json.dump({'playlist_data': playlist_data, 'videos': videos_dict}, file, indent=4)
    return {'status': 'success', 'file_path': file_path}


def _save_csv_report(folder_path, list_mode, date_time, videos):
    file_path = os.path.join(folder_path, f"{list_mode}_{date_time}.csv")
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        headers = ["Lp", "Title", "URL", "Duration", "Uploader", "Uploader URL", "Approximate View Count", "bValid"]
        writer.writerow(headers)
        for index, video in enumerate(videos):
            video_row = [
                index + 1,
                getattr(video, 'title', 'N/A'),
                getattr(video, 'url', 'N/A'),
                getattr(video, 'duration', 'N/A'),
                getattr(video, 'uploader', 'N/A'),
                getattr(video, 'uploader_url', 'N/A'),
                getattr(video, 'view_count', 'N/A'),
                getattr(video, 'valid', 'N/A'),
            ]
            writer.writerow(video_row)
    return {'status': 'success', 'file_path': file_path}


def _save_html_report(folder_path, list_mode, date_time, playlist_name, playlist_link, playlist_data, videos):
    with open('web_template/script_head_template.js', 'r', encoding='utf-8') as js_file:
        js_code = js_file.read()
    with open('web_template/style_template.css', 'r', encoding='utf-8') as css_file:
        css_styles = css_file.read()

    if list_mode == 'unavailable':
        html_list = generate_html_list_invalid_videos(videos, playlist_name, playlist_link)
        html_template_path = 'web_template/html_template_backup_removed_report.html'
        page_title = f'Removed videos for Playlist: {playlist_name}'
    else:
        html_list = generate_html_list(videos, playlist_name, playlist_data['url'], playlist_data)
        html_template_path = 'web_template/html_template_backup_report.html'
        page_title = f'Report for Playlist: {playlist_name}'

    safe_page_title = html.escape(page_title)
    html_template = read_html_template(html_template_path)
    head, body = extract_head_and_body(html_template)

    final_html = f"""<html>
            <head>
                <title>{safe_page_title}</title>
                <script>{js_code}</script>
                <style>{css_styles}</style>
                {head}
            </head>
            <body>
                {body}
                {html_list}
                <footer>
                    <h3>Authors:</h3>
                    <div class='links'><a href='https://github.com/Kordight'><strong>Kordight</strong></a></div>
                </footer>
            </body>
            </html>"""

    file_path = os.path.join(folder_path, f"{list_mode}_{date_time}.html")
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(final_html)
    latest_path = os.path.join(folder_path, f"latest_{list_mode}.html")
    with open(latest_path, 'w', encoding='utf-8') as file:
        file.write(final_html)
    return {'status': 'success', 'file_path': file_path, 'latest_path': latest_path}


def _save_mysql_report(db_config, playlist_data, videos, progress_callback=None):
    db_port = int(db_config.get('port', 3306) or 3306)
    create_database(db_config['host'], db_config['user'], db_config['password'], db_config['database'], db_port)

    downloaded_thumbnails_cache = {}
    video_titles = [video.title for video in videos]
    saved_video_links = [video.url for video in videos]
    video_durations = [video.duration for video in videos]
    uploader = [video.uploader for video in videos]
    uploader_url = [video.uploader_url for video in videos]
    view_count = [video.view_count for video in videos]
    isvalid = [video.valid for video in videos]
    video_thumbnails = [video.thumbnail for video in videos]

    saved = add_report(
        db_config['host'],
        db_config['user'],
        db_config['password'],
        db_config['database'],
        db_port,
        video_titles,
        saved_video_links,
        playlist_data['playlist_name'],
        playlist_data['url'],
        video_durations,
        uploader,
        uploader_url,
        view_count,
        isvalid,
        playlist_data.get('description', ''),
        playlist_data.get('playlist_privacy', 'public'),
        playlist_data.get('playlist_thumbnail', None),
        video_thumbnails,
        downloaded_thumbnails_cache,
        playlist_author=playlist_data.get('uploader', None),
        playlist_author_url=playlist_data.get('uploader_url', None),
        progress_callback=progress_callback
    )

    if not saved:
        raise RuntimeError('Report was not saved to MySQL database.')

    return {'status': 'success', 'saved': True}


def generate_reports_for_formats(
    *,
    formats,
    playlist_data,
    videos,
    list_mode,
    playlist_link,
    calculate_total_duration,
    db_config=None,
    output_folder=None,
    date_time=None,
    progress_callback=None
):
    normalized_formats = []
    for report_format in formats or []:
        if report_format not in normalized_formats:
            normalized_formats.append(report_format)

    if not normalized_formats:
        raise ValueError('At least one report format is required.')

    unsupported_formats = [report_format for report_format in normalized_formats if report_format not in SUPPORTED_REPORT_FORMATS]
    if unsupported_formats:
        raise ValueError(f"Unsupported report format(s): {', '.join(unsupported_formats)}")

    playlist_name = playlist_data['playlist_name']
    playlist_id = playlist_data['url'].split('list=')[-1]
    folder_path = output_folder or build_output_folder(playlist_name, playlist_id)
    current_date_time = date_time or datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    results = {}
    for report_format in normalized_formats:
        try:
            if report_format == 'cmd':
                results[report_format] = _save_cmd_report(playlist_data, videos, calculate_total_duration)
            elif report_format == 'txt':
                results[report_format] = _save_txt_report(folder_path, list_mode, current_date_time, playlist_data, videos, calculate_total_duration)
            elif report_format == 'json':
                results[report_format] = _save_json_report(folder_path, list_mode, current_date_time, playlist_data, videos)
            elif report_format == 'csv':
                results[report_format] = _save_csv_report(folder_path, list_mode, current_date_time, videos)
            elif report_format == 'html':
                results[report_format] = _save_html_report(folder_path, list_mode, current_date_time, playlist_name, playlist_link, playlist_data, videos)
            elif report_format == 'mySQL':
                if db_config is None:
                    raise ValueError('Database configuration is required for mySQL format.')
                results[report_format] = _save_mysql_report(db_config, playlist_data, videos)
        except Exception as error:
            results[report_format] = {'status': 'error', 'error': str(error)}

    return {
        'folder_path': folder_path,
        'date_time': current_date_time,
        'results': results,
    }