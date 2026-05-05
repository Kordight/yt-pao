import { useEffect, useState } from 'react'
import './App.css'
import HomePage from './pages/HomePage'
import PlaylistPage from './pages/PlaylistPage'
import { API_BASE_URL } from './utils/formatters'

function getCurrentPath() {
  return window.location.pathname
}

function getPlaylistIdFromPath(pathname) {
  const match = pathname.match(/^\/playlist\/(\d+)$/)
  return match ? Number(match[1]) : null
}

function App() {
  const [playlists, setPlaylists] = useState([])
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(true)
  const [playlistsError, setPlaylistsError] = useState('')
  const [registrationStatus, setRegistrationStatus] = useState('')
  const [currentPath, setCurrentPath] = useState(getCurrentPath())

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

  const playlistId = getPlaylistIdFromPath(currentPath)

  return playlistId ? (
    <main className="yt-page">
      <PlaylistPage playlistId={playlistId} onBack={handleBack} />
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
    </main>
  )
}

export default App
