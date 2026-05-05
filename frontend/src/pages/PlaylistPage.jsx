import { useEffect, useState } from 'react'
import { API_BASE_URL, DEFAULT_THUMBNAIL, formatCompactNumber, formatDuration, formatPlaylistDuration, resolveThumbnailSrc } from '../utils/formatters'

function PlaylistPage({ playlistId, onBack, activeTask, onStartTask }) {
  const [selectedPlaylist, setSelectedPlaylist] = useState(null)
  const [reports, setReports] = useState([])
  const [selectedReportIndex, setSelectedReportIndex] = useState(0)
  const [playlistSnapshot, setPlaylistSnapshot] = useState(null)
  const [videoFilter, setVideoFilter] = useState('all')
  const [isLoadingReports, setIsLoadingReports] = useState(true)
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(false)
  const [isRunningReport, setIsRunningReport] = useState(false)
  const [error, setError] = useState('')
  const [actionStatus, setActionStatus] = useState('')

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
              <a href={playlistUrl} target="_blank" rel="noreferrer">
                Open playlist
              </a>
            )}
            {playlistAuthorUrl !== '#' && (
              <a href={playlistAuthorUrl} target="_blank" rel="noreferrer">
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
            Report {reports.length > 0 ? selectedReportIndex + 1 : 0}/{reports.length || 0}
            {currentReport?.report_id ? ` • ID ${currentReport.report_id}` : ''}
          </span>
        </div>

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
          <span>{reports[0]?.report_date || '—'}</span>
          <span>{currentReport?.report_date || '—'}</span>
          <span>{reports[reports.length - 1]?.report_date || '—'}</span>
        </div>
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
    </section>
  )
}

export default PlaylistPage