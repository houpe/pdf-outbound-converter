import { useState, useCallback, useEffect, useReducer, useRef } from 'react'
import './CustomerPhoneManager.css'
import { IconBack, IconTrash, IconPlus } from './Icons'
import Button from './ui/Button'
import Modal from './ui/Modal'
import ToastViewport from './ui/Toast'
import useToast from './lib/hooks/useToast'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'
const TEMPLATE_KEY = 'pl'  // 派乐汉堡

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso.replace(' ', 'T'))
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function tableReducer(state, action) {
  switch (action.type) {
    case 'set_all':
      return { ...state, rows: action.rows, pending: new Set(), addRowVisible: false }
    case 'update_cell': {
      const nextRows = state.rows.map(r => (r.id === action.id ? { ...r, [action.field]: action.value } : r))
      const nextRow = nextRows.find(r => r.id === action.id)
      const nextPending = new Set(state.pending)
      if (!nextRow) return { ...state, rows: nextRows, pending: nextPending }
      if (nextRow.isNew) {
        nextPending.add(action.id)
        return { ...state, rows: nextRows, pending: nextPending }
      }
      const baseline = action.baseline
      const isDirty = !baseline
        || (nextRow.customer_code ?? '') !== (baseline?.customer_code ?? '')
        || (nextRow.phone ?? '') !== (baseline?.phone ?? '')
      if (isDirty) nextPending.add(action.id)
      else nextPending.delete(action.id)
      return { ...state, rows: nextRows, pending: nextPending }
    }
    case 'add_row': {
      const nextPending = new Set(state.pending)
      nextPending.add(action.row.id)
      return { ...state, rows: [action.row, ...state.rows], pending: nextPending, addRowVisible: true }
    }
    case 'remove_row': {
      const nextPending = new Set(state.pending)
      nextPending.delete(action.id)
      return { ...state, rows: state.rows.filter(r => r.id !== action.id), pending: nextPending, addRowVisible: action.hideAddRowVisible ? false : state.addRowVisible }
    }
    case 'discard':
      return { ...state, rows: action.rows, pending: new Set(), addRowVisible: false }
    default:
      return state
  }
}

export default function CustomerPhoneManager({ onBack }) {
  const [tableState, dispatch] = useReducer(tableReducer, {
    rows: [], pending: new Set(), addRowVisible: false,
  })
  const rows = tableState.rows
  const pending = tableState.pending

  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const newInputRef = useRef(null)
  const baselineByIdRef = useRef(new Map())
  const { toasts, pushToast, dismissToast } = useToast({ duration: 3000, limit: 3 })
  const notify = useCallback((msg, variant = 'info') => pushToast(msg, variant), [pushToast])

  const fetchList = useCallback(() => {
    fetch(`${API_BASE}/customer-phones?template_key=${TEMPLATE_KEY}`)
      .then(res => res.json())
      .then(data => {
        const nextRows = (data.items || []).map(row => ({ ...row, id: row.customer_code, isNew: false }))
        baselineByIdRef.current = new Map(
          nextRows.map(r => [r.id, { customer_code: r.customer_code ?? '', phone: r.phone ?? '' }]),
        )
        dispatch({ type: 'set_all', rows: nextRows })
      })
      .catch(() => notify('获取门店电话列表失败', 'danger'))
  }, [notify])

  useEffect(() => { fetchList() }, [fetchList])

  const updateCell = (id, field, value) => {
    dispatch({
      type: 'update_cell', id, field, value,
      baseline: baselineByIdRef.current.get(id),
    })
  }

  const addNewRow = () => {
    const id = `_new_${Date.now()}`
    dispatch({ type: 'add_row', row: { id, customer_code: '', phone: '', created_at: '', isNew: true } })
    setTimeout(() => newInputRef.current?.focus(), 50)
  }

  const discardAll = () => {
    const savedRows = rows.filter(r => !r.isNew).map(r => {
      const b = baselineByIdRef.current.get(r.id)
      return b ? { ...r, customer_code: b.customer_code, phone: b.phone, id: b.customer_code } : r
    })
    dispatch({ type: 'discard', rows: savedRows })
  }

  const saveAll = async () => {
    const changed = rows.filter(r => pending.has(r.id))
    if (changed.length === 0) { notify('没有需要保存的更改', 'warning'); return }
    setLoading(true)
    try {
      const payload = changed.map(r => ({
        id: r.isNew ? '' : r.id,
        customer_code: r.customer_code.trim(),
        phone: r.phone.trim(),
        template_key: TEMPLATE_KEY,
      }))
      const res = await fetch(`${API_BASE}/customer-phones/batch`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const data = await res.json()
        const errMsg = Array.isArray(data.detail)
          ? data.detail.map(e => e.error).join('；')
          : (data.detail || '未知错误')
        notify(`保存失败：${errMsg}`, 'danger')
        return
      }
      notify(`已保存 ${changed.length} 条记录`, 'success')
      fetchList()
    } catch {
      notify('请求失败', 'danger')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return
    if (deleteTarget.isNew) {
      dispatch({ type: 'remove_row', id: deleteTarget.id, hideAddRowVisible: true })
      setDeleteTarget(null)
      notify('已移除未保存的记录', 'info')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/customer-phones/${encodeURIComponent(deleteTarget.id)}?template_key=${TEMPLATE_KEY}`,
        { method: 'DELETE' },
      )
      if (!res.ok) { notify('删除失败', 'danger'); return }
      notify('已删除', 'success')
      baselineByIdRef.current.delete(deleteTarget.id)
      dispatch({ type: 'remove_row', id: deleteTarget.id })
    } catch {
      notify('请求失败', 'danger')
    } finally {
      setLoading(false)
      setDeleteTarget(null)
    }
  }

  const pendingCount = pending.size

  const filtered = rows.filter(r => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return (r.customer_code || '').toLowerCase().includes(q) || (r.phone || '').toLowerCase().includes(q)
  })

  return (
    <div className="cpm">
      <header className="cpm-header">
        <button className="cpm-back" onClick={onBack} type="button" aria-label="返回">
          <IconBack />
        </button>
        <h1 className="cpm-header__title">门店电话管理</h1>
        <Badge>{rows.filter(r => !r.isNew).length} 个门店</Badge>
      </header>

      <div className="cpm-toolbar">
        <div className="cpm-search">
          <input
            className="cpm-search__input"
            placeholder="搜索客户编码或电话…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="cpm-toolbar__actions">
          <Button variant="ghost" size="sm" onClick={addNewRow} disabled={loading}>
            <IconPlus /> 新增门店
          </Button>
        </div>
      </div>

      <div className="cpm-table-card">
        <div className="cpm-table-scroll">
          <table className="cpm-table">
            <thead>
              <tr>
                <th className="cpm-th--code">客户编码</th>
                <th className="cpm-th--phone">联系电话</th>
                <th className="cpm-th--time">创建时间</th>
                <th className="cpm-th--actions"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={4} className="cpm-empty">暂无门店电话记录</td></tr>
              )}
              {filtered.map(r => {
                const isDirty = pending.has(r.id)
                return (
                  <tr key={r.id} className={[
                    r.isNew ? 'cpm-row--new' : '',
                    isDirty ? 'cpm-row--dirty' : '',
                  ].filter(Boolean).join(' ')}>
                    <td className="cpm-code">
                      <div className="cpm-code__wrap">
                        {isDirty && <span className="cpm-dirty-dot" title="未保存更改" />}
                        <input
                          ref={r.isNew ? newInputRef : null}
                          className="cpm-code__input"
                          value={r.customer_code ?? ''}
                          onChange={e => updateCell(r.id, 'customer_code', e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && !loading && saveAll()}
                          disabled={loading}
                          placeholder="如 PHUN07306963"
                        />
                      </div>
                    </td>
                    <td className="cpm-phone">
                      <input
                        className="cpm-phone__input"
                        value={r.phone ?? ''}
                        onChange={e => updateCell(r.id, 'phone', e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && !loading && saveAll()}
                        disabled={loading}
                        placeholder="如 13800000000"
                      />
                    </td>
                    <td className="cpm-time">{r.created_at ? formatDateTime(r.created_at) : '—'}</td>
                    <td className="cpm-cell-actions">
                      <Button variant="ghost" size="sm" className="cpm-icon-btn cpm-icon-btn--danger"
                        onClick={() => setDeleteTarget(r)} aria-label="删除">
                        <IconTrash />
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {pendingCount > 0 && (
        <div className="cpm-dirtybar">
          <div className="cpm-dirtybar__left">
            <span className="cpm-dirtybar__dot" />
            <span>待保存 {pendingCount} 条更改</span>
          </div>
          <div className="cpm-dirtybar__actions">
            <Button variant="ghost" size="sm" onClick={discardAll} disabled={loading}>放弃更改</Button>
            <Button variant="primary" size="sm" onClick={saveAll} disabled={loading}>保存更改</Button>
          </div>
        </div>
      )}

      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="删除门店电话"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="danger" size="sm" onClick={handleConfirmDelete}>确认删除</Button>
          </>
        }
      >
        <p className="cpm-modal__message">
          确定删除客户编码 <strong>{deleteTarget?.customer_code || deleteTarget?.id}</strong> 的电话记录吗？
        </p>
      </Modal>

      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}

// Badge 内联（避免额外 import，SplitManager 也是类似处理）
function Badge({ children }) {
  return <span className="cpm-badge">{children}</span>
}
