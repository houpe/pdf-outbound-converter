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

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="4" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M10 10l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

export default function SplitManager({ onBack }) {
  const [codes, setCodes] = useState([])
  const [newCode, setNewCode] = useState('')
  const [newSplit, setNewSplit] = useState('是')
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [msg, setMsg] = useState(null)

  const fetchCodes = useCallback(() => {
    fetch(`${API_BASE}/split-codes`)
      .then(res => res.json())
      .then(data => setCodes(data.codes || []))
      .catch(() => flashMsg('⚠️ 获取列表失败', 'error'))
  }, [])

  useEffect(() => { fetchCodes() }, [fetchCodes])

  const flashMsg = (text, type) => {
    setMsg({ text, type })
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

  const handleDelete = async (code) => {
    try {
      const res = await fetch(`${API_BASE}/split-codes/${encodeURIComponent(code)}`, { method: 'DELETE' })
      if (!res.ok) { flashMsg('删除失败', 'error'); return }
      flashMsg(`🗑️ 已删除 ${code}`, 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
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

      {msg && <div className={`sm-toast sm-toast--${msg.type}`}>{msg.text}</div>}

      <section className="sm-add">
        <div className="sm-add__row">
          <input
            className="sm-input"
            placeholder="输入商品编码，如 LMTZ0150001"
            value={newCode}
            onChange={e => setNewCode(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <div className="sm-toggle">
            <button
              type="button"
              className={`sm-toggle__btn ${newSplit === '是' ? 'active' : ''}`}
              onClick={() => setNewSplit('是')}
            >拆零</button>
            <button
              type="button"
              className={`sm-toggle__btn ${newSplit === '否' ? 'active' : ''}`}
              onClick={() => setNewSplit('否')}
            >不拆零</button>
          </div>
          <button className="sm-add__btn" onClick={handleAdd} disabled={loading}>
            {loading ? '添加中…' : '+ 添加'}
          </button>
        </div>
      </section>

      <section className="sm-search">
        <IconSearch />
        <input
          className="sm-search__input"
          placeholder="搜索商品编码…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
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
              {sorted.map(c => (
                <tr key={c.code}>
                  <td className="sm-code">{c.code}</td>
                  <td>
                    <span className={`sm-badge sm-badge--${c.split === '是' ? 'yes' : 'no'}`}>
                      {c.split === '是' ? '拆零 (二级单位)' : '不拆零 (最小单位)'}
                    </span>
                  </td>
                  <td>
                    <button className="sm-del" onClick={() => handleDelete(c.code)} title="删除">
                      <IconTrash />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
