import { useEffect, useState } from 'react'
import * as api from '../../api'

const ALL_ACTIONS = [
  'idle', 'walk_to', 'speak_to', 'inspect_object',
  'follow_character', 'attack', 'flee', 'ask_for_screenshot', 'remember',
]

export default function ToolsTab({ agentId }: { agentId: string }) {
  const [allowed, setAllowed] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    setStatus(null)
    api.getTools(agentId).then((actions) => setAllowed(new Set(actions))).catch(() => setStatus({ ok: false, msg: 'Failed to load' }))
  }, [agentId])

  const toggle = (action: string) =>
    setAllowed((prev) => { const next = new Set(prev); next.has(action) ? next.delete(action) : next.add(action); return next })

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      await api.putTools(agentId, [...allowed])
      setStatus({ ok: true, msg: 'Saved' })
    } catch {
      setStatus({ ok: false, msg: 'Save failed — is the backend running?' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="tab-body">
      <div style={{ fontSize: 12, color: '#7a7a9a', marginBottom: 4 }}>Select the actions this agent is allowed to perform.</div>
      <div className="checkbox-grid">
        {ALL_ACTIONS.map((action) => {
          const on = allowed.has(action)
          return (
            <div key={action} className={`checkbox-item${on ? ' checked' : ''}`} onClick={() => toggle(action)}>
              <span className="checkbox-dot" />{action}
            </div>
          )
        })}
      </div>
      <div className="save-row">
        {status && <span style={{ fontSize: 12, color: status.ok ? '#4caf7d' : '#e94560' }}>{status.msg}</span>}
        <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </div>
    </div>
  )
}
