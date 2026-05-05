import { useState, useEffect } from 'react'
import './App.css'

function App() {
  // 1. Zmienna do przechowywania naszych playlist
  const [playlists, setPlaylists] = useState([])

  // 2. Funkcja, która uruchamia się raz przy załadowaniu strony
  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/playlists');
        const data = await response.json();
        const downloadedPlaylists = data.playlists;
        setPlaylists(downloadedPlaylists);
      } catch (error) {
        console.error("Błąd pobierania danych:", error)
      }
    }
    fetchData()
  }, [])

  // 3. To, co wyświetla się na ekranie
  return (
    <div>
      {playlists.map(playlist => (
        <div key={playlist.playlist_id}>
          <p><strong>Nazwa playlisty:</strong> {playlist.latest_title || playlist.playlist_name}</p>
          <p><strong>Link do playlisty:</strong> <a href={playlist.playlist_url} target="_blank" rel="noopener noreferrer">{playlist.playlist_url}</a></p>
          <p><strong>Opis playlisty:</strong> {playlist.latest_description}</p>
          <p><strong>Autor playlisty:</strong> {playlist.playlist_author}</p>
          {playlist.latest_thumbnail_url && (
             <img src={`http://127.0.0.1:8000${playlist.latest_thumbnail_url}`} alt="Thumbnail" style={{ width: '200px', height: 'auto' }} />
          )}
        </div>
      ))}
    </div>
  )
}

export default App