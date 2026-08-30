import './HistoryPanel.css'

function formatTime(ts) {
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

export default function HistoryPanel({ sessions, activeSessionId, onSelect, onClear, onNew, onDelete, visible }) {
  return (
    <div className={`history-panel ${visible ? 'open' : ''}`}>
      <div className="history-header">
        <h3>💬 对话记录</h3>
        <div className="history-actions">
          <button className="btn-new-chat" onClick={onNew} title="新建对话">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <button className="btn-clear-all" onClick={onClear} title="清空全部历史">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>
      </div>
      <div className="history-list">
        {sessions.length === 0 ? (
          <p className="history-empty">暂无对话记录</p>
        ) : (
          sessions.map(item => (
            <div
              key={item.session_id}
              className={`history-item-row ${item.session_id === activeSessionId ? 'active' : ''}`}
            >
              <button className="history-item" onClick={() => onSelect(item)}>
                <span className="history-preview">{item.preview}</span>
                <span className="history-time">{formatTime(item.last_activity)}</span>
                <span className="history-count">{item.message_count} 条消息</span>
              </button>
              <button
                className="btn-delete-session"
                onClick={(e) => { e.stopPropagation(); onDelete(item.session_id) }}
                title="删除此对话"
                aria-label="删除此对话"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
