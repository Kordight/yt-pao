import { useEffect, useState } from 'react'
import { API_BASE_URL, DEFAULT_THUMBNAIL, formatCompactNumber, formatDuration, formatPlaylistDuration, resolveThumbnailSrc } from '../utils/formatters'
import {
  buildCsvExport,
  buildHtmlExport,
  buildJsonExport,
  buildSqlExport,
  buildTxtExport,
  downloadTextFile,
  getExportFileName,
} from '../utils/reportExporters'

function PlaylistPage({ playlistId, onBack, activeTask, onStartTask, appVersion }) {
  const [selectedPlaylist, setSelectedPlaylist] = useState(null)
  const [reports, setReports] = useState([])
  const [selectedReportIndex, setSelectedReportIndex] = useState(0)
  const [playlistSnapshot, setPlaylistSnapshot] = useState(null)
  const [videoFilter, setVideoFilter] = useState('all')
  const [selectedExportFormats, setSelectedExportFormats] = useState(['csv', 'sql', 'txt', 'json', 'html'])
  const [isLoadingReports, setIsLoadingReports] = useState(true)
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(false)
  const [isRunningReport, setIsRunningReport] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false)
  const [error, setError] = useState('')
  const [actionStatus, setActionStatus] = useState('')
  const availableExportFormats = ['csv', 'sql', 'txt', 'json', 'html']

  useEffect(() => {
    const controller = new AbortController()

    async function fetchReports() {
      try {
        setIsLoadingReports(true)
        setError('')

        const response = await fetch(`${API_BASE_URL}/api/playlists/${playlistId}/reports`, {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        const nextReports = Array.isArray(data.reports) ? data.reports : []
        setReports(nextReports)
        if (nextReports.length > 0) {
          setSelectedReportIndex(nextReports.length - 1)
        }
      } catch (requestError) {
        if (requestError.name !== 'AbortError') {
          console.error('Error fetching reports:', requestError)
          setError('Failed to load playlist reports.')
        }
      } finally {
        setIsLoadingReports(false)
      }
    }

    fetchReports()

    return () => controller.abort()
  }, [playlistId])

  useEffect(() => {
    if (reports.length === 0) {
      return undefined
    }

    const report = reports[selectedReportIndex] || reports[reports.length - 1]
    if (!report) {
      return undefined
    }

    const controller = new AbortController()

    async function fetchSnapshot() {
      try {
        setIsLoadingSnapshot(true)
        setError('')

        const response = await fetch(
          `${API_BASE_URL}/api/playlists/${playlistId}/reports/${report.report_id}`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        setPlaylistSnapshot(data)
        setSelectedPlaylist(data)
      } catch (requestError) {
        if (requestError.name !== 'AbortError') {
          console.error('Error fetching playlist snapshot:', requestError)
          setError('Failed to load the selected report snapshot.')
        }
      } finally {
        setIsLoadingSnapshot(false)
      }
    }

    fetchSnapshot()

    return () => controller.abort()
  }, [playlistId, reports, selectedReportIndex])

  useEffect(() => {
    if (!activeTask) {
      return
    }

    if (activeTask.status === 'completed') {
      setActionStatus('Report completed! Refreshing data...')

      const reportsResponse = fetch(`${API_BASE_URL}/api/playlists/${playlistId}/reports`)
        .then(res => res.json())
        .then(reportsData => {
          const nextReports = Array.isArray(reportsData.reports) ? reportsData.reports : []
          setReports(nextReports)
          if (nextReports.length > 0) {
            setSelectedReportIndex(nextReports.length - 1)
          }
        })
        .catch(error => console.error('Error refreshing reports:', error))
    } else if (activeTask.status === 'error') {
      setActionStatus(`Error: ${activeTask.message}`)
    }
  }, [activeTask?.taskId, activeTask?.status])

  const currentReport = reports[selectedReportIndex] || reports[reports.length - 1] || null
  const reportCounts = reports.map((report) => Number(report.video_count ?? 0))
  const showReportTrend = reports.length > 5 && reportCounts.length > 0
  const trendMin = reportCounts.length > 0 ? Math.min(...reportCounts) : 0
  const trendMax = reportCounts.length > 0 ? Math.max(...reportCounts) : 0
  const trendRange = Math.max(trendMax - trendMin, 1)
  const videos = playlistSnapshot?.videos || []
  const filteredVideos = videos.filter((video) => {
    if (videoFilter === 'available') {
      return Number(video.valid) === 1
    }
    if (videoFilter === 'unavailable') {
      return Number(video.valid) === 0
    }
    return true
  })

  const playlistTitle =
    playlistSnapshot?.playlist_title || selectedPlaylist?.playlist_title || selectedPlaylist?.playlist_name || 'Untitled'
  const playlistDescription = playlistSnapshot?.playlist_description || selectedPlaylist?.playlist_description || ''
  const playlistThumbnail =
    playlistSnapshot?.playlist_thumbnail_url || selectedPlaylist?.playlist_thumbnail_url || DEFAULT_THUMBNAIL
  const playlistAuthor = playlistSnapshot?.playlist_author || selectedPlaylist?.playlist_author || 'Unknown author'
  const playlistAuthorUrl = playlistSnapshot?.playlist_author_url || selectedPlaylist?.playlist_author_url || '#'
  const playlistUrl = playlistSnapshot?.playlist_url || selectedPlaylist?.playlist_url || '#'
  const playlistPrivacy = playlistSnapshot?.playlist_privacy || 'unknown'

  const runReport = async () => {
    try {
      setIsRunningReport(true)
      setActionStatus('Starting report generation...')

      const response = await fetch(`${API_BASE_URL}/api/playlists/${playlistId}/reports`, {
        method: 'POST',
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`)
      }

      onStartTask(data.task_id)
      setActionStatus(data.message || 'Report generation started...')
    } catch (requestError) {
      console.error('Error starting report generation:', requestError)
      setActionStatus('Could not start report generation.')
      setIsRunningReport(false)
    }
  }

  const toggleExportFormat = (format) => {
    setSelectedExportFormats((currentFormats) => {
      if (currentFormats.includes(format)) {
        return currentFormats.filter((item) => item !== format)
      }

      return [...currentFormats, format]
    })
  }

  const exportCurrentReport = async () => {
    if (!playlistSnapshot) {
      setActionStatus('Load a report snapshot before exporting.')
      return
    }

    try {
      setIsExporting(true)
      setActionStatus('Exporting current report...')

      const snapshot = {
        ...playlistSnapshot,
        app_version: appVersion,
      }
      const exportDate = snapshot.report_date || new Date().toISOString().replace(/[:.]/g, '-')
      const fileBaseName = getExportFileName(snapshot.playlist_name || playlistTitle, snapshot.report_id || selectedReportIndex + 1, exportDate)

      if (selectedExportFormats.includes('csv')) {
        downloadTextFile(`${fileBaseName}.csv`, buildCsvExport(snapshot), 'text/csv;charset=utf-8')
      }
      if (selectedExportFormats.includes('sql')) {
        downloadTextFile(`${fileBaseName}.sql`, buildSqlExport(snapshot), 'application/sql;charset=utf-8')
      }
      if (selectedExportFormats.includes('txt')) {
        downloadTextFile(`${fileBaseName}.txt`, buildTxtExport(snapshot), 'text/plain;charset=utf-8')
      }
      if (selectedExportFormats.includes('json')) {
        downloadTextFile(`${fileBaseName}.json`, buildJsonExport(snapshot), 'application/json;charset=utf-8')
      }
      if (selectedExportFormats.includes('html')) {
        downloadTextFile(`${fileBaseName}.html`, buildHtmlExport(snapshot), 'text/html;charset=utf-8')
      }

      setActionStatus('Report exported successfully.')
    } catch (requestError) {
      console.error('Error exporting report:', requestError)
      setActionStatus('Could not export the current report.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <section className="yt-detail">
      <header className="yt-detail__topbar">
        <button className="yt-backButton" type="button" onClick={onBack}>
          ← Back to playlists
        </button>
        <div className="yt-detail__topbarMeta">
          <span>{selectedPlaylist?.playlist_name || playlistTitle}</span>
          <span>{playlistSnapshot?.video_count ?? selectedPlaylist?.video_count ?? 0} videos</span>
        </div>
      </header>

      <div className="yt-detail__hero">
        <div className="yt-detail__heroMedia">
          <img className="yt-detail__heroThumb" src={resolveThumbnailSrc(playlistThumbnail)} alt={playlistTitle} />
        </div>

        <div className="yt-detail__heroContent">
          <p className="yt-page__eyebrow">Report view</p>
          <h1 className="yt-detail__title">{playlistTitle}</h1>
          <p className="yt-detail__metaLine">
            {playlistAuthor}
            {' '}
            • {playlistPrivacy}
            {' '}
            • {currentReport?.report_date || playlistSnapshot?.report_date || 'no date available'}
            {' '}
            • {formatPlaylistDuration(playlistSnapshot?.playlist_duration)} duration
          </p>
          {playlistDescription && <p className="yt-detail__description">{playlistDescription}</p>}

          <div className="yt-detail__links">
            {playlistUrl !== '#' && (
              <a href={playlistUrl} target="_blank" rel="noreferrer" className="yt-runReportButton">
                Open playlist
              </a>
            )}
            {playlistAuthorUrl !== '#' && (
              <a href={playlistAuthorUrl} target="_blank" rel="noreferrer" className="yt-runReportButton">
                Author channel
              </a>
            )}
            <button className="yt-runReportButton" type="button" onClick={runReport} disabled={!!activeTask}>
              {activeTask ? 'Running report...' : 'Run report'}
            </button>
          </div>

          {actionStatus && <p className="yt-register__status">{actionStatus}</p>}
        </div>
      </div>

      <div className="yt-timeline">
        <div className="yt-timeline__header">
          <span>Time machine</span>
          <span>
            {/* Wskaźnik ładowania podczas przesuwania suwaka */}
            {isLoadingSnapshot && <span className="yt-spinner">Loading... </span>}
            Report {reports.length > 0 ? selectedReportIndex + 1 : 0}/{reports.length || 0}
            {currentReport?.report_id ? ` • ID ${currentReport.report_id}` : ''}
          </span>
        </div>

        {showReportTrend && (
          <div className="yt-timeline__trendCard">
            <div className="yt-timeline__trendHeader">
              <span>Report size trend</span>
              <span>{trendMin} - {trendMax} videos</span>
            </div>
            <div className="yt-timeline__trendChart" role="img" aria-label="Trend of video counts across reports">
              <svg className="yt-timeline__trendSvg" viewBox="0 0 100 40" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="trendGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="rgba(255, 59, 48, 0.4)" />
                    <stop offset="100%" stopColor="rgba(255, 59, 48, 0.0)" />
                  </linearGradient>
                </defs>
                <polygon
                  fill="url(#trendGradient)"
                  points={`0,40 ${reportCounts.map((count, index) => {
                    const x = reports.length === 1 ? 0 : (index / (reports.length - 1)) * 100
                    const y = 38 - ((count - trendMin) / trendRange) * 34
                    return `${x},${y}`
                  }).join(' ')} 100,40`}
                />
                <polyline
                  className="yt-timeline__trendLine"
                  fill="none"
                  stroke="#ff3b30"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                  points={reportCounts.map((count, index) => {
                    const x = reports.length === 1 ? 0 : (index / (reports.length - 1)) * 100
                    const y = 38 - ((count - trendMin) / trendRange) * 34
                    return `${x},${y}`
                  }).join(' ')}
                />
                {reports.length > 0 && (
                  <circle
                    className="yt-timeline__trendPoint yt-timeline__trendPoint--active"
                    cx={reports.length === 1 ? 0 : (selectedReportIndex / (reports.length - 1)) * 100}
                    cy={38 - ((reportCounts[selectedReportIndex] - trendMin) / trendRange) * 34}
                    r="1.5"
                    fill="#fff"
                    stroke="#ff3b30"
                    strokeWidth="3"
                    vectorEffect="non-scaling-stroke"
                  />
                )}
              </svg>
            </div>
          </div>
        )}

        <input
          className="yt-timeline__range"
          type="range"
          min="0"
          max={Math.max(reports.length - 1, 0)}
          value={selectedReportIndex}
          onChange={(event) => setSelectedReportIndex(Number(event.target.value))}
          disabled={reports.length <= 1}
        />
        <div className="yt-timeline__labels">
          <span>{reports[0]?.report_date || ' '}</span>
          <span>{currentReport?.report_date || ' '}</span>
          <span>{reports[reports.length - 1]?.report_date || ' '}</span>
        </div>

        {/* --- Nowoczesny, oddzielny blok eksportu --- */}
        <div className="yt-timeline__exportBlock">
          <details className="yt-exportAccordion">
            <summary className="yt-exportAccordion__summary">Export snapshot options</summary>
            <div className="yt-exportAccordion__content">
              <div className="yt-exportPanel__options">
                {availableExportFormats.map((format) => (
                  <label key={format} className={selectedExportFormats.includes(format) ? 'yt-exportPanel__option yt-exportPanel__option--active' : 'yt-exportPanel__option'}>
                    <input
                      type="checkbox"
                      checked={selectedExportFormats.includes(format)}
                      onChange={() => toggleExportFormat(format)}
                      disabled={!!activeTask}
                    />
                    <span>{format}</span>
                  </label>
                ))}
              </div>
              <button
                className="yt-runReportButton"
                type="button"
                onClick={exportCurrentReport}
                disabled={isExporting || isLoadingSnapshot || !playlistSnapshot || selectedExportFormats.length === 0}
              >
                {isExporting ? 'Exporting...' : 'Export current snapshot'}
              </button>
            </div>
          </details>
        </div>

        <footer className="yt-detail__footer">
          <span>YT-PAO version {appVersion || '0.0.0'}</span>
        </footer>
      </div>

      <div className="yt-filters">
        <button className={videoFilter === 'all' ? 'yt-filter yt-filter--active' : 'yt-filter'} type="button" onClick={() => setVideoFilter('all')}>
          All
        </button>
        <button className={videoFilter === 'available' ? 'yt-filter yt-filter--active' : 'yt-filter'} type="button" onClick={() => setVideoFilter('available')}>
          Available
        </button>
        <button className={videoFilter === 'unavailable' ? 'yt-filter yt-filter--active' : 'yt-filter'} type="button" onClick={() => setVideoFilter('unavailable')}>
          Unavailable
        </button>
      </div>

      {(isLoadingReports || isLoadingSnapshot) && <p className="yt-state">Loading playlist report...</p>}
      {!isLoadingReports && !isLoadingSnapshot && error && <p className="yt-state yt-state--error">{error}</p>}

      {!isLoadingReports && !isLoadingSnapshot && !error && (
        <section className="yt-videoGrid" aria-label="Videos in playlist">
          {filteredVideos.length === 0 ? (
            <p className="yt-state">No videos match the selected filter.</p>
          ) : (
            filteredVideos.map((video) => {
              const videoThumbnail = resolveThumbnailSrc(video.display_thumbnail_url || video.thumbnail_url)
              const displayTitle = video.display_title || video.title || 'Untitled'
              const isUnavailable = Number(video.valid) === 0
              const waybackSearchUrl = video.wayback_search_url

              return (
                <article
                  className={isUnavailable ? 'yt-videoCard yt-videoCard--unavailable' : 'yt-videoCard'}
                  key={video.video_id}
                >
                  <a href={video.url} target="_blank" rel="noreferrer" className="yt-videoCard__thumbLink">
                    <div className="yt-videoCard__thumbWrap">
                      <img className="yt-videoCard__thumb" src={videoThumbnail} alt={displayTitle} />
                      <span className="yt-videoCard__badge">{formatDuration(video.duration)}</span>
                    </div>
                  </a>

                  <div className="yt-videoCard__body">
                    <h2 className="yt-videoCard__title">{displayTitle}</h2>
                    <p className="yt-videoCard__meta">
                      {video.uploader || 'Unknown author'}
                      {' '}
                      • {formatCompactNumber(video.view_count ?? 0)} views
                    </p>
                    <p className="yt-videoCard__availability">
                      {isUnavailable ? 'Unavailable' : 'Available'}
                    </p>
                    {isUnavailable && video.recovered_from_history && (
                      <p className="yt-videoCard__historyHint">Recovered the last valid state from the database.</p>
                    )}
                    {isUnavailable && waybackSearchUrl && (
                      <a className="yt-videoCard__waybackButton" href={waybackSearchUrl} target="_blank" rel="noreferrer">
                        Search in Wayback Machine
                      </a>
                    )}
                  </div>
                </article>
              )
            })
          )}
        </section>
      )}
      <footer className="yt-detail__footer">
        <span>YT-PAO version {appVersion || '0.0.0'}</span>
      </footer>
    </section>

  )
}

export default PlaylistPage