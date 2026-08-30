import { useState } from 'react'
import './SettingsPanel.css'

const PRESETS = [
  {
    key: 'deepseek',
    label: 'DeepSeek 官方',
    name: 'DeepSeek',
    provider: 'openai_compatible',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat'
  },
  {
    key: 'ollama',
    label: '本地 Qwen (Ollama)',
    name: 'Ollama Qwen',
    provider: 'openai_compatible',
    baseUrl: 'http://localhost:11434/v1',
    model: 'qwen2.5'
  },
  {
    key: 'bailian',
    label: '阿里云百炼',
    name: '阿里云百炼',
    provider: 'dashscope',
    baseUrl: '',
    model: 'qwen-plus'
  }
]

const PROVIDER_LABELS = {
  dashscope: 'dashscope（阿里云百炼）',
  openai_compatible: 'openai_compatible（OpenAI 兼容）'
}

export default function SettingsPanel({ configs, onSave, onDelete, onClose }) {
  const [name, setName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [provider, setProvider] = useState('dashscope')
  const [baseUrl, setBaseUrl] = useState('')
  const [error, setError] = useState('')

  const applyPreset = (preset) => {
    setName(preset.name)
    setProvider(preset.provider)
    setBaseUrl(preset.baseUrl)
    setModel(preset.model)
    setError('')
  }

  const handleAdd = () => {
    const trimmedName = name.trim()
    const trimmedKey = apiKey.trim()
    const trimmedModel = model.trim()

    if (!trimmedName || !trimmedKey || !trimmedModel) {
      setError('请填写所有字段')
      return
    }

    if (configs.some(c => c.name === trimmedName)) {
      setError('配置名称已存在')
      return
    }

    onSave({
      name: trimmedName,
      apiKey: trimmedKey,
      model: trimmedModel,
      provider,
      base_url: baseUrl.trim()
    })
    setName('')
    setApiKey('')
    setModel('')
    setProvider('dashscope')
    setBaseUrl('')
    setError('')
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={e => e.stopPropagation()}>
        <div className="settings-header">
          <h2>⚙️ 模型配置</h2>
          <button className="settings-close" onClick={onClose} aria-label="关闭">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="settings-body">
          <div className="settings-section">
            <h3 className="section-title">快速模板</h3>
            <div className="preset-row">
              {PRESETS.map(p => (
                <button key={p.key} className="preset-chip" onClick={() => applyPreset(p)}>
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <h3 className="section-title">新增配置</h3>
            <div className="config-form">
              <div className="form-field">
                <label>配置名称</label>
                <input type="text" value={name} onChange={e => { setName(e.target.value); setError('') }} placeholder="例如：我的千问" />
              </div>
              <div className="form-field">
                <label>API Key</label>
                <input type="password" value={apiKey} onChange={e => { setApiKey(e.target.value); setError('') }} placeholder="sk-..." />
              </div>
              <div className="form-field">
                <label>模型名称</label>
                <input type="text" value={model} onChange={e => { setModel(e.target.value); setError('') }} placeholder="例如：qwen-plus" />
              </div>
              <div className="form-field">
                <label>Provider</label>
                <select value={provider} onChange={e => { setProvider(e.target.value); setError('') }}>
                  <option value="dashscope">{PROVIDER_LABELS.dashscope}</option>
                  <option value="openai_compatible">{PROVIDER_LABELS.openai_compatible}</option>
                </select>
              </div>
              <div className="form-field">
                <label>Base URL（可选）</label>
                <input type="text" value={baseUrl} onChange={e => { setBaseUrl(e.target.value); setError('') }} placeholder="留空使用默认地址" />
              </div>
              {error && <p className="form-error">{error}</p>}
              <button className="btn-add" onClick={handleAdd}>保存配置</button>
            </div>
          </div>

          <div className="settings-section">
            <h3 className="section-title">
              已保存的配置
              {configs.length > 0 && <span className="count-badge">{configs.length}</span>}
            </h3>
            {configs.length === 0 ? (
              <p className="empty-hint">暂无配置，请添加</p>
            ) : (
              <div className="config-list">
                {configs.map(cfg => (
                  <div key={cfg.id} className="config-item">
                    <div className="config-info">
                      <div className="config-name-row">
                        <span className="config-name">{cfg.name}</span>
                        <span className={`provider-badge ${cfg.provider || 'dashscope'}`}>
                          {cfg.provider === 'openai_compatible' ? 'OpenAI 兼容' : '百炼'}
                        </span>
                      </div>
                      <span className="config-model">{cfg.model}</span>
                      <span className="config-key">{maskKey(cfg.apiKey)}</span>
                    </div>
                    <button className="btn-delete" onClick={() => onDelete(cfg.id)} aria-label={`删除 ${cfg.name}`}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function maskKey(key) {
  if (key.length <= 12) return key.slice(0, 4) + '****'
  return key.slice(0, 6) + '****' + key.slice(-4)
}
