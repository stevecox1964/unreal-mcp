import { useState } from 'react'

interface Props {
  agents: string[]
  selected: string | null
  onSelect: (id: string) => void
  onCreate: (name: string) => Promise<void>
}

export default function AgentList({ agents, selected, onSelect, onCreate }: Props) {
  const [showModal, setShowModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    setError(null)
    try {
      await onCreate(name)
      setNewName('')
      setShowModal(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create agent. Is the backend running?')
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <div className="sidebar">
        <div className="sidebar-header">Agents</div>
        <div className="agent-list">
          {agents.length === 0 && (
            <div style={{ padding: '14px 16px', fontSize: 12, color: '#4a4a6a' }}>
              No agents yet
            </div>
          )}
          {agents.map((id) => (
            <div
              key={id}
              className={`agent-item${selected === id ? ' selected' : ''}`}
              onClick={() => onSelect(id)}
            >
              {id}
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <button className="btn btn-primary btn-full" onClick={() => setShowModal(true)}>
            + New Agent
          </button>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">New Agent</div>
            <input
              className="field-input"
              placeholder="agent_id (e.g. gondolf)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              autoFocus
            />
            {error && (
              <div style={{ fontSize: 12, color: '#e94560' }}>{error}</div>
            )}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => { setShowModal(false); setError(null) }}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleCreate} disabled={creating || !newName.trim()}>
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
