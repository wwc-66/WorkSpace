import './MessageBubble.css'

export default function MessageBubble({ message }) {
  const { role, content, sources, isError, isLoading } = message
  // 每条消息自带 model 字段（发送时记录），不读取全局配置，切换模型不影响历史消息
  const modelName = message.model || '默认模型'

  if (role === 'system') {
    return (
      <div className={`bubble-row ${role}`}>
        <div className={`bubble system ${isError ? 'error' : ''}`}>
          <p>{content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bubble-row ${role}`}>
      <div className="bubble-avatar">
        {role === 'user' ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        )}
      </div>
      <div className="bubble-content">
        {role === 'assistant' && modelName && (isLoading || content) && (
          <div className="bubble-model">{modelName}</div>
        )}
        <div className={`bubble ${role} ${isLoading ? 'loading' : ''}`}>
          {isLoading ? (
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          ) : (
            <p>{content}</p>
          )}
        </div>
        {sources && sources.length > 0 && (
          <div className="sources">
            {sources.map((s, i) => (
              <div key={i} className="source-item">来源：{s}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
