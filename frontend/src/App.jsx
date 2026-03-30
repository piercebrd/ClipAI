import { useState } from 'react'
import UrlForm from './components/UrlForm'
import JobStatus, { StatusCard } from './components/JobStatus'
import ClipList from './components/ClipList'

export default function App() {
  const [jobId, setJobId] = useState(null)
  const [job, setJob] = useState(null)

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <header className="border-b border-white/10 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <span className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            ClipAI
          </span>
          <span className="text-gray-500 text-sm">YouTube → TikTok clips</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10 space-y-8">
        <UrlForm onJobCreated={(id) => { setJobId(id); setJob(null) }} />

        {jobId && (
          <>
            <JobStatus jobId={jobId} onJobUpdate={setJob} />
            <StatusCard job={job} />
          </>
        )}

        {job?.step === 'analyzed' && job.clips?.length > 0 && (
          <ClipList jobId={jobId} clips={job.clips} />
        )}
      </main>
    </div>
  )
}
