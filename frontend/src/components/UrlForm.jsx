import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import API_URL from '../api'

export default function UrlForm({ onJobCreated }) {
  const [url, setUrl] = useState('')
  const [prompt, setPrompt] = useState('')
  const [minDuration, setMinDuration] = useState(15)
  const [maxDuration, setMaxDuration] = useState(90)
  const [mode, setMode] = useState('viral')
  const [showOptions, setShowOptions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const isSequential = mode === 'sequential'

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setError(null)
    setLoading(true)

    try {
      const body = { url: url.trim(), mode }
      if (!isSequential && prompt.trim()) body.prompt = prompt.trim()
      if (!isSequential && minDuration !== 15) body.min_duration = minDuration
      if (maxDuration !== 90) body.max_duration = maxDuration

      const res = await fetch(`${API_URL}/analyze`, {
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

        {/* Mode toggle */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('viral')}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              !isSequential
                ? 'bg-purple-600/20 border-purple-500/40 text-purple-300'
                : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
            }`}
          >
            Clips viraux
          </button>
          <button
            type="button"
            onClick={() => setMode('sequential')}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              isSequential
                ? 'bg-purple-600/20 border-purple-500/40 text-purple-300'
                : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
            }`}
          >
            Découpage séquentiel
          </button>
        </div>

        {isSequential && (
          <p className="text-xs text-gray-500">
            Découpe toute la vidéo en clips successifs de durée fixe, sans analyse IA.
          </p>
        )}

        {/* Toggle options */}
        <button
          type="button"
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition"
        >
          {showOptions ? (
            <><ChevronDown size={13} /> Masquer les options</>
          ) : (
            <><ChevronRight size={13} /> Options avancées</>
          )}
        </button>

        {showOptions && (
          <div className="space-y-4 bg-white/3 border border-white/5 rounded-xl p-4">
            {/* Prompt — only for viral mode */}
            {!isSequential && (
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
            )}

            {/* Duration range */}
            <div className="flex gap-6">
              {!isSequential && (
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
              )}
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">
                  {isSequential ? `Durée par clip (${maxDuration}s)` : `Durée max (${maxDuration}s)`}
                </label>
                <input
                  type="range"
                  min={isSequential ? 10 : minDuration + 5}
                  max={300}
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
