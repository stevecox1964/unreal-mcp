import { useState } from 'react'
import CharacterTab from './tabs/CharacterTab'
import GoalsTab from './tabs/GoalsTab'
import MemoryTab from './tabs/MemoryTab'
import RulesTab from './tabs/RulesTab'
import StateTab from './tabs/StateTab'
import ToolsTab from './tabs/ToolsTab'

type Tab = 'character' | 'goals' | 'rules' | 'tools' | 'state' | 'memory'

const TABS: Tab[] = ['character', 'goals', 'rules', 'tools', 'state', 'memory']

interface Props {
  agentId: string
  onDelete: () => void
}

export default function AgentEditor({ agentId, onDelete }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('character')
  const [confirming, setConfirming] = useState(false)

  const handleDelete = () => {
    if (confirming) {
      onDelete()
      setConfirming(false)
    } else {
      setConfirming(true)
      setTimeout(() => setConfirming(false), 3000)
    }
  }

  return (
    <div className="editor">
      <div className="editor-header">
        <span className="editor-title">{agentId}</span>
        <button
          className={`btn btn-sm ${confirming ? 'btn-danger' : 'btn-secondary'}`}
          onClick={handleDelete}
        >
          {confirming ? 'Confirm delete?' : 'Delete agent'}
        </button>
      </div>

      <div className="tabs">
        {TABS.map((tab) => (
          <div
            key={tab}
            className={`tab${activeTab === tab ? ' active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </div>
        ))}
      </div>

      {activeTab === 'character' && <CharacterTab agentId={agentId} />}
      {activeTab === 'goals' && <GoalsTab agentId={agentId} />}
      {activeTab === 'rules' && <RulesTab agentId={agentId} />}
      {activeTab === 'tools' && <ToolsTab agentId={agentId} />}
      {activeTab === 'state' && <StateTab agentId={agentId} />}
      {activeTab === 'memory' && <MemoryTab agentId={agentId} />}
    </div>
  )
}
