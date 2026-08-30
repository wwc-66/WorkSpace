import { useState, useEffect } from 'react'
import { checkHealth } from '../api'
import './StatusBar.css'

export default function StatusBar() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        await checkHealth()
        if (!cancelled) setStatus('connected')
      } catch {
        if (!cancelled) setStatus('disconnected')
      }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  const labels = {
    checking:  { text: '检测中…',  cls: 'checking' },
    connected: { text: '已连接',   cls: 'connected' },
    disconnected: { text: '未连接', cls: 'disconnected' }
  }
  const { text, cls } = labels[status]

  return (
    <div className={`status-bar ${cls}`}>
      <span className="status-dot" />
      <span className="status-text">{text}</span>
    </div>
  )
}
