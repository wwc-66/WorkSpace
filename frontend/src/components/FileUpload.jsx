import { useRef, useState } from 'react'
import { uploadFile } from '../api'
import './FileUpload.css'

export default function FileUpload({ onUploaded }) {
  const [dragOver, setDragOver] = useState(false)
  const [status, setStatus] = useState('idle')
  const [filename, setFilename] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file.name.endsWith('.txt')) {
      setStatus('error')
      setErrorMsg('仅支持 .txt 文件')
      return
    }
    setStatus('uploading')
    setFilename(file.name)
    setErrorMsg('')
    try {
      await uploadFile(file)
      setStatus('success')
      onUploaded?.(file.name)
    } catch (err) {
      setStatus('error')
      setErrorMsg(err.message || '上传失败')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true) }
  const handleDragLeave = () => setDragOver(false)
  const handleClick = () => inputRef.current?.click()

  const handleChange = (e) => {
    const file = e.target.files[0]
    if (file) handleFile(file)
  }

  const handleReset = () => {
    setStatus('idle'); setFilename(''); setErrorMsg('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="file-upload">
      {status === 'idle' && (
        <div
          className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleClick}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span>拖拽或点击上传 .txt 文档</span>
          <input ref={inputRef} type="file" accept=".txt" onChange={handleChange} className="file-input-hidden" />
        </div>
      )}
      {status === 'uploading' && (
        <div className="upload-status uploading"><div className="spinner" /><span>正在上传 {filename}…</span></div>
      )}
      {status === 'success' && (
        <div className="upload-status success">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <span>已上传：{filename}</span>
          <button className="btn-dismiss" onClick={handleReset} aria-label="清除">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      )}
      {status === 'error' && (
        <div className="upload-status error">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <span>{errorMsg}</span>
          <button className="btn-dismiss" onClick={handleReset} aria-label="清除">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
