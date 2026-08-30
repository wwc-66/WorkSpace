import './RagToggle.css'

export default function RagToggle({ enabled, onChange }) {
  return (
    <button
      className={`rag-toggle ${enabled ? 'active' : ''}`}
      onClick={() => onChange(!enabled)}
      role="switch"
      aria-checked={enabled}
      aria-label="知识库开关"
    >
      <span className="rag-toggle-track"><span className="rag-toggle-thumb" /></span>
      <span className="rag-toggle-label">📁 {enabled ? '知识库已启用' : '启用知识库'}</span>
    </button>
  )
}
