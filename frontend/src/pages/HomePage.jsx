import { useState } from 'react'
import { formatCompactNumber, resolveThumbnailSrc } from '../utils/formatters'

function HomePage({ playlists, isLoading, error, onOpenPlaylist, onRegisterPlaylist, registrationStatus }) {
  const [playlistUrl, setPlaylistUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmedUrl = playlistUrl.trim()
    if (!trimmedUrl) {
      return
    }

    try {
      setIsSubmitting(true)
      await onRegisterPlaylist(trimmedUrl)
      setPlaylistUrl('')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <header className="yt-page__header">
        <div>
          <p className="yt-page__eyebrow">YT-PAO</p>
          <h1 className="yt-page__title">Playlists</h1>
        </div>
      </header>

      <section className="yt-register">
        <div className="yt-register__copy">
          <h2 className="yt-register__title">Register a playlist</h2>
          <p className="yt-register__text">
            Paste a YouTube playlist link and the app will start processing it in the background.
            This can take a while, so check back later for the result.
          </p>
        </div>

        <form className="yt-register__form" onSubmit={handleSubmit}>
          <input
            className="yt-register__input"
            type="url"
            value={playlistUrl}
            onChange={(event) => setPlaylistUrl(event.target.value)}
            placeholder="https://www.youtube.com/playlist?list=..."
            aria-label="Playlist URL"
            required
          />
          <button className="yt-register__button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Registering...' : 'Register playlist'}
          </button>
        </form>

        {registrationStatus && <p className="yt-register__status">{registrationStatus}</p>}
      </section>

      {isLoading && <p className="yt-state">Loading playlists...</p>}
      {!isLoading && error && <p className="yt-state yt-state--error">{error}</p>}

      {!isLoading && !error && (
        <section className="yt-grid" aria-label="Playlists">
          {playlists.length === 0 ? (
            <p className="yt-state">No playlists to display.</p>
          ) : (
            playlists.map((playlist) => {
              const thumbnailSrc = resolveThumbnailSrc(playlist.latest_thumbnail_url)
              const title = playlist.latest_title || playlist.playlist_name || 'Untitled'
              const author = playlist.playlist_author || 'Unknown author'
              const videoCount = playlist.video_count ?? 0

              return (
                <button
                  key={playlist.playlist_id}
                  type="button"
                  className="yt-card yt-card--button"
                  onClick={() => onOpenPlaylist(playlist.playlist_id)}
                >
                  <div className="yt-card__thumbWrap">
                    <img className="yt-card__thumb" src={thumbnailSrc} alt={title} />
                    <span className="yt-card__badge">{videoCount} videos</span>
                  </div>

                  <div className="yt-card__body">
                    <div className="yt-card__content">
                      <h2 className="yt-card__title">{title}</h2>
                      <p className="yt-card__meta">
                        {author}
                        {' '}
                        • {formatCompactNumber(videoCount)} videos
                      </p>
                      {playlist.latest_description && (
                        <p className="yt-card__description">{playlist.latest_description}</p>
                      )}
                    </div>

                    <span className="yt-card__menu" aria-hidden="true">
                      ⋮
                    </span>
                  </div>
                </button>
              )
            })
          )}
        </section>
      )}
    </>
  )
}

export default HomePage