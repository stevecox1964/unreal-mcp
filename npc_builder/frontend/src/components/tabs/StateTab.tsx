import { useEffect, useState } from 'react'
import * as api from '../../api'
import type { AgentState } from '../../api'

const EMPTY: AgentState = {
  agent_id: '',
  is_active: true,
  is_busy: false,
  current_goal: '',
  tick_interval_seconds: 10,
  speech_cooldown_seconds: 30,
  last_tick_time: null,
  last_spoke_time: null,
}

export default function StateTab({ agentId }: { agentId: string }) {
  const [state, setState] = useState<AgentState>({ ...EMPTY, agent_id: agentId })
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    setStatus(null)
    api.getState(agentId)
      .then((s) => setState(s ?? { ...EMPTY, agent_id: agentId }))
      .catch(() => setStatus({ ok: false, msg: 'Failed to load' }))
  }, [agentId])

  const set = <K extends keyof AgentState>(key: K, value: AgentState[K]) =>
    setState((prev) => ({ ...prev, [key]: value }))

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      await api.putState(agentId, state)
      setStatus({ ok: true, msg: 'Saved' })
    } catch {
      setStatus({ ok: false, msg: 'Save failed — is the backend running?' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="tab-body">
      <div className="field-grid">
        <div className="field-row">
          <span className="field-label">Active</span>
          <div className="toggle-row">
            <button className={`toggle${state.is_active ? ' on' : ''}`} onClick={() => set('is_active', !state.is_active)} />
            <span>{state.is_active ? 'Active' : 'Inactive'}</span>
          </div>
        </div>
        <div className="field-row">
          <span className="field-label">Busy</span>
          <div className="toggle-row">
            <button className={`toggle${state.is_busy ? ' on' : ''}`} onClick={() => set('is_busy', !state.is_busy)} />
            <span>{state.is_busy ? 'Busy' : 'Free'}</span>
          </div>
        </div>
        <div className="field-row">
          <span className="field-label">Tick interval (seconds)</span>
          <input type="number" className="field-input" value={state.tick_interval_seconds} min={1}
            onChange={(e) => set('tick_interval_seconds', Number(e.target.value))} />
        </div>
        <div className="field-row">
          <span className="field-label">Speech cooldown (seconds)</span>
          <input type="number" className="field-input" value={state.speech_cooldown_seconds} min={0}
            onChange={(e) => set('speech_cooldown_seconds', Number(e.target.value))} />
        </div>
        <div className="field-row field-input-full">
          <span className="field-label">Current goal</span>
          <input type="text" className="field-input" value={state.current_goal} placeholder="e.g. patrol_village"
            onChange={(e) => set('current_goal', e.target.value)} />
        </div>
      </div>
      {(state.last_tick_time || state.last_spoke_time) && (
        <div style={{ fontSize: 12, color: '#5a5a7a', display: 'flex', gap: 24 }}>
          {state.last_tick_time && <span>Last tick: {state.last_tick_time}</span>}
          {state.last_spoke_time && <span>Last spoke: {state.last_spoke_time}</span>}
        </div>
      )}
      <div className="save-row">
        {status && <span style={{ fontSize: 12, color: status.ok ? '#4caf7d' : '#e94560' }}>{status.msg}</span>}
        <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </div>
    </div>
  )
}
