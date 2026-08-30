import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import StatusBar from './components/StatusBar'
import ModelSelector from './components/ModelSelector'
import HistoryPanel from './components/HistoryPanel'
import ChatArea from './components/ChatArea'
import ChatInput from './components/ChatInput'
import FileUpload from './components/FileUpload'
import RagToggle from './components/RagToggle'
import SettingsPanel from './components/SettingsPanel'
import useLocalStorage from './hooks/useLocalStorage'
import { generate, ask, fetchSessions, fetchSessionMessages, deleteSession, clearAllSessions } from './api'
import './App.css'

let idCounter = Date.now()
function uid() { return String(++idCounter) }

// 后端 /ask 存历史时会把检索资料拼进用户消息（"[资料参考]...\n\n[用户问题]..."），
// 前端展示时只保留原始问题
function displayContent(content) {
  if (typeof content !== 'string') return content
  const marker = '[用户问题]'
  const idx = content.lastIndexOf(marker)
  if (idx !== -1) return content.slice(idx + marker.length).trim()
  return content
}

// 加载历史消息时检查 sources 字段（RAG 参考来源列表）：
// 有效则保留，缺失/无效则去掉，保证渲染时只对有来源的消息显示来源信息
function normalizeHistoryMessage(m) {
  const msg = { ...m, content: displayContent(m.content) }
  const srcs = Array.isArray(msg.sources)
    ? msg.sources.filter(s => typeof s === 'string' && s.trim())
    : []
  if (srcs.length > 0) msg.sources = srcs
  else delete msg.sources
  return msg
}

export default function App() {
  const [currentSessionId, setCurrentSessionId] = useLocalStorage('workspace_current_session', null)
  const [ragEnabled, setRagEnabled] = useLocalStorage('workspace_rag_enabled', false)
  const [configs, setConfigs] = useLocalStorage('workspace_configs', [])
  const [selectedConfigId, setSelectedConfigId] = useLocalStorage('workspace_selected_config', null)
  // 会话 -> 模型配置 ID 映射：每个会话记住最后使用的模型配置
  const [sessionModelMap, setSessionModelMap] = useLocalStorage('workspace_session_models', {})

  // 会话列表与当前会话消息，均以后端为准
  const [sessions, setSessions] = useState([])  // [{ session_id, preview, message_count, last_activity }]
  const [messages, setMessages] = useState([])  // 当前会话的消息 [{ role, content, ... }]

  const [isLoading, setIsLoading] = useState(false)      // 发送消息中
  const [loadingHistory, setLoadingHistory] = useState(false) // 切换会话加载历史中
  const [showSettings, setShowSettings] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [notice, setNotice] = useState(null)             // 全局提示（网络错误等）
  const noticeTimer = useRef(null)
  const hasSent = useRef(false)                          // 启动恢复完成前是否已发送过消息

  // --- Fix 3: auto-select first config on mount ---
  useEffect(() => {
    if (configs.length > 0 && !selectedConfigId) {
      setSelectedConfigId(configs[0].id)
    }
  }, []) // run once on mount

  const selectedConfig = useMemo(() => {
    return configs.find(c => c.id === selectedConfigId) || null
  }, [configs, selectedConfigId])

  // 切换会话时恢复该会话保存的模型配置；无记录或配置已删除时保持全局默认
  const applySessionModel = useCallback((sessionId) => {
    const saved = sessionModelMap[sessionId]
    if (saved && configs.some(c => c.id === saved)) {
      setSelectedConfigId(saved)
    }
  }, [sessionModelMap, configs, setSelectedConfigId])

  // 会话产生/发送消息后，记录该会话使用的模型配置
  const rememberSessionModel = useCallback((sessionId) => {
    if (sessionId && selectedConfigId) {
      setSessionModelMap(prev => ({ ...prev, [sessionId]: selectedConfigId }))
    }
  }, [selectedConfigId, setSessionModelMap])

  // 用户手动切换模型：更新全局选择 + 当前会话的映射
  const handleModelChange = useCallback((configId) => {
    setSelectedConfigId(configId)
    if (currentSessionId) {
      setSessionModelMap(prev => {
        const next = { ...prev }
        if (configId) next[currentSessionId] = configId
        else delete next[currentSessionId]
        return next
      })
    }
  }, [currentSessionId, setSelectedConfigId, setSessionModelMap])

  // --- 提示条 ---
  const showNotice = useCallback((msg) => {
    setNotice(msg)
    if (noticeTimer.current) clearTimeout(noticeTimer.current)
    noticeTimer.current = setTimeout(() => setNotice(null), 3000)
  }, [])

  useEffect(() => () => { if (noticeTimer.current) clearTimeout(noticeTimer.current) }, [])

  // --- 会话列表 ---
  const normalizeSessions = useCallback((data) => {
    // 后端返回 { session_id: {preview, message_count, last_activity} }，转数组并按最近活动排序
    return Object.entries(data)
      .map(([session_id, s]) => ({ session_id, ...s }))
      .sort((a, b) => new Date(b.last_activity) - new Date(a.last_activity))
  }, [])

  const refreshSessions = useCallback(async ({ silent = false } = {}) => {
    try {
      const data = await fetchSessions()
      const list = normalizeSessions(data)
      setSessions(list)
      return list
    } catch (err) {
      if (!silent) showNotice(`加载会话列表失败：${err.message}`)
      return null
    }
  }, [normalizeSessions, showNotice])

  const loadSessionMessages = useCallback(async (sessionId) => {
    setLoadingHistory(true)
    try {
      const data = await fetchSessionMessages(sessionId)
      setMessages((data.messages || []).map(normalizeHistoryMessage))
    } catch (err) {
      showNotice(`加载对话内容失败：${err.message}`)
    } finally {
      setLoadingHistory(false)
    }
  }, [showNotice])

  // --- 启动：加载会话列表并恢复会话（需求 7）---
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const list = await refreshSessions()
      // 用户已抢先发送消息（新会话已建立），不再用启动恢复覆盖当前状态
      if (cancelled || !list || hasSent.current) return
      // 恢复当前会话；若已不存在（如被删除），回退到最近一次使用的会话
      const current = list.find(s => s.session_id === currentSessionId)
      const target = current || list[0] || null
      if (target) {
        if (!current) setCurrentSessionId(target.session_id)
        // 恢复该会话保存的模型配置
        applySessionModel(target.session_id)
        try {
          const data = await fetchSessionMessages(target.session_id)
          if (!cancelled) setMessages((data.messages || []).map(normalizeHistoryMessage))
        } catch (err) {
          if (!cancelled) showNotice(`加载对话内容失败：${err.message}`)
        }
      } else {
        // 没有任何会话，显示空白对话界面
        setCurrentSessionId(null)
      }
    })()
    return () => { cancelled = true }
  }, []) // 仅挂载时执行

  // --- 发送消息 ---
  const handleSend = useCallback(async (text) => {
    // 新对话时 sid 为 null，不传 session_id，由后端生成新的 session_id
    const sid = currentSessionId
    hasSent.current = true
    setIsLoading(true)

    // 发送时记录当时使用的模型名称，切换模型不影响历史消息的显示
    const modelName = selectedConfig?.model || '默认模型'

    setMessages(prev => [
      ...prev,
      { role: 'user', content: text, model: modelName },
      { role: 'assistant', content: '', isLoading: true, model: modelName }
    ])

    const apiKey = selectedConfig?.apiKey || null
    const model = selectedConfig?.model || null
    const provider = selectedConfig?.provider || null
    const baseUrl = selectedConfig?.base_url || null

    const finishAssistant = (content, extra = {}) => {
      setMessages(prev => {
        const msgs = [...prev]
        const li = msgs.length - 1
        if (li >= 0 && msgs[li].role === 'assistant') msgs[li] = { ...msgs[li], content, ...extra, isLoading: false }
        return msgs
      })
    }

    const fail = (errMsg) => {
      setMessages(prev => {
        const msgs = [...prev]
        const li = msgs.length - 1
        if (li >= 0 && msgs[li].role === 'assistant') msgs[li] = { ...msgs[li], content: '', isLoading: false }
        return [...msgs, { role: 'system', content: `❌ ${errMsg}`, isError: true }]
      })
    }

    try {
      if (ragEnabled) {
        const result = await ask(text, sid, apiKey, model, provider, baseUrl)
        // 需求 8：后端返回的 session_id 以最新为准（新对话或后端重建会话时可能变化）
        if (result.session_id) {
          setCurrentSessionId(result.session_id)
          rememberSessionModel(result.session_id)
        }
        if (result.error) {
          fail(result.error)
        } else {
          finishAssistant(result.answer, { sources: result.sources || [] })
        }
      } else {
        const result = await generate(text, sid, apiKey, model, provider, baseUrl)
        if (result.session_id) {
          setCurrentSessionId(result.session_id)
          rememberSessionModel(result.session_id)
        }
        finishAssistant(result.response)
      }
      // 同步会话列表（预览、消息数）
      refreshSessions({ silent: true })
    } catch (err) {
      fail(`请求失败：${err.message}`)
    } finally {
      setIsLoading(false)
    }
  }, [currentSessionId, ragEnabled, selectedConfig, setCurrentSessionId, rememberSessionModel, refreshSessions])

  // --- 会话操作 ---
  const handleSelectSession = useCallback(async (session) => {
    setCurrentSessionId(session.session_id)
    // 切换到该会话最后使用的模型配置（无记录时保持全局默认）
    applySessionModel(session.session_id)
    setShowHistory(false)
    await loadSessionMessages(session.session_id)
  }, [setCurrentSessionId, applySessionModel, loadSessionMessages])

  const handleNewChat = useCallback(() => {
    // 清空界面；不传 session_id，下一条消息由后端生成新会话
    setCurrentSessionId(null)
    setMessages([])
    setShowHistory(false)
  }, [setCurrentSessionId])

  const handleClearHistory = useCallback(async () => {
    if (!window.confirm('确认清空全部对话历史？此操作不可恢复。')) return
    try {
      await clearAllSessions()
    } catch (err) {
      showNotice(`清空失败：${err.message}`)
      return
    }
    setSessions([])
    setCurrentSessionId(null)
    setMessages([])
    setSessionModelMap({})
  }, [showNotice, setCurrentSessionId, setSessionModelMap])

  const handleDeleteSession = useCallback(async (sessionId) => {
    if (!window.confirm('确认删除该对话？')) return
    try {
      await deleteSession(sessionId)
    } catch (err) {
      showNotice(`删除失败：${err.message}`)
      return
    }
    // 清理该会话的模型映射
    setSessionModelMap(prev => {
      const next = { ...prev }
      delete next[sessionId]
      return next
    })
    const list = (await refreshSessions({ silent: true })) || sessions.filter(s => s.session_id !== sessionId)
    if (currentSessionId === sessionId) {
      if (list.length > 0) {
        // 自动切换到剩余的第一个会话，并恢复其模型配置
        setCurrentSessionId(list[0].session_id)
        applySessionModel(list[0].session_id)
        await loadSessionMessages(list[0].session_id)
      } else {
        setCurrentSessionId(null)
        setMessages([])
      }
    }
  }, [sessions, currentSessionId, refreshSessions, loadSessionMessages, applySessionModel, setSessionModelMap, showNotice, setCurrentSessionId])

  // --- 文件上传提示 ---
  const addSystemMessage = useCallback((msg) => {
    setMessages(prev => [...prev, msg])
  }, [])

  // --- settings ---
  const handleSaveConfig = useCallback((cfg) => {
    const newConfig = { ...cfg, id: uid() }
    setConfigs(prev => [...prev, newConfig])
    if (!selectedConfigId) setSelectedConfigId(newConfig.id)
  }, [setConfigs, selectedConfigId, setSelectedConfigId])

  const handleDeleteConfig = useCallback((id) => {
    setConfigs(prev => prev.filter(c => c.id !== id))
    if (selectedConfigId === id) setSelectedConfigId(null)
    // 清理指向已删除配置的会话映射
    setSessionModelMap(prev => {
      const next = {}
      for (const [sid, cid] of Object.entries(prev)) {
        if (cid !== id) next[sid] = cid
      }
      return next
    })
  }, [setConfigs, selectedConfigId, setSelectedConfigId, setSessionModelMap])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <button
            className={`history-toggle ${showHistory ? 'active' : ''}`}
            onClick={() => setShowHistory(v => !v)}
            aria-label="历史记录" title="对话历史"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </button>
          <h1 className="app-title"><span className="title-icon">⚡</span>Workspace AI</h1>
        </div>
        <div className="header-right">
          <ModelSelector
            configs={configs} selectedId={selectedConfigId} onChange={handleModelChange}
            onOpenSettings={() => setShowSettings(true)}
          />
          <StatusBar />
        </div>
      </header>

      <div className="app-body">
        <HistoryPanel
          sessions={sessions}
          activeSessionId={currentSessionId}
          onSelect={handleSelectSession}
          onClear={handleClearHistory}
          onNew={handleNewChat}
          onDelete={handleDeleteSession}
          visible={showHistory}
        />
        <ChatArea messages={messages} hasHistory={sessions.length > 0} loadingHistory={loadingHistory} />
      </div>

      <div className="input-area">
        <FileUpload onUploaded={(name) => { addSystemMessage({ role: 'system', content: `📄 文件已上传并处理：${name}` }) }} />
        <div className="input-controls">
          <RagToggle enabled={ragEnabled} onChange={setRagEnabled} />
        </div>
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </div>

      {showSettings && (
        <SettingsPanel configs={configs} onSave={handleSaveConfig} onDelete={handleDeleteConfig} onClose={() => setShowSettings(false)} />
      )}

      {notice && <div className="toast" role="alert">{notice}</div>}
    </div>
  )
}
