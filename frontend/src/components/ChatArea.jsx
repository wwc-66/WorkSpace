import { useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import './ChatArea.css'

export default function ChatArea({ messages, hasHistory, loadingHistory }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (loadingHistory && messages.length === 0) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <div className="spinner" />
          <p>正在加载对话…</p>
        </div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </div>
          <h2>Workspace AI Core</h2>
          <p>在下方输入问题，开始与 AI 对话</p>
          {hasHistory && (
            <p className="empty-sub">或点击左侧 ⏱️ 图标查看历史对话</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="chat-area">
      <div className="messages-list">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
