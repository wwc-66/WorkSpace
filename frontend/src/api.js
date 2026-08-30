const API_BASE = '/api'

async function request(path, { method = 'POST', body } = {}) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`${API_BASE}${path}`, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

function applyConfig(body, apiKey, model, provider, baseUrl) {
  if (apiKey) body.api_key = apiKey
  if (model) body.model = model
  if (provider) body.provider = provider
  if (baseUrl) body.base_url = baseUrl
}

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('Backend unreachable')
  return res.json()
}

export async function generate(prompt, sessionId = null, apiKey = null, model = null, provider = null, baseUrl = null) {
  const body = { prompt }
  // 新对话不传 session_id，由后端生成新的会话
  if (sessionId) body.session_id = sessionId
  applyConfig(body, apiKey, model, provider, baseUrl)
  return request('/generate', { body })
}

export async function ask(question, sessionId = null, apiKey = null, model = null, provider = null, baseUrl = null) {
  const body = { question }
  if (sessionId) body.session_id = sessionId
  applyConfig(body, apiKey, model, provider, baseUrl)
  return request('/ask', { body })
}

// ===== 会话管理 =====

export async function fetchSessions() {
  return request('/sessions', { method: 'GET' })
}

export async function fetchSessionMessages(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'GET' })
}

export async function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function clearAllSessions() {
  return request('/sessions', { method: 'DELETE' })
}

export async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}
