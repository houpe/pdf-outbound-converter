import { useState, useEffect, useCallback } from 'react'
import './AdminPage.css'
import { IconBack, IconPlus, IconTrash } from './Icons'
import { apiClient } from './lib/apiClient'
import AIRuleModal from './features/AIRuleModal'

const EMPTY_WH = { code: '', name: '', url_path: '' }
const EMPTY_TMPL = { key: '', name: '', accept: '.xlsx,.xls', merchant_code: '', warehouse_code: '' }

// 安全解析 parse_rule JSON：解析失败不崩溃，打日志便于诊断
function safeParseRule(s, key) {
  if (!s) return null
  try {
    const parsed = JSON.parse(s)
    if (parsed && typeof parsed === 'object' && Object.keys(parsed).length === 0) {
      console.warn(`[safeParseRule] 模板 ${key} 的 parse_rule 是空对象 {}`)
      return null
    }
    return parsed
  } catch (e) {
    console.error(`[safeParseRule] 模板 ${key} 的 parse_rule 解析失败:`, e, '\n原始值:', s)
    return null
  }
}

export default function AdminPage({ onBack }) {
  const [warehouses, setWarehouses] = useState([])
  const [templates, setTemplates] = useState([])
  const [groups, setGroups] = useState({})
  const [whForm, setWhForm] = useState(EMPTY_WH)
  const [tmplForm, setTmplForm] = useState(EMPTY_TMPL)
  const [editingWh, setEditingWh] = useState(null)
  const [editingTmpl, setEditingTmpl] = useState(null)
  const [error, setError] = useState('')
  const [addingTemplateTo, setAddingTemplateTo] = useState(null)
  const [aiRuleModal, setAiRuleModal] = useState(null)
  const [confirmDialog, setConfirmDialog] = useState(null)

  const loadData = useCallback(async () => {
    try {
      const [whRes, tmplRes, grpRes] = await Promise.all([
        apiClient.get('/admin/warehouses'),
        apiClient.get('/admin/templates'),
        apiClient.get('/admin/warehouse-templates'),
      ])
      setWarehouses(whRes.data.warehouses || [])
      setTemplates(tmplRes.data.templates || [])
      setGroups(grpRes.data.groups || {})
    } catch {
      setError('加载管理数据失败')
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleAddWarehouse = async () => {
    if (!whForm.code.trim() || !whForm.name.trim()) { setError('仓库编码和名称不能为空'); return }
    try {
      await apiClient.post('/admin/warehouses', whForm)
      setWhForm(EMPTY_WH)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '添加失败') }
  }

  const handleUpdateWarehouse = async (code) => {
    try {
      await apiClient.put(`/admin/warehouses/${code}`, { name: editingWh.name, url_path: editingWh.url_path })
      setEditingWh(null)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '更新失败') }
  }

  const handleDeleteWarehouse = async (code) => {
    showConfirm(`确定删除仓库 ${code}？`, '关联的模板绑定也会一并删除。', () => doDeleteWarehouse(code))
  }
  const doDeleteWarehouse = async (code) => {
    try {
      await apiClient.delete(`/admin/warehouses/${code}`)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '删除失败') }
  }

  const handleAddTemplate = async () => {
    if (!tmplForm.key.trim() || !tmplForm.name.trim()) { setError('模板键和名称不能为空'); return }
    if (!tmplForm.warehouse_code) { setError('请选择关联仓库'); return }
    try {
      await apiClient.post('/admin/templates', tmplForm)
      setTmplForm(EMPTY_TMPL)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '添加失败') }
  }

  const handleUpdateTemplate = async (key) => {
    try {
      await apiClient.put(`/admin/templates/${key}`, { name: editingTmpl.name, accept: editingTmpl.accept, merchant_code: editingTmpl.merchant_code, warehouse_code: editingTmpl.warehouse_code || '' })
      setEditingTmpl(null)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '更新失败') }
  }

  const handleDeleteTemplate = async (key) => {
    showConfirm(`确定删除模板 ${key}？`, '所有仓库关联也会一并解除。', () => doDeleteTemplate(key))
  }
  const doDeleteTemplate = async (key) => {
    try {
      await apiClient.delete(`/admin/templates/${key}`)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '删除失败') }
  }

  const handleRemoveTemplateFromWh = async (whCode, tmplKey) => {
    const current = groups[whCode]?.templates || []
    const next = current.filter(k => k !== tmplKey)
    try {
      await apiClient.put(`/admin/warehouse-templates/${whCode}`, { template_keys: next })
      setError('')
      loadData()
    } catch (e) { setError(e.message || '操作失败') }
  }

  const handleAddTemplateToWh = async (whCode, tmplKey) => {
    const current = groups[whCode]?.templates || []
    if (current.includes(tmplKey)) { setAddingTemplateTo(null); return }
    const next = [...current, tmplKey]
    try {
      await apiClient.put(`/admin/warehouse-templates/${whCode}`, { template_keys: next })
      setAddingTemplateTo(null)
      setError('')
      loadData()
    } catch (e) { setError(e.message || '操作失败') }
  }

  const unassignedTemplates = (whCode) => {
    const assigned = new Set(groups[whCode]?.templates || [])
    return templates.filter(t => !assigned.has(t.key))
  }

  const showConfirm = (title, message, onConfirm) => {
    setConfirmDialog({ title, message, onConfirm })
  }
  const closeConfirm = () => setConfirmDialog(null)
  const handleConfirmOk = () => {
    const cb = confirmDialog?.onConfirm
    setConfirmDialog(null)
    cb && cb()
  }

  return (
    <div className="admin-root">
      <div className="admin-header">
        <button className="admin-back-btn" onClick={onBack} type="button">
          <IconBack /> 返回
        </button>
        <h1>仓库与模板管理</h1>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: 'var(--color-danger)', color: '#fff', borderRadius: 'var(--radius-sm)', fontSize: 13, marginBottom: 'var(--space-3)' }}>
          {error}
          <button onClick={() => setError('')} style={{ marginLeft: 8, background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 700 }}>✕</button>
        </div>
      )}

      <section className="admin-section">
        <div className="admin-section__header">
          <h2 className="admin-section__title">仓库管理</h2>
          <span className="admin-section__count">{warehouses.length} 个仓库</span>
        </div>

        <table className="admin-table">
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>访问路径</th>
              <th>关联模板</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {warehouses.length === 0 && (
              <tr><td colSpan={5} className="admin-empty">暂无仓库，请添加</td></tr>
            )}
            {warehouses.map(wh => (
              <tr key={wh.code}>
                <td className="admin-table__mono">{wh.code}</td>
                <td>
                  {editingWh?.code === wh.code ? (
                    <input value={editingWh.name} onChange={e => setEditingWh({ ...editingWh, name: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)', width: '100%' }} />
                  ) : wh.name}
                </td>
                <td>
                  {editingWh?.code === wh.code ? (
                    <input value={editingWh.url_path} onChange={e => setEditingWh({ ...editingWh, url_path: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)', width: '100%' }} />
                  ) : (
                    <span className="admin-table__mono">{wh.url_path || `/wms/${wh.code}/`}</span>
                  )}
                </td>
                <td>
                  <div className="admin-tag-list">
                    {(groups[wh.code]?.templates || []).map(tk => {
                      const tmpl = templates.find(t => t.key === tk)
                      return (
                        <span key={tk} className="admin-tag admin-tag--active">
                          {tmpl?.name || tk}
                          <button className="admin-tag-remove" onClick={() => handleRemoveTemplateFromWh(wh.code, tk)} type="button">×</button>
                        </span>
                      )
                    })}
                    {addingTemplateTo === wh.code ? (
                      <select
                        className="admin-select-inline"
                        autoFocus
                        onChange={e => { if (e.target.value) handleAddTemplateToWh(wh.code, e.target.value) }}
                        onBlur={() => setAddingTemplateTo(null)}
                        defaultValue=""
                      >
                        <option value="" disabled>+ 选择模板</option>
                        {unassignedTemplates(wh.code).map(t => (
                          <option key={t.key} value={t.key}>{t.name} ({t.key})</option>
                        ))}
                      </select>
                    ) : (
                      templates.length > (groups[wh.code]?.templates || []).length && (
                        <button className="admin-tag" onClick={() => setAddingTemplateTo(wh.code)} type="button" style={{ cursor: 'pointer', color: 'var(--color-primary)' }}>+ 添加</button>
                      )
                    )}
                  </div>
                </td>
                <td>
                  <div className="admin-table__actions">
                    {editingWh?.code === wh.code ? (
                      <>
                        <button className="admin-link-btn" onClick={() => handleUpdateWarehouse(wh.code)} type="button">保存</button>
                        <button className="admin-link-btn" onClick={() => setEditingWh(null)} type="button" style={{ color: 'var(--color-text-muted)' }}>取消</button>
                      </>
                    ) : (
                      <>
                        <button className="admin-link-btn" onClick={() => setEditingWh({ code: wh.code, name: wh.name, url_path: wh.url_path || `/wms/${wh.code}/` })} type="button">编辑</button>
                        <button className="admin-link-btn" onClick={() => handleDeleteWarehouse(wh.code)} type="button" style={{ color: 'var(--color-danger)' }}>删除</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="admin-form-row">
          <label>
            编码
            <input placeholder="如 ZTOWHXX001" value={whForm.code} onChange={e => setWhForm({ ...whForm, code: e.target.value })} />
          </label>
          <label>
            名称
            <input placeholder="如 北京朝阳仓" value={whForm.name} onChange={e => setWhForm({ ...whForm, name: e.target.value })} />
          </label>
          <label>
            访问路径
            <input placeholder="/wms/ZTOWHXX001/" value={whForm.url_path} onChange={e => setWhForm({ ...whForm, url_path: e.target.value })} className="admin-form-row__input--short" />
          </label>
          <button className="ui-btn ui-btn--primary ui-btn--sm" onClick={handleAddWarehouse} type="button"><IconPlus /> 添加仓库</button>
        </div>
      </section>

      <section className="admin-section">
        <div className="admin-section__header">
          <h2 className="admin-section__title">模板管理</h2>
          <span className="admin-section__count">{templates.length} 个模板</span>
        </div>

        <table className="admin-table">
          <thead>
            <tr>
              <th>键</th>
              <th>名称</th>
              <th>文件类型</th>
              <th>商户编码</th>
              <th>绑定仓库</th>
              <th>规则</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {templates.length === 0 && (
              <tr><td colSpan={7} className="admin-empty">暂无模板，请添加</td></tr>
            )}
            {templates.map(t => {
              return (
                <tr key={t.key}>
                  <td className="admin-table__mono">{t.key}</td>
                  <td>
                    {editingTmpl?.key === t.key ? (
                      <input value={editingTmpl.name} onChange={e => setEditingTmpl({ ...editingTmpl, name: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)', width: '100%' }} />
                    ) : t.name}
                  </td>
                  <td>
                    {editingTmpl?.key === t.key ? (
                      <input value={editingTmpl.accept} onChange={e => setEditingTmpl({ ...editingTmpl, accept: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)', width: 100 }} />
                    ) : (
                      <span className="admin-table__mono">{t.accept}</span>
                    )}
                  </td>
                  <td>
                    {editingTmpl?.key === t.key ? (
                      <input value={editingTmpl.merchant_code} onChange={e => setEditingTmpl({ ...editingTmpl, merchant_code: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)', width: 140 }} />
                    ) : (
                      <span className="admin-table__mono">{t.merchant_code}</span>
                    )}
                  </td>
                  <td>
                    {editingTmpl?.key === t.key ? (
                      <select value={editingTmpl.warehouse_code || ''} onChange={e => setEditingTmpl({ ...editingTmpl, warehouse_code: e.target.value })} style={{ padding: '4px 8px', fontSize: 13, border: '1px solid var(--color-border-strong)', borderRadius: 'var(--radius-xs)' }}>
                        <option value="" disabled>选择仓库</option>
                        {warehouses.map(w => <option key={w.code} value={w.code}>{w.name} ({w.code})</option>)}
                      </select>
                    ) : (
                      <span className="admin-table__mono">{t.warehouse_code || <span style={{ color: 'var(--color-danger)' }}>未绑定</span>}</span>
                    )}
                  </td>
                  <td>
                    {t.parse_rule ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="admin-tag admin-tag--active">{t.rule_source === 'ai' ? 'AI规则' : '手动规则'}</span>
                        <button
                          className="admin-link-btn"
                          onClick={() => setAiRuleModal({ key: t.key, name: t.name, rule: safeParseRule(t.parse_rule, t.key) })}
                          type="button"
                        >
                          AI编辑规则
                        </button>
                      </div>
                    ) : (
                      <button className="admin-link-btn" onClick={() => setAiRuleModal({ key: t.key, name: t.name, rule: null })} type="button">AI生成</button>
                    )}
                  </td>
                  <td>
                    <div className="admin-table__actions">
                      {editingTmpl?.key === t.key ? (
                        <>
                          <button className="admin-link-btn" onClick={() => handleUpdateTemplate(t.key)} type="button">保存</button>
                          <button className="admin-link-btn" onClick={() => setEditingTmpl(null)} type="button" style={{ color: 'var(--color-text-muted)' }}>取消</button>
                        </>
                      ) : (
                        <>
                          <button className="admin-link-btn" onClick={() => setEditingTmpl({ key: t.key, name: t.name, accept: t.accept, merchant_code: t.merchant_code, warehouse_code: t.warehouse_code || '' })} type="button">编辑</button>
                          <button className="admin-link-btn" onClick={() => handleDeleteTemplate(t.key)} type="button" style={{ color: 'var(--color-danger)' }}>删除</button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        <div className="admin-form-row">
          <label>
            键
            <input placeholder="如 abc" value={tmplForm.key} onChange={e => setTmplForm({ ...tmplForm, key: e.target.value })} />
          </label>
          <label>
            名称
            <input placeholder="如 新商户模板" value={tmplForm.name} onChange={e => setTmplForm({ ...tmplForm, name: e.target.value })} />
          </label>
          <label>
            文件类型
            <input placeholder=".xlsx,.xls" value={tmplForm.accept} onChange={e => setTmplForm({ ...tmplForm, accept: e.target.value })} className="admin-form-row__input--short" />
          </label>
          <label>
            商户编码
            <input placeholder="Q2026xxxxxxx" value={tmplForm.merchant_code} onChange={e => setTmplForm({ ...tmplForm, merchant_code: e.target.value })} />
          </label>
          <label>
            绑定仓库
            <select value={tmplForm.warehouse_code} onChange={e => setTmplForm({ ...tmplForm, warehouse_code: e.target.value })}>
              <option value="" disabled>选择仓库</option>
              {warehouses.map(w => <option key={w.code} value={w.code}>{w.name}</option>)}
            </select>
          </label>
          <button className="ui-btn ui-btn--primary ui-btn--sm" onClick={handleAddTemplate} type="button"><IconPlus /> 添加模板</button>
        </div>
      </section>

      {confirmDialog && (
        <div className="ui-modal__overlay" onClick={closeConfirm}>
          <div className="ui-modal" style={{ width: 'min(400px, 92vw)' }} onClick={e => e.stopPropagation()}>
            <div className="ui-modal__header">
              <h3 className="ui-modal__title">{confirmDialog.title}</h3>
            </div>
            <div className="ui-modal__body">
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', margin: 0 }}>{confirmDialog.message}</p>
            </div>
            <div className="ui-modal__footer" style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', padding: '12px 16px', borderTop: '1px solid var(--color-border-light, #f0f0f0)' }}>
              <button className="ui-btn ui-btn--secondary ui-btn--sm" onClick={closeConfirm} type="button">取消</button>
              <button className="ui-btn ui-btn--danger ui-btn--sm" onClick={handleConfirmOk} type="button">确认删除</button>
            </div>
          </div>
        </div>
      )}

      {aiRuleModal && (
        <AIRuleModal
          templateKey={aiRuleModal.key}
          templateName={aiRuleModal.name}
          initialRule={aiRuleModal.rule}
          onClose={() => setAiRuleModal(null)}
          onSave={loadData}
          onError={setError}
        />
      )}
    </div>
  )
}
