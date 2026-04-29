import { useState, useCallback, useEffect } from 'react'
import './SplitManager.css'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'

function IconBack() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M12 4l-6 6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconTrash() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M3 4h10M5 4V3a1 1 0 011-1h4a1 1 0 011 1v1M6 7v5M10 7v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 4l1 9a1 1 0 001 1h4a1 1 0 001-1l1-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconEdit() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M9.5 2.5l2 2L5 11H3v-2L9.5 2.5z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8 4l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="4" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M10 10l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function IconCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 7l3 3 5-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

function SplitToggle({ value, onChange }) {
  return (
    <div className="sm-toggle">
      <button type="button" className={`sm-toggle__btn ${value === '是' ? 'active' : ''}`} onClick={() => onChange('是')}>拆零</button>
      <button type="button" className={`sm-toggle__btn ${value === '否' ? 'active' : ''}`} onClick={() => onChange('否')}>不拆零</button>
    </div>
  )
}

function InlineEditRow({ item, onSave, onCancel }) {
  const [code, setCode] = useState(item.code)
  const [split, setSplit] = useState(item.split)

  const handleSave = () => {
    if (!code.trim()) return
    onSave(item.code, code.trim(), split)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter') handleSave()
    if (e.key === 'Escape') onCancel()
  }

  return (
    <tr className="sm-row--editing">
      <td><input className="sm-cell-input" value={code} onChange={e => setCode(e.target.value)} onKeyDown={handleKey} autoFocus /></td>
      <td><SplitToggle value={split} onChange={setSplit} /></td>
      <td className="sm-cell-actions">
        <button className="sm-action-btn sm-action-btn--save" onClick={handleSave} title="保存"><IconCheck /></button>
        <button className="sm-action-btn sm-action-btn--cancel" onClick={onCancel} title="取消"><IconX /></button>
      </td>
    </tr>
  )
}

export default function SplitManager({ onBack }) {
  const [codes, setCodes] = useState([])
  const [newCode, setNewCode] = useState('')
  const [newSplit, setNewSplit] = useState('是')
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [msg, setMsg] = useState(null)
  const [editingCode, setEditingCode] = useState(null)

  const fetchCodes = useCallback(() => {
    fetch(`${API_BASE}/split-codes`)
      .then(res => res.json())
      .then(data => setCodes(data.codes || []))
      .catch(() => flashMsg('⚠️ 获取列表失败', 'error'))
  }, [])

  useEffect(() => { fetchCodes() }, [fetchCodes])

  const flashMsg = (text, type) => {
    setMsg({ text, type, id: Date.now() })
    setTimeout(() => setMsg(null), 3000)
  }

  const handleAdd = async () => {
    if (!newCode.trim()) { flashMsg('请输入商品编码', 'error'); return }
    if (!/^[A-Za-z0-9]/.test(newCode.trim())) { flashMsg('编码需以字母或数字开头', 'error'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/split-codes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: newCode.trim(), split: newSplit }),
      })
      if (res.status === 409) { flashMsg('该商品编码已存在', 'error'); return }
      if (!res.ok) { const d = await res.json(); flashMsg(d.detail || '添加失败', 'error'); return }
      setNewCode('')
      flashMsg(`✅ 已添加 ${newCode.trim()} → ${newSplit}`, 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
    finally { setLoading(false) }
  }

  const handleEditSave = async (oldCode, newCode, split) => {
    try {
      const res = await fetch(`${API_BASE}/split-codes/${encodeURIComponent(oldCode)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: newCode, split }),
      })
      if (!res.ok) { const d = await res.json(); flashMsg(d.detail || '修改失败', 'error'); return }
      setEditingCode(null)
      flashMsg(`✅ 已修改 ${oldCode} → ${newCode}`, 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
  }

  const handleDelete = async (code) => {
    try {
      const res = await fetch(`${API_BASE}/split-codes/${encodeURIComponent(code)}`, { method: 'DELETE' })
      if (!res.ok) { flashMsg('删除失败', 'error'); return }
      flashMsg(`🗑️ 已删除 ${code}`, 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
  }

  const handleDeduplicate = async () => {
    if (!confirm('确定要去重吗？将自动移除重复的商品编码（保留首条）。')) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/split-codes/deduplicate`, { method: 'POST' })
      if (!res.ok) { flashMsg('去重失败', 'error'); return }
      const data = await res.json()
      flashMsg(`✅ 已移除 ${data.removed} 条重复记录，剩余 ${data.kept} 条`, 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
    finally { setLoading(false) }
  }

  const filtered = codes.filter(c =>
    !search || c.code.toLowerCase().includes(search.toLowerCase())
  )
  const sorted = [...filtered].sort((a, b) => a.code.localeCompare(b.code))

  return (
    <div className="split-manager">
      <header className="split-manager__header">
        <button className="split-manager__back" onClick={onBack} type="button">
          <IconBack /> 返回转换
        </button>
        <h2>商品拆零管理</h2>
        <span className="split-manager__total">{codes.length} 条记录</span>
      </header>

      {msg && <div key={msg.id} className={`sm-toast sm-toast--${msg.type}`}>{msg.text}</div>}

      <section className="sm-add">
        <div className="sm-add__row">
          <input
            className="sm-input"
            placeholder="输入商品编码，如 LMTZ0150001"
            value={newCode}
            onChange={e => setNewCode(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <SplitToggle value={newSplit} onChange={setNewSplit} />
          <button className="sm-add__btn" onClick={handleAdd} disabled={loading}>
            {loading ? '添加中…' : '+ 添加'}
          </button>
        </div>
      </section>

      <section className="sm-toolbar">
        <div className="sm-search">
          <IconSearch />
          <input
            className="sm-search__input"
            placeholder="搜索商品编码…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button className="sm-dedup-btn" onClick={handleDeduplicate} disabled={loading}>
          去重清理
        </button>
      </section>

      <section className="sm-table">
        {sorted.length === 0 ? (
          <div className="sm-empty">{search ? '未找到匹配的编码' : '暂无数据，请先添加'}</div>
        ) : (
          <table>
            <thead>
              <tr><th>商品编码</th><th>拆零规则</th><th>操作</th></tr>
            </thead>
            <tbody>
              {sorted.map(c =>
                editingCode === c.code ? (
                  <InlineEditRow
                    key={c.code}
                    item={c}
                    onSave={handleEditSave}
                    onCancel={() => setEditingCode(null)}
                  />
                ) : (
                  <tr key={c.code}>
                    <td className="sm-code">{c.code}</td>
                    <td>
                      <span className={`sm-badge sm-badge--${c.split === '是' ? 'yes' : 'no'}`}>
                        {c.split === '是' ? '拆零 (二级单位)' : '不拆零 (最小单位)'}
                      </span>
                    </td>
                    <td className="sm-cell-actions">
                      <button className="sm-action-btn" onClick={() => setEditingCode(c.code)} title="编辑"><IconEdit /></button>
                      <button className="sm-action-btn sm-action-btn--danger" onClick={() => handleDelete(c.code)} title="删除"><IconTrash /></button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
