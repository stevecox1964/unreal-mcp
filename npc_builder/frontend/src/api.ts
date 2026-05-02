const BASE = 'http://localhost:8001'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

async function put(path: string, body: unknown): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
}

async function post(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
}

// ── Agent list ────────────────────────────────────────────────────────────

export async function listAgents(): Promise<string[]> {
  const data = await get<{ agents: string[] }>('/agents')
  return data.agents
}

export async function createAgent(agentId: string): Promise<void> {
  await post(`/agents/${encodeURIComponent(agentId)}`)
}

export async function deleteAgent(agentId: string): Promise<void> {
  await del(`/agents/${encodeURIComponent(agentId)}`)
}

// ── Text files ────────────────────────────────────────────────────────────

async function getText(agentId: string, file: string): Promise<string> {
  const data = await get<{ content: string }>(`/agents/${encodeURIComponent(agentId)}/${file}`)
  return data.content
}

async function putText(agentId: string, file: string, content: string): Promise<void> {
  await put(`/agents/${encodeURIComponent(agentId)}/${file}`, { content })
}

export const getCharacter = (id: string) => getText(id, 'character')
export const putCharacter = (id: string, content: string) => putText(id, 'character', content)

export const getGoals = (id: string) => getText(id, 'goals')
export const putGoals = (id: string, content: string) => putText(id, 'goals', content)

export const getRules = (id: string) => getText(id, 'rules')
export const putRules = (id: string, content: string) => putText(id, 'rules', content)

// ── Tools ─────────────────────────────────────────────────────────────────

export async function getTools(agentId: string): Promise<string[]> {
  const data = await get<{ allowed_actions: string[] }>(`/agents/${encodeURIComponent(agentId)}/tools`)
  return data.allowed_actions ?? []
}

export async function putTools(agentId: string, allowed_actions: string[]): Promise<void> {
  await put(`/agents/${encodeURIComponent(agentId)}/tools`, { allowed_actions })
}

// ── State ─────────────────────────────────────────────────────────────────

export interface AgentState {
  agent_id: string
  is_active: boolean
  is_busy: boolean
  current_goal: string
  tick_interval_seconds: number
  speech_cooldown_seconds: number
  last_tick_time: string | null
  last_spoke_time: string | null
}

export async function getState(agentId: string): Promise<AgentState> {
  return get<AgentState>(`/agents/${encodeURIComponent(agentId)}/state`)
}

export async function putState(agentId: string, state: AgentState): Promise<void> {
  await put(`/agents/${encodeURIComponent(agentId)}/state`, state)
}

// ── Memory ────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  timestamp: string
  importance: number
  text: string
}

export interface AgentMemory {
  agent_id: string
  memories: MemoryEntry[]
}

export async function getMemory(agentId: string): Promise<AgentMemory> {
  return get<AgentMemory>(`/agents/${encodeURIComponent(agentId)}/memory`)
}

export async function putMemory(agentId: string, memory: AgentMemory): Promise<void> {
  await put(`/agents/${encodeURIComponent(agentId)}/memory`, memory)
}
