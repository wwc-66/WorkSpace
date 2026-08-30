import './ModelSelector.css'

export default function ModelSelector({ configs, selectedId, onChange, onOpenSettings }) {
  const selected = configs.find(c => c.id === selectedId)
  const label = selected
    ? `${selected.name} (${selected.model})`
    : '默认'

  return (
    <div className="model-selector">
      <div className="model-selector-box">
        {configs.length === 0 ? (
          <span className="model-label">{label}</span>
        ) : (
          <select
            className="model-select"
            value={selectedId || ''}
            onChange={e => onChange(e.target.value || null)}
          >
            <option value="">默认配置（后端）</option>
            {configs.map(cfg => (
              <option key={cfg.id} value={cfg.id}>{cfg.name} ({cfg.model})</option>
            ))}
          </select>
        )}
        <button
          className="model-add-btn"
          onClick={onOpenSettings}
          aria-label="添加模型配置"
          title="添加模型配置"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
