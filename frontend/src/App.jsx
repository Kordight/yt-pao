import { useEffect, useState } from 'react'
import './App.css'
import HomePage from './pages/HomePage'
import PlaylistPage from './pages/PlaylistPage'
import { API_BASE_URL } from './utils/formatters'

const ACTIVE_TASKS_STORAGE_KEY = 'ytp_active_tasks'

function isTerminalTask(task) {
  return task?.status === 'completed' || task?.status === 'error'
}

function getCurrentPath() {
  return window.location.pathname
}

function getPlaylistIdFromPath(pathname) {
  const match = pathname.match(/^\/playlist\/(\d+)$/)
  return match ? Number(match[1]) : null
}

function formatTimeSpan(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(remainingSeconds).padStart(2, '0')}s`
  }

  if (minutes > 0) {
    return `${minutes}m ${String(remainingSeconds).padStart(2, '0')}s`
  }

  return `${remainingSeconds}s`
}

function App() {
  const [playlists, setPlaylists] = useState([])
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(true)
  const [playlistsError, setPlaylistsError] = useState('')
  const [registrationStatus, setRegistrationStatus] = useState('')
  const [currentPath, setCurrentPath] = useState(getCurrentPath())
  const [activeTasks, setActiveTasks] = useState(() => {
    try {
      const savedTasks = window.localStorage.getItem(ACTIVE_TASKS_STORAGE_KEY)
      const parsedTasks = savedTasks ? JSON.parse(savedTasks) : {}
      return Object.fromEntries(
        Object.entries(parsedTasks).filter(([, task]) => !isTerminalTask(task))
      )
    } catch {
      return {}
    }
  })
  const [taskPollingIntervals, setTaskPollingIntervals] = useState({})

  useEffect(() => {
    try {
      window.localStorage.setItem(ACTIVE_TASKS_STORAGE_KEY, JSON.stringify(
        Object.fromEntries(
          Object.entries(activeTasks).filter(([, task]) => !isTerminalTask(task))
        )
      ))
    } catch {
      // Ignore storage failures in private browsing / blocked storage modes.
    }
  }, [activeTasks])

  useEffect(() => {
    const controller = new AbortController()

    async function fetchPlaylists() {
      try {
        setIsLoadingPlaylists(true)
        setPlaylistsError('')

        const response = await fetch(`${API_BASE_URL}/api/playlists`, { signal: controller.signal })
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        setPlaylists(Array.isArray(data.playlists) ? data.playlists : [])
      } catch (requestError) {
        if (requestError.name !== 'AbortError') {
          console.error('Error fetching playlists:', requestError)
          setPlaylistsError('Failed to load playlists from the API.')
        }
      } finally {
        setIsLoadingPlaylists(false)
      }
    }

    fetchPlaylists()

    const handlePopState = () => setCurrentPath(getCurrentPath())
    window.addEventListener('popstate', handlePopState)

    return () => {
      controller.abort()
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = (path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path)
    }
    setCurrentPath(getCurrentPath())
  }

  const handleOpenPlaylist = (playlistId) => {
    navigate(`/playlist/${playlistId}`)
  }

  const handleBack = () => {
    navigate('/')
  }

  const handleRegisterPlaylist = async (playlistUrl) => {
    setRegistrationStatus('Starting playlist registration. Check back soon.')

    const response = await fetch(`${API_BASE_URL}/api/playlists/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ playlist_url: playlistUrl }),
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`)
    }

    setRegistrationStatus(data.message || 'Playlist registration started. Check back soon.')
  }

  const startTaskPolling = (taskId, playlistId = null) => {
    if (taskPollingIntervals[taskId]) {
      return
    }

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/processing/${taskId}`)
        if (!response.ok) {
          if (response.status === 404) {
            clearInterval(interval)
            setTaskPollingIntervals(prev => {
              const newIntervals = { ...prev }
              delete newIntervals[taskId]
              return newIntervals
            })
          }
          return
        }

        const status = await response.json()
        setActiveTasks(prev => {
          const existingTask = prev[taskId] || {}
          return {
            ...prev,
            [taskId]: {
              ...existingTask,
              ...status,
              playlistId,
              taskId,
              created_at: status.created_at || existingTask.created_at || new Date().toISOString(),
            }
          }
        })

        if (status.status === 'completed' || status.status === 'error') {
          clearInterval(interval)
          setTaskPollingIntervals(prev => {
            const newIntervals = { ...prev }
            delete newIntervals[taskId]
            return newIntervals
          })

          if (status.status === 'completed' && playlistId) {
            setTimeout(() => {
              setActiveTasks(prev => {
                const newTasks = { ...prev }
                delete newTasks[taskId]
                return newTasks
              })
            }, 3000)
          }
        }
      } catch (error) {
        console.error('Error polling task status:', error)
      }
    }, 1000)

    setTaskPollingIntervals(prev => ({
      ...prev,
      [taskId]: interval
    }))
  }

  useEffect(() => {
    Object.values(activeTasks).forEach(task => {
      if (!task?.taskId) {
        return
      }
      if (!taskPollingIntervals[task.taskId] && task.status !== 'completed' && task.status !== 'error') {
        startTaskPolling(task.taskId, task.playlistId ?? null)
      }
    })
  }, [])

  const getTaskByPlaylistId = (playlistId) => {
    return Object.values(activeTasks).find(task => task.playlistId === playlistId)
  }

  const playlistId = getPlaylistIdFromPath(currentPath)

  return playlistId ? (
    <main className="yt-page">
      <PlaylistPage
        playlistId={playlistId}
        onBack={handleBack}
        activeTask={getTaskByPlaylistId(playlistId)}
        onStartTask={(taskId) => startTaskPolling(taskId, playlistId)}
      />
      <ProcessingOverlay activeTasks={Object.values(activeTasks)} />
    </main>
  ) : (
    <main className="yt-page">
      <HomePage
        playlists={playlists}
        isLoading={isLoadingPlaylists}
        error={playlistsError}
        onOpenPlaylist={handleOpenPlaylist}
        onRegisterPlaylist={handleRegisterPlaylist}
        registrationStatus={registrationStatus}
      />
      <ProcessingOverlay activeTasks={Object.values(activeTasks)} />
    </main>
  )
}

function ProcessingOverlay({ activeTasks }) {
  if (activeTasks.length === 0) {
    return null
  }

  const getProgressStats = (task) => {
    const processedVideos = Number(task.processed_videos ?? task.processedVideos ?? 0)
    const totalVideos = Number(task.total_videos ?? task.totalVideos ?? 0)
    const remainingVideos = totalVideos > 0 ? Math.max(totalVideos - processedVideos, 0) : 0
    const startedAt = new Date(task.created_at || Date.now()).getTime()
    const elapsedSeconds = Math.max(0, (Date.now() - startedAt) / 1000)

    let etaSeconds = null
    if (processedVideos > 0 && totalVideos > processedVideos) {
      const secondsPerVideo = elapsedSeconds / processedVideos
      etaSeconds = Math.max(0, Math.round(secondsPerVideo * remainingVideos))
    }

    return {
      processedVideos,
      totalVideos,
      remainingVideos,
      elapsedSeconds,
      etaSeconds,
    }
  }

  const formatETA = (task) => {
    const { etaSeconds } = getProgressStats(task)
    if (etaSeconds == null || task.progress == null || task.progress >= 100 || task.progress <= 0) {
      return ''
    }
    return `~${formatTimeSpan(etaSeconds)}`
  }

  return (
    <div className="yt-processingOverlay">
      <div className="yt-processingOverlay__header">
        <span>Processing ({activeTasks.length})</span>
      </div>
      <div className="yt-processingOverlay__list">
        {activeTasks.map(task => (
          <div key={task.taskId} className="yt-processingOverlay__item">
            <p className="yt-processingOverlay__message">{task.message}</p>
            {task.current_video_title && (
              <p className="yt-processingOverlay__submessage">{task.current_video_title}</p>
            )}
            <div className="yt-processingOverlay__progressWrap">
              <div
                className="yt-processingOverlay__progressBar"
                style={{ width: `${task.progress || 0}%` }}
              />
            </div>
            {(() => {
              const stats = getProgressStats(task)
              return (
                <div className="yt-processingOverlay__stats">
                  <span>
                    {stats.totalVideos > 0
                      ? `${stats.processedVideos}/${stats.totalVideos} videos`
                      : `${Math.round(task.progress || 0)}% complete`}
                  </span>
                  <span>
                    {stats.totalVideos > 0
                      ? `${stats.remainingVideos} left`
                      : formatETA(task)}
                  </span>
                  <span>{formatTimeSpan(stats.elapsedSeconds)} elapsed</span>
                </div>
              )
            })()}
            <div className="yt-processingOverlay__footer">
              <span>{Math.round(task.progress || 0)}%</span>
              <span>{formatETA(task)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App
