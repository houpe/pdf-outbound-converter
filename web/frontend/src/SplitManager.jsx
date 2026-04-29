import { useState, useCallback, useEffect, useRef } from 'react'
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

function IconLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 3v8M3 7h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

function IconX() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M6 6l8 8M14 6l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
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

function formatDateTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso.replace(' ', 'T'))
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export default function SplitManager({ onBack }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [splitFilter, setSplitFilter] = useState('全部')
  const [msg, setMsg] = useState(null)

  const [pending, setPending] = useState(new Set())
  const [addRowVisible, setAddRowVisible] = useState(false)
  const newInputRef = useRef(null)

  const flashMsg = useCallback((text, type) => {
    setMsg({ text, type, id: Date.now() })
    setTimeout(() => setMsg(null), 3000)
  }, [])

  const fetchCodes = useCallback(() => {
    fetch(`${API_BASE}/split-codes`)
      .then(res => res.json())
      .then(data => setRows((data.codes || []).map(row => ({ ...row, id: row.code, isNew: false }))))
      .catch(() => flashMsg('️ 获取列表失败', 'error'))
  }, [flashMsg])

  useEffect(() => { fetchCodes() }, [fetchCodes])

  const updateCell = (id, field, value) => {
    setRows(prev => prev.map(r => r.id === id ? { ...r, [field]: value } : r))
    setPending(prev => new Set(prev).add(id))
  }

  const saveAll = async () => {
    const changed = rows.filter(r => pending.has(r.id))
    if (changed.length === 0) { flashMsg('没有需要保存的更改', 'warn'); return }

    setLoading(true)
    setPending(new Set())
    try {
      const payload = changed.map(r => ({
        id: r.isNew ? '' : r.id,
        code: r.code,
        split: r.split,
      }))
      const res = await fetch(`${API_BASE}/split-codes/batch`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const data = await res.json()
        const errMsg = Array.isArray(data.detail)
          ? data.detail.map(e => e.error).join(', ')
          : (data.detail || '未知错误')
        flashMsg(`保存失败: ${errMsg}`, 'error')
        fetchCodes()
        return
      }
      flashMsg(`✅ 已保存 ${changed.length} 条记录`, 'success')
      fetchCodes()
      setAddRowVisible(false)
    } catch { flashMsg('请求失败', 'error'); fetchCodes() }
    finally { setLoading(false) }
  }

  const [deleteTarget, setDeleteTarget] = useState(null)

  const discardRow = (row) => {
    if (row.isNew) {
      setRows(prev => prev.filter(r => r.id !== row.id))
      setPending(prev => {
        const next = new Set(prev)
        next.delete(row.id)
        return next
      })
      setAddRowVisible(false)
      return
    }
    setDeleteTarget(row)
  }

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/split-codes/${encodeURIComponent(deleteTarget.id)}`, { method: 'DELETE' })
      if (!res.ok) {
        flashMsg('删除失败', 'error')
        return
      }
      flashMsg('已删除', 'success')
      fetchCodes()
    } catch { flashMsg('请求失败', 'error') }
    finally { 
      setLoading(false)
      setDeleteTarget(null)
    }
  }

  const addNewRow = () => {
    const id = `_new_${Date.now()}`
    setRows(prev => [{ id, code: '', split: '是', created_at: '', isNew: true }, ...prev])
    setAddRowVisible(true)
    setPending(prev => new Set(prev).add(id))
    setTimeout(() => newInputRef.current?.focus(), 50)
  }

  const filtered = rows.filter(r => {
    const code = r.code || ''
    const matchSearch = !search || code.toLowerCase().includes(search.toLowerCase())
    const matchSplit = splitFilter === '全部' || r.split === (splitFilter === '拆零' ? '是' : '否')
    return matchSearch && matchSplit
  })

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const currentPage = Math.min(page, totalPages)

  const startIndex = (currentPage - 1) * pageSize
  const endIndex = startIndex + pageSize
  const paginatedItems = filtered.slice(startIndex, endIndex)

  return (
    <div className="split-manager">
      <header className="split-manager__header">
        <button className="split-manager__back" onClick={onBack} type="button">
          <IconBack /> 返回转换
        </button>
        <h2>商品拆零管理</h2>
        <span className="split-manager__total">{rows.length} 条记录</span>
      </header>

      {msg && <div key={msg.id} className={`sm-toast sm-toast--${msg.type}`}>{msg.text}</div>}

      <section className="sm-toolbar">
        <div className="sm-search">
          <IconSearch />
          <input
            className="sm-search__input"
            placeholder="搜索商品编码…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <select
          className="sm-filter-select"
          value={splitFilter}
          onChange={e => { setSplitFilter(e.target.value); setPage(1) }}
        >
          <option value="全部">全部规则</option>
          <option value="拆零">拆零</option>
          <option value="不拆零">不拆零</option>
        </select>
        <button className="sm-add-btn" onClick={addNewRow} type="button" disabled={addRowVisible}>
          <IconPlus /> 新增
        </button>
        <button className="sm-save-btn" onClick={saveAll} disabled={loading || pending.size === 0}>
          {loading ? '保存中…' : `保存 (${pending.size})`}
        </button>
      </section>

      <section className="sm-table">
        {filtered.length === 0 ? (
          <div className="sm-empty">{search || splitFilter !== '全部' ? '未找到匹配的编码' : '暂无数据，请点击 "+ 新增" 添加'}</div>
        ) : (
          <>
            <table>
              <thead>
                <tr><th>商品编码</th><th>拆零规则</th><th>创建时间</th><th>操作</th></tr>
              </thead>
              <tbody>
                {paginatedItems.map(r => {
                  const isNew = r.isNew
                  const displayCode = r.code || ''
                  return (
                    <tr key={r.id} className={isNew ? 'sm-row--new' : ''}>
                      <td className="sm-code">
                        <input
                          ref={isNew ? newInputRef : null}
                          className="sm-code__input"
                          value={displayCode}
                          onChange={e => updateCell(r.id, 'code', e.target.value)}
                          placeholder="输入商品编码"
                          onKeyDown={e => e.key === 'Enter' && saveAll()}
                        />
                      </td>
                      <td>
                        <SplitToggle value={r.split} onChange={val => updateCell(r.id, 'split', val)} />
                      </td>
                      <td className="sm-time">{r.created_at ? formatDateTime(r.created_at) : '—'}</td>
                      <td className="sm-cell-actions">
                        <button className="sm-action-btn sm-action-btn--danger" onClick={() => discardRow(r)} title="删除"><IconTrash /></button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <div className="sm-pagination">
              <div className="sm-pagination__info">
                显示 <strong>{startIndex + 1}-{Math.min(endIndex, filtered.length)}</strong> 条，共 <strong>{filtered.length}</strong> 条
              </div>
              <div className="sm-pagination__group">
                <div className="sm-pagination__size-box">
                  <span className="sm-pagination__size-label">每页</span>
                  <select className="sm-select" value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                  </select>
                  <span className="sm-pagination__size-label">条</span>
                </div>
                <div className="sm-pagination__nav">
                  <button
                    className="sm-pagination__btn"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}
                  >
                    <IconLeft />
                  </button>
                  <span className="sm-pagination__page-text">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    className="sm-pagination__btn"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                  >
                    <IconRight />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {deleteTarget && (
        <div className="sm-dialog__overlay" onClick={() => !loading && setDeleteTarget(null)}>
          <div className="sm-dialog__container">
            <div className="sm-dialog__wrapper">
              <div className="sm-dialog__panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'var(--text)' }}>确认删除</h3>
                  <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '4px' }} onClick={() => setDeleteTarget(null)} disabled={loading}>
                    <IconX />
                  </button>
                </div>
                <div style={{ marginBottom: '24px', fontSize: '14px', color: 'var(--text-muted)' }}>
                  确定要删除编码 <strong style={{ color: 'var(--text)' }}>{deleteTarget.code}</strong> 吗？<br/>此操作不可撤销。
                </div>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button className="sm-dialog__btn sm-dialog__btn--cancel" onClick={() => setDeleteTarget(null)} disabled={loading}>取消</button>
                  <button className="sm-dialog__btn sm-dialog__btn--save" style={{ background: '#EF4444' }} onClick={handleConfirmDelete} disabled={loading}>
                    {loading ? '删除中...' : '确认删除'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
