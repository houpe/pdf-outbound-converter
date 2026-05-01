import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import './SplitManager.css'
import { IconBack, IconTrash, IconSearch, IconLeft, IconRight, IconPlus } from './Icons'
import SplitToggle from './SplitToggle'
import Button from './ui/Button'
import Badge from './ui/Badge'
import Modal from './ui/Modal'
import ToastViewport from './ui/Toast'
import useToast from './lib/hooks/useToast'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'

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

  const [pending, setPending] = useState(new Set())
  const [backConfirmOpen, setBackConfirmOpen] = useState(false)
  const [addRowVisible, setAddRowVisible] = useState(false)
  const newInputRef = useRef(null)

  const baselineRowsRef = useRef([])
  const baselineByIdRef = useRef(new Map())
  const { toasts, pushToast, dismissToast } = useToast({ duration: 3000, limit: 3 })

  const notify = useCallback((message, variant = 'info') => {
    pushToast({ message, variant })
  }, [pushToast])

  const fetchCodes = useCallback(() => {
    fetch(`${API_BASE}/split-codes`)
      .then(res => res.json())
      .then(data => {
        const nextRows = (data.codes || []).map(row => ({ ...row, id: row.code, isNew: false }))
        baselineRowsRef.current = nextRows
        baselineByIdRef.current = new Map(
          nextRows.map(r => [r.id, { code: r.code ?? '', split: r.split }]),
        )
        setRows(nextRows)
        setPending(new Set())
        setAddRowVisible(false)
      })
      .catch(() => notify('获取列表失败', 'danger'))
  }, [notify])

  useEffect(() => { fetchCodes() }, [fetchCodes])

  const updateCell = useCallback((id, field, value) => {
    setRows(prevRows => {
      const nextRows = prevRows.map(r => (r.id === id ? { ...r, [field]: value } : r))
      const nextRow = nextRows.find(r => r.id === id)

      setPending(prevPending => {
        const nextPending = new Set(prevPending)
        if (!nextRow) return nextPending
        if (nextRow.isNew) {
          nextPending.add(id)
          return nextPending
        }

        const baseline = baselineByIdRef.current.get(id)
        const baselineCode = baseline?.code ?? ''
        const baselineSplit = baseline?.split
        const isDirty = !baseline
          || (nextRow.code ?? '') !== baselineCode
          || nextRow.split !== baselineSplit

        if (isDirty) nextPending.add(id)
        else nextPending.delete(id)
        return nextPending
      })

      return nextRows
    })
  }, [])

  const discardChanges = useCallback(() => {
    setRows(baselineRowsRef.current)
    setPending(new Set())
    setAddRowVisible(false)
    notify('已放弃未保存更改', 'info')
  }, [notify])

  const saveAll = async () => {
    const changed = rows.filter(r => pending.has(r.id))
    if (changed.length === 0) { notify('没有需要保存的更改', 'warning'); return }

    setLoading(true)
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
        notify(`保存失败：${errMsg}`, 'danger')
        return
      }
      notify(`已保存 ${changed.length} 条记录`, 'success')
      fetchCodes()
    } catch {
      notify('请求失败', 'danger')
    }
    finally { setLoading(false) }
  }

  const [deleteTarget, setDeleteTarget] = useState(null)

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    // new row: local remove only
    if (deleteTarget.isNew) {
      setRows(prev => prev.filter(r => r.id !== deleteTarget.id))
      setPending(prev => {
        const next = new Set(prev)
        next.delete(deleteTarget.id)
        return next
      })
      setAddRowVisible(false)
      setDeleteTarget(null)
      notify('已移除未保存的记录', 'info')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/split-codes/${encodeURIComponent(deleteTarget.id)}`, { method: 'DELETE' })
      if (!res.ok) {
        notify('删除失败', 'danger')
        return
      }
      notify('已删除', 'success')
      fetchCodes()
    } catch { notify('请求失败', 'danger') }
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

  const pendingCount = pending.size
  const deleteTitle = deleteTarget?.isNew ? '确认移除' : '确认删除'
  const deleteBody = useMemo(() => {
    if (!deleteTarget) return null
    const codeText = (deleteTarget.code || '').trim()
    const label = codeText ? `编码「${codeText}」` : '该记录'
    return deleteTarget.isNew
      ? `确定要移除未保存的${label}吗？此操作不会影响已保存的数据。`
      : `确定要删除${label}吗？此操作不可撤销。`
  }, [deleteTarget])

  return (
    <div className="split-manager">
      <ToastViewport toasts={toasts} onClose={dismissToast} />

      <header className="sm-header">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => (pendingCount > 0 ? setBackConfirmOpen(true) : onBack())}
          type="button"
        >
          <IconBack /> 返回转换
        </Button>
        <div className="sm-header__title">
          <h2>商品拆零管理</h2>
        </div>
        <Badge variant="info" className="sm-header__badge">{rows.length} 条记录</Badge>
      </header>

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
        <div className="sm-toolbar__controls">
          <select
            className="sm-select"
            value={splitFilter}
            onChange={e => { setSplitFilter(e.target.value); setPage(1) }}
            aria-label="拆零筛选"
          >
            <option value="全部">全部规则</option>
            <option value="拆零">拆零</option>
            <option value="不拆零">不拆零</option>
          </select>
          <div className="sm-pagesize">
            <span className="sm-pagesize__label">每页</span>
            <select
              className="sm-select"
              value={pageSize}
              onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
              aria-label="每页条数"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
            <span className="sm-pagesize__label">条</span>
          </div>
        </div>
        <div className="sm-toolbar__actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={addNewRow}
            type="button"
            disabled={addRowVisible}
          >
            <IconPlus /> 新增
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={saveAll}
            type="button"
            loading={loading}
            disabled={pendingCount === 0}
          >
            保存{pendingCount > 0 ? ` (${pendingCount})` : ''}
          </Button>
        </div>
      </section>

      <section className="sm-table-card">
        {filtered.length === 0 ? (
          <div className="sm-empty">{search || splitFilter !== '全部' ? '未找到匹配的编码' : '暂无数据，请点击 "+ 新增" 添加'}</div>
        ) : (
          <>
            <div className="sm-table-scroll" role="region" aria-label="拆零规则表格（可横向滚动）" tabIndex={0}>
              <table className="sm-table">
                <thead>
                  <tr><th>商品编码</th><th>拆零规则</th><th>创建时间</th><th>操作</th></tr>
                </thead>
                <tbody>
                  {paginatedItems.map(r => {
                    const isNew = r.isNew
                    const displayCode = r.code || ''
                    const isDirty = pending.has(r.id)
                    return (
                      <tr key={r.id} className={[
                        isNew ? 'sm-row--new' : '',
                        isDirty ? 'sm-row--dirty' : '',
                      ].filter(Boolean).join(' ')}>
                        <td className="sm-code">
                          <div className="sm-code__wrap">
                            {isDirty && <span className="sm-dirty-dot" title="未保存更改" aria-label="未保存更改" />}
                            <input
                              ref={isNew ? newInputRef : null}
                              className="sm-code__input"
                              value={displayCode}
                              onChange={e => updateCell(r.id, 'code', e.target.value)}
                              placeholder="输入商品编码"
                              onKeyDown={e => e.key === 'Enter' && saveAll()}
                            />
                          </div>
                        </td>
                        <td>
                          <SplitToggle value={r.split} onChange={val => updateCell(r.id, 'split', val)} />
                        </td>
                        <td className="sm-time">{r.created_at ? formatDateTime(r.created_at) : '—'}</td>
                        <td className="sm-cell-actions">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="sm-icon-btn sm-icon-btn--danger"
                            onClick={() => setDeleteTarget(r)}
                            type="button"
                            aria-label="删除"
                            title="删除"
                          >
                            <IconTrash />
                            <span className="ui-sr-only">删除</span>
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="sm-pagination">
              <div className="sm-pagination__info">
                显示 <strong>{startIndex + 1}-{Math.min(endIndex, filtered.length)}</strong> 条，共 <strong>{filtered.length}</strong> 条
              </div>
              <div className="sm-pagination__group">
                <div className="sm-pagination__nav">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="sm-page-btn"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}
                    type="button"
                  >
                    <IconLeft />
                    <span className="ui-sr-only">上一页</span>
                  </Button>
                  <span className="sm-pagination__page-text">
                    {currentPage} / {totalPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="sm-page-btn"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage >= totalPages}
                    type="button"
                  >
                    <IconRight />
                    <span className="ui-sr-only">下一页</span>
                  </Button>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      {pendingCount > 0 && (
        <div className="sm-dirtybar" role="status" aria-live="polite">
          <div className="sm-dirtybar__left">
            <span className="sm-dirtybar__dot" aria-hidden="true" />
            待保存 <strong>{pendingCount}</strong> 条
          </div>
          <div className="sm-dirtybar__actions">
            <Button variant="secondary" size="sm" type="button" onClick={discardChanges} disabled={loading}>
              放弃更改
            </Button>
            <Button variant="primary" size="sm" type="button" onClick={saveAll} loading={loading}>
              保存更改
            </Button>
          </div>
        </div>
      )}

      <Modal
        open={backConfirmOpen}
        onClose={() => !loading && setBackConfirmOpen(false)}
        title="确认返回"
        closeLabel="关闭"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setBackConfirmOpen(false)} disabled={loading}>
              取消
            </Button>
            <Button
              variant="danger"
              type="button"
              onClick={() => { setBackConfirmOpen(false); onBack() }}
              disabled={loading}
            >
              返回转换
            </Button>
          </>
        )}
      >
        <div className="sm-modal__content">
          <p className="sm-modal__message">
            当前有 <strong>{pendingCount}</strong> 条未保存更改，返回后将丢失这些更改。是否继续？
          </p>
        </div>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => !loading && setDeleteTarget(null)}
        title={deleteTitle}
        closeLabel="关闭"
        footer={(
          <>
            <Button variant="secondary" type="button" onClick={() => setDeleteTarget(null)} disabled={loading}>
              取消
            </Button>
            <Button
              variant={deleteTarget?.isNew ? 'danger' : 'danger'}
              type="button"
              onClick={handleConfirmDelete}
              loading={loading}
            >
              {deleteTarget?.isNew ? '移除' : '删除'}
            </Button>
          </>
        )}
      >
        <div className="sm-modal__content">
          <p className="sm-modal__message">{deleteBody}</p>
        </div>
      </Modal>
    </div>
  )
}
