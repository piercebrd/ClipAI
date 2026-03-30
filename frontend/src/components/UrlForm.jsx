import { useState } from 'react'

export default function UrlForm({ onJobCreated }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setError(null)
    setLoading(true)

    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      onJobCreated(data.job_id)
      setUrl('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
      <h1 className="text-2xl font-bold mb-1">Extraire des clips viraux</h1>
      <p className="text-gray-400 text-sm mb-5">
        Colle une URL YouTube — ClipAI détecte les meilleurs moments et les exporte en 9:16.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="flex-1 bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-sm placeholder-gray-600 focus:outline-none focus:border-purple-500 transition"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium px-6 py-3 rounded-xl text-sm transition"
        >
          {loading ? 'Envoi...' : 'Analyser'}
        </button>
      </form>

      {error && (
        <p className="mt-3 text-red-400 text-sm">{error}</p>
      )}
    </div>
  )
}
