import { useState } from 'react'

const TYPE_COLORS = {
  hook: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  story: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  insight: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  funny: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
  emotional: 'bg-red-500/20 text-red-300 border-red-500/30',
}

const FORMAT_OPTIONS = [
  { value: 'portrait', label: 'Portrait 9:16' },
  { value: 'landscape_blur', label: 'Paysage flou' },
  { value: 'square', label: 'Carré 1:1' },
  { value: 'original', label: 'Original' },
]

const SUBTITLE_OPTIONS = [
  { value: 'tiktok', label: 'TikTok' },
  { value: 'minimal', label: 'Minimal' },
  { value: 'none', label: 'Sans' },
]

function formatTime(s) {
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function ScoreBadge({ score }) {
  const color = score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-gray-400'
  return (
    <span className={`font-mono text-sm font-bold ${color}`}>{score}</span>
  )
}

function ClipCard({ clip, jobId }) {
  const [renderState, setRenderState] = useState('idle') // idle | loading | rendering | done | error
  const [downloadUrl, setDownloadUrl] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const [progress, setProgress] = useState(0)
  const [format, setFormat] = useState('portrait')
  const [subtitleStyle, setSubtitleStyle] = useState('tiktok')

  const typeClass = TYPE_COLORS[clip.type] || 'bg-gray-500/20 text-gray-300 border-gray-500/30'
  const duration = Math.round(clip.end - clip.start)

  async function handleRender() {
    setRenderState('loading')
    setErrorMsg(null)
    setProgress(0)

    try {
      const res = await fetch('/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          clips: [{
            id: clip.id,
            start: clip.start,
            end: clip.end,
            format,
            subtitle_style: subtitleStyle,
          }],
        }),
      })
      if (!res.ok) throw new Error(`Erreur ${res.status}`)
      const { render_id } = await res.json()

      setRenderState('rendering')
      await pollRender(render_id, clip.id)
    } catch (err) {
      setRenderState('error')
      setErrorMsg(err.message)
    }
  }

  async function pollRender(renderId, clipId) {
    const MAX = 600
    let elapsed = 0

    while (elapsed < MAX) {
      await sleep(3000)
      elapsed += 3

      const res = await fetch(`/render/status/${renderId}`)
      if (!res.ok) continue
      const data = await res.json()

      if (data.progress != null) setProgress(data.progress)

      if (data.step === 'done') {
        setDownloadUrl(`/download/${renderId}/${clipId}`)
        setRenderState('done')
        return
      }
      if (data.step === 'error') {
        throw new Error(data.message || 'Render failed')
      }
    }
    throw new Error('Timeout — le rendu a pris trop longtemps')
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3 hover:border-white/20 transition">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-100 truncate">{clip.title}</p>
          <p className="text-gray-500 text-xs mt-0.5 line-clamp-2">{clip.reason}</p>
        </div>
        <ScoreBadge score={clip.score} />
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${typeClass}`}>
          {clip.type}
        </span>
        <span className="text-xs text-gray-500 font-mono">
          {formatTime(clip.start)} → {formatTime(clip.end)}
        </span>
        <span className="text-xs text-gray-600">
          {duration}s
        </span>
      </div>

      {/* Action */}
      <div className="pt-1">
        {renderState === 'idle' && (
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-purple-500"
                >
                  {FORMAT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">Sous-titres</label>
                <select
                  value={subtitleStyle}
                  onChange={(e) => setSubtitleStyle(e.target.value)}
                  className="w-full bg-white/5 border border-white/15 rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-purple-500"
                >
                  {SUBTITLE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={handleRender}
              className="text-sm bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg transition"
            >
              Exporter
            </button>
          </div>
        )}
        {renderState === 'loading' && (
          <span className="text-sm text-gray-400">Lancement du rendu...</span>
        )}
        {renderState === 'rendering' && (
          <div className="space-y-1">
            <span className="text-sm text-purple-400 animate-pulse">Rendu en cours... {progress > 0 ? `${progress}%` : ''}</span>
            <div className="w-full bg-white/10 rounded-full h-1.5">
              <div
                className="bg-purple-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
        {renderState === 'done' && (
          <div className="flex items-center gap-3">
            <a
              href={downloadUrl}
              download={`${clip.id}.mp4`}
              className="inline-block text-sm bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg transition"
            >
              Télécharger MP4
            </a>
            <button
              onClick={() => { setRenderState('idle'); setDownloadUrl(null) }}
              className="text-xs text-gray-500 hover:text-gray-300 transition"
            >
              Re-exporter
            </button>
          </div>
        )}
        {renderState === 'error' && (
          <div>
            <p className="text-red-400 text-xs mb-1">{errorMsg}</p>
            <button
              onClick={() => setRenderState('idle')}
              className="text-xs text-gray-500 underline"
            >
              Réessayer
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

export default function ClipList({ jobId, clips }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {clips.length} clips détectés
        </h2>
        <span className="text-xs text-gray-500">trié par score viral</span>
      </div>

      <div className="space-y-3">
        {clips.map((clip) => (
          <ClipCard key={clip.id} clip={clip} jobId={jobId} />
        ))}
      </div>
    </div>
  )
}
