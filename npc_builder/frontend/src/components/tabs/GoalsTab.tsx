import { useEffect, useState } from 'react'
import * as api from '../../api'

export default function GoalsTab({ agentId }: { agentId: string }) {
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    setStatus(null)
    api.getGoals(agentId).then(setContent).catch(() => setStatus({ ok: false, msg: 'Failed to load' }))
  }, [agentId])

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      await api.putGoals(agentId, content)
      setStatus({ ok: true, msg: 'Saved' })
    } catch {
      setStatus({ ok: false, msg: 'Save failed — is the backend running?' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="tab-body">
      <textarea className="code-area" value={content} onChange={(e) => setContent(e.target.value)} spellCheck={false} />
      <div className="save-row">
        {status && <span style={{ fontSize: 12, color: status.ok ? '#4caf7d' : '#e94560' }}>{status.msg}</span>}
        <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </div>
    </div>
  )
}
