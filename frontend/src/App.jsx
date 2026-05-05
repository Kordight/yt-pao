import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = 'http://127.0.0.1:8000'
const DEFAULT_THUMBNAIL = '/playlist-placeholder.svg'

function App() {
  const [playlists, setPlaylists] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function fetchData() {
      try {
        setIsLoading(true)
        setError('')

        const response = await fetch(`${API_BASE_URL}/api/playlists`, { signal: controller.signal })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        setPlaylists(Array.isArray(data.playlists) ? data.playlists : [])
      } catch (requestError) {
        if (requestError.name !== 'AbortError') {
          console.error('Błąd pobierania danych:', requestError)
          setError('Nie udało się pobrać playlist z API.')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()

    return () => controller.abort()
  }, [])

  const playlistCards = useMemo(() => playlists, [playlists])

  return (
    <main className="yt-page">
      <header className="yt-page__header">
        <div>
          <p className="yt-page__eyebrow">YT-PAO</p>
          <h1 className="yt-page__title">Playlists</h1>
        </div>
      </header>

      {isLoading && <p className="yt-state">Ładowanie playlist...</p>}
      {!isLoading && error && <p className="yt-state yt-state--error">{error}</p>}

      {!isLoading && !error && (
        <section className="yt-grid" aria-label="Lista playlist">
          {playlistCards.length === 0 ? (
            <p className="yt-state">No playlists available.</p>
          ) : (
            playlistCards.map((playlist) => {
              const thumbnailSrc = playlist.latest_thumbnail_url
                ? `${API_BASE_URL}${playlist.latest_thumbnail_url}`
                : DEFAULT_THUMBNAIL
              const title = playlist.latest_title || playlist.playlist_name || 'Bez tytułu'
              const author = playlist.playlist_author || 'Nieznany autor'
              const authorUrl = playlist.playlist_author_url || playlist.playlist_url || '#'
              const videoCount = playlist.video_count ?? 0

              return (
                <article className="yt-card" key={playlist.playlist_id}>
                  <a
                    className="yt-card__thumbLink"
                    href={playlist.playlist_url || authorUrl}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Otwórz playlistę ${title}`}
                  >
                    <div className="yt-card__thumbWrap">
                      <img className="yt-card__thumb" src={thumbnailSrc} alt={title} />
                      <span className="yt-card__badge">{videoCount} videos</span>
                    </div>
                  </a>

                  <div className="yt-card__body">
                    <div className="yt-card__content">
                      <h2 className="yt-card__title">{title}</h2>
                      <p className="yt-card__meta">
                        <a href={authorUrl} target="_blank" rel="noreferrer">
                          {author}
                        </a>
                      </p>
                      {playlist.latest_description && (
                        <p className="yt-card__description">{playlist.latest_description}</p>
                      )}
                    </div>

                    <button className="yt-card__menu" type="button" aria-label="Options">
                      ⋮
                    </button>
                  </div>
                </article>
              )
            })
          )}
        </section>
      )}
    </main>
  )
}

export default App