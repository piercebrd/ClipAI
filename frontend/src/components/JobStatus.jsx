import { useEffect, useRef } from 'react'
import API_URL from '../api'

const STEP_LABELS = {
  downloading: 'Téléchargement',
  downloaded: 'Téléchargé',
  transcribing: 'Transcription',
  transcribed: 'Transcrit',
  analyzing: 'Analyse Claude',
  analyzed: 'Analysé',
  error: 'Erreur',
}

export default function JobStatus({ jobId, onJobUpdate }) {
  const intervalRef = useRef(null)

  useEffect(() => {
    let active = true

    async function poll() {
      try {
        const res = await fetch(`${API_URL}/status/${jobId}`)
        if (!res.ok) return
        const data = await res.json()
        if (active) onJobUpdate(data)

        if (data.step === 'analyzed' || data.step === 'error') {
          clearInterval(intervalRef.current)
        }
      } catch {
        // network glitch — keep polling
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2500)

    return () => {
      active = false
      clearInterval(intervalRef.current)
    }
  }, [jobId, onJobUpdate])

  return null
}

export function StatusCard({ job }) {
  if (!job) return null

  const isError = job.step === 'error'
  const isDone = job.step === 'analyzed'
  const progress = job.progress ?? 0

  return (
    <div className={`bg-white/5 border rounded-2xl p-5 space-y-3 ${isError ? 'border-red-500/40' : 'border-white/10'}`}>
      <div className="flex justify-between items-center text-sm">
        <span className="text-gray-300 font-medium">
          {STEP_LABELS[job.step] ?? job.step}
        </span>
        <span className={`text-xs font-mono ${isError ? 'text-red-400' : 'text-purple-400'}`}>
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${isError ? 'bg-red-500' : isDone ? 'bg-green-500' : 'bg-purple-500'}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="text-gray-400 text-xs">{job.message}</p>
    </div>
  )
}
