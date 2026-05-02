import { useEffect, useState } from 'react'
import * as api from '../../api'
import type { MemoryEntry } from '../../api'

export default function MemoryTab({ agentId }: { agentId: string }) {
  const [memories, setMemories] = useState<MemoryEntry[]>([])
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    setStatus(null)
    api.getMemory(agentId)
      .then((m) => setMemories(m.memories ?? []))
      .catch(() => setStatus({ ok: false, msg: 'Failed to load' }))
  }, [agentId])

  const add = () =>
    setMemories((prev) => [...prev, { timestamp: new Date().toISOString(), importance: 0.5, text: '' }])

  const remove = (i: number) => setMemories((prev) => prev.filter((_, idx) => idx !== i))

  const update = <K extends keyof MemoryEntry>(i: number, key: K, value: MemoryEntry[K]) =>
    setMemories((prev) => prev.map((entry, idx) => (idx === i ? { ...entry, [key]: value } : entry)))

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      const stamped = memories.map((m) => ({ ...m, timestamp: m.timestamp || new Date().toISOString() }))
      await api.putMemory(agentId, { agent_id: agentId, memories: stamped })
      setMemories(stamped)
      setStatus({ ok: true, msg: 'Saved' })
    } catch {
      setStatus({ ok: false, msg: 'Save failed — is the backend running?' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="tab-body">
      <div className="memory-list">
        {memories.length === 0 && <div style={{ fontSize: 13, color: '#4a4a6a' }}>No memories yet.</div>}
        {memories.map((entry, i) => (
          <div key={i} className="memory-entry">
            <div className="memory-entry-header">
              <span className="memory-timestamp">{entry.timestamp || '—'}</span>
              <button className="btn btn-sm btn-danger" onClick={() => remove(i)}>Remove</button>
            </div>
            <textarea className="memory-text-input" value={entry.text} placeholder="Memory text…"
              onChange={(e) => update(i, 'text', e.target.value)} />
            <div className="importance-row">
              <span>Importance</span>
              <input type="range" min={0} max={1} step={0.05} value={entry.importance}
                onChange={(e) => update(i, 'importance', Number(e.target.value))} />
              <span style={{ minWidth: 30, textAlign: 'right' }}>{entry.importance.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button className="btn btn-secondary btn-sm" onClick={add}>+ Add memory</button>
        <div className="save-row" style={{ margin: 0 }}>
          {status && <span style={{ fontSize: 12, color: status.ok ? '#4caf7d' : '#e94560' }}>{status.msg}</span>}
          <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
        </div>
      </div>
    </div>
  )
}
