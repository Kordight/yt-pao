function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function toRows(snapshot) {
  return Array.isArray(snapshot?.videos) ? snapshot.videos : []
}

function getPlaylistData(snapshot) {
  return {
    report_id: snapshot?.report_id ?? '',
    report_date: snapshot?.report_date ?? '',
    playlist_id: snapshot?.playlist_id ?? '',
    playlist_name: snapshot?.playlist_name ?? '',
    playlist_title: snapshot?.playlist_title ?? '',
    playlist_url: snapshot?.playlist_url ?? '',
    playlist_description: snapshot?.playlist_description ?? '',
    playlist_privacy: snapshot?.playlist_privacy ?? '',
    playlist_author: snapshot?.playlist_author ?? '',
    playlist_author_url: snapshot?.playlist_author_url ?? '',
    playlist_duration: snapshot?.playlist_duration ?? 0,
    video_count: snapshot?.video_count ?? 0,
  }
}

function stringifySqlValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'NULL'
  }

  if (typeof value === 'number' || typeof value === 'bigint') {
    return String(value)
  }

  if (typeof value === 'boolean') {
    return value ? '1' : '0'
  }

  return `'${String(value).replace(/'/g, "''")}'`
}

function buildHeaders(rows) {
  return [
    'video_id',
    'title',
    'display_title',
    'url',
    'duration',
    'uploader',
    'uploader_url',
    'view_count',
    'valid',
    'availability',
    'thumbnail_url',
    'display_thumbnail_url',
    'recovered_from_history',
    'wayback_search_url',
  ].filter((header) => rows.some((row) => Object.prototype.hasOwnProperty.call(row, header)))
}

export function getExportFileName(playlistName, reportId, reportDate) {
  const safeName = String(playlistName || 'playlist')
    .trim()
    .replace(/[^a-zA-Z0-9-_]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '') || 'playlist'
  const safeDate = String(reportDate || '').trim().replace(/[:\s]+/g, '-') || 'snapshot'
  return `${safeName}_report_${reportId ?? 'latest'}_${safeDate}`
}

export function downloadTextFile(fileName, content, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = fileName
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
}

export function buildCsvExport(snapshot) {
  const rows = toRows(snapshot)
  const headers = buildHeaders(rows)
  const csvRows = [headers.join(',')]

  rows.forEach((row) => {
    csvRows.push(headers.map((header) => {
      const value = row?.[header]
      const normalized = value === null || value === undefined ? '' : String(value)
      return `"${normalized.replace(/"/g, '""')}"`
    }).join(','))
  })

  return csvRows.join('\n')
}

export function buildSqlExport(snapshot) {
  const playlist = getPlaylistData(snapshot)
  const rows = toRows(snapshot)
  const statements = []

  statements.push(`-- YT-PAO export for report ${playlist.report_id}`)
  statements.push('START TRANSACTION;')
  statements.push(`INSERT INTO ytp_reports (report_id, report_date, playlist_id) VALUES (${stringifySqlValue(playlist.report_id)}, ${stringifySqlValue(playlist.report_date)}, ${stringifySqlValue(playlist.playlist_id)});`)

  rows.forEach((row) => {
    statements.push(`-- video ${stringifySqlValue(row?.video_id)}`)
    statements.push(
      'INSERT INTO ytp_report_details (report_id, video_id) VALUES ('
      + `${stringifySqlValue(playlist.report_id)}, ${stringifySqlValue(row?.video_id)});`
    )
  })

  statements.push('COMMIT;')
  return statements.join('\n')
}

export function buildTxtExport(snapshot) {
  const playlist = getPlaylistData(snapshot)
  const rows = toRows(snapshot)
  const lines = []

  lines.push('Playlist Data:')
  lines.push(`Report ID: ${playlist.report_id}`)
  lines.push(`Report Date: ${playlist.report_date}`)
  lines.push(`Playlist Name: ${playlist.playlist_name}`)
  lines.push(`Playlist Title: ${playlist.playlist_title}`)
  lines.push(`Playlist URL: ${playlist.playlist_url}`)
  lines.push(`Description: ${playlist.playlist_description}`)
  lines.push(`Privacy: ${playlist.playlist_privacy}`)
  lines.push(`Author: ${playlist.playlist_author}`)
  lines.push(`Video Count: ${playlist.video_count}`)
  lines.push('')
  lines.push('Video Data:')

  rows.forEach((row, index) => {
    lines.push(`${index + 1}. ${row?.display_title || row?.title || 'Untitled'} | ${row?.url || ''} | ${row?.availability || (Number(row?.valid) ? 'available' : 'unavailable')}`)
  })

  return lines.join('\n')
}

export function buildJsonExport(snapshot) {
  const payload = {
    playlist_data: getPlaylistData(snapshot),
    videos: toRows(snapshot),
  }

  return JSON.stringify(payload, null, 2)
}

export function buildHtmlExport(snapshot) {
  const playlist = getPlaylistData(snapshot)
  const rows = toRows(snapshot)
  const title = escapeHtml(playlist.playlist_title || playlist.playlist_name || 'Playlist report')
  const playlistName = escapeHtml(playlist.playlist_name || 'Untitled')
  const playlistUrl = escapeHtml(playlist.playlist_url || '#')
  const playlistDescription = escapeHtml(playlist.playlist_description || '')
  const reportDate = escapeHtml(playlist.report_date || '')
  const version = escapeHtml(snapshot?.app_version || '0.0.0')

  const tableRows = rows.map((row) => {
    const rowTitle = escapeHtml(row?.display_title || row?.title || 'Untitled')
    const rowUrl = escapeHtml(row?.url || '#')
    const uploader = escapeHtml(row?.uploader || 'Unknown author')
    const duration = escapeHtml(String(row?.duration ?? ''))
    const availability = escapeHtml(row?.availability || (Number(row?.valid) ? 'available' : 'unavailable'))

    return `
      <tr>
        <td>${rowTitle}</td>
        <td><a href="${rowUrl}" target="_blank" rel="noreferrer">${rowUrl}</a></td>
        <td>${uploader}</td>
        <td>${duration}</td>
        <td>${availability}</td>
      </tr>
    `
  }).join('')

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${title}</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f0f0f;
      --panel: rgba(255, 255, 255, 0.04);
      --panel-strong: rgba(255, 255, 255, 0.08);
      --border: rgba(255, 255, 255, 0.08);
      --text: #f1f1f1;
      --muted: #aaaaaa;
      --accent: #ff3b30;
    }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.06), transparent 24%),
        var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }
    .report-shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }
    .report-card {
      border: 1px solid var(--border);
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
      overflow: hidden;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
    }
    .report-hero {
      padding: 24px;
      border-bottom: 1px solid var(--border);
      display: grid;
      gap: 10px;
    }
    .report-hero h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.05;
    }
    .report-meta {
      color: var(--muted);
      line-height: 1.5;
      display: grid;
      gap: 4px;
    }
    .report-body {
      padding: 24px;
      display: grid;
      gap: 18px;
    }
    .report-summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }
    .summary-tile {
      padding: 14px 16px;
      border-radius: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
    }
    .summary-tile__label {
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }
    .summary-tile__value {
      font-size: 1rem;
      line-height: 1.45;
      word-break: break-word;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.18);
    }
    th, td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }
    th {
      background: rgba(255,255,255,0.06);
      color: #ffffff;
      font-size: 0.88rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    tr:nth-child(even) td {
      background: rgba(255,255,255,0.02);
    }
    a {
      color: #ff6b6b;
      word-break: break-word;
    }
    @media (max-width: 720px) {
      .report-shell { padding: 12px; }
      .report-hero, .report-body { padding: 16px; }
      th, td { padding: 12px 10px; }
    }
  </style>
</head>
<body>
  <div class="report-shell">
    <section class="report-card">
      <header class="report-hero">
        <h1>${title}</h1>
        <div class="report-meta">
          <span><strong>Playlist:</strong> <a href="${playlistUrl}" target="_blank" rel="noreferrer">${playlistName}</a></span>
          <span><strong>Report date:</strong> ${reportDate || 'unknown'}</span>
        </div>
      </header>
      <div class="report-body">
        <div class="report-summary">
          <div class="summary-tile"><div class="summary-tile__label">Playlist URL</div><div class="summary-tile__value"><a href="${playlistUrl}" target="_blank" rel="noreferrer">${playlistUrl}</a></div></div>
          <div class="summary-tile"><div class="summary-tile__label">Videos</div><div class="summary-tile__value">${escapeHtml(String(playlist.video_count || rows.length || 0))}</div></div>
          <div class="summary-tile"><div class="summary-tile__label">Privacy</div><div class="summary-tile__value">${escapeHtml(String(playlist.playlist_privacy || 'unknown'))}</div></div>
          <div class="summary-tile"><div class="summary-tile__label">Author</div><div class="summary-tile__value">${escapeHtml(String(playlist.playlist_author || 'Unknown author'))}</div></div>
        </div>
        ${playlistDescription ? `<div class="summary-tile"><div class="summary-tile__label">Description</div><div class="summary-tile__value">${playlistDescription}</div></div>` : ''}
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>URL</th>
              <th>Uploader</th>
              <th>Duration</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows || '<tr><td colspan="5">No videos available.</td></tr>'}
          </tbody>
        </table>
        <footer class="report-footer">
          <span>YT-PAO version ${version}</span>
        </footer>
      </div>
    </section>
  </div>
</body>
</html>`
}