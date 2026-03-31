import { useState } from 'react'

export default function UrlForm({ onJobCreated }) {
  const [url, setUrl] = useState('')
  const [prompt, setPrompt] = useState('')
  const [minDuration, setMinDuration] = useState(15)
  const [maxDuration, setMaxDuration] = useState(90)
  const [showOptions, setShowOptions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setError(null)
    setLoading(true)

    try {
      const body = { url: url.trim() }
      if (prompt.trim()) body.prompt = prompt.trim()
      if (minDuration !== 15) body.min_duration = minDuration
      if (maxDuration !== 90) body.max_duration = maxDuration

      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
        Colle une URL YouTube — ClipAI détecte les meilleurs moments et les exporte.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex gap-3">
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
        </div>

        {/* Toggle options */}
        <button
          type="button"
          onClick={() => setShowOptions(!showOptions)}
          className="text-xs text-gray-500 hover:text-gray-300 transition"
        >
          {showOptions ? '▾ Masquer les options' : '▸ Options avancées'}
        </button>

        {showOptions && (
          <div className="space-y-4 bg-white/3 border border-white/5 rounded-xl p-4">
            {/* Prompt */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Instructions pour l'analyse (optionnel)
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ex: Je veux des moments drôles uniquement, axés sur les anecdotes personnelles..."
                rows={3}
                className="w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm placeholder-gray-600 focus:outline-none focus:border-purple-500 transition resize-none"
                disabled={loading}
              />
            </div>

            {/* Duration range */}
            <div className="flex gap-6">
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  Durée min ({minDuration}s)
                </label>
                <input
                  type="range"
                  min={5}
                  max={maxDuration - 5}
                  value={minDuration}
                  onChange={(e) => setMinDuration(Number(e.target.value))}
                  className="w-full accent-purple-500"
                  disabled={loading}
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  Durée max ({maxDuration}s)
                </label>
                <input
                  type="range"
                  min={minDuration + 5}
                  max={180}
                  value={maxDuration}
                  onChange={(e) => setMaxDuration(Number(e.target.value))}
                  className="w-full accent-purple-500"
                  disabled={loading}
                />
              </div>
            </div>
          </div>
        )}
      </form>

      {error && (
        <p className="mt-3 text-red-400 text-sm">{error}</p>
      )}
    </div>
  )
}
