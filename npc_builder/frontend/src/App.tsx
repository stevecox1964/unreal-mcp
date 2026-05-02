import { useEffect, useState } from 'react'
import * as api from './api'
import AgentEditor from './components/AgentEditor'
import AgentList from './components/AgentList'

export default function App() {
  const [agents, setAgents] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)

  const refresh = () => api.listAgents().then(setAgents)

  useEffect(() => { refresh() }, [])

  const handleCreate = async (name: string) => {
    await api.createAgent(name)
    await refresh()
    setSelected(name)
  }

  const handleDelete = async (id: string) => {
    await api.deleteAgent(id)
    if (selected === id) setSelected(null)
    await refresh()
  }

  return (
    <div className="app">
      <AgentList
        agents={agents}
        selected={selected}
        onSelect={setSelected}
        onCreate={handleCreate}
      />
      <div className="main">
        {selected ? (
          <AgentEditor agentId={selected} onDelete={() => handleDelete(selected)} />
        ) : (
          <div className="empty-state">Select an agent or create a new one</div>
        )}
      </div>
    </div>
  )
}
