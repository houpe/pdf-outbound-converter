import { useState } from 'react'
import { apiClient } from '../lib/apiClient'

const MODE_LABELS = {
  table: '标准表格',
  matrix_transpose: '矩阵转置',
  card_split: '卡片拆分',
  text_parse: '纯文本解析',
  multi_sheet: '多Sheet合并',
}

function summarizeRule(rule) {
  if (!rule) return null
  const fm = rule.fieldMappings || {}
  const mappings = Object.entries(fm).map(([field, mapping]) => {
    let desc = ''
    switch (mapping.source) {
      case 'header_column':
        desc = `表头"${mapping.headerName || '?'}"`
        break
      case 'col_index':
        desc = `第${(mapping.col ?? 0) + 1}列`
        break
      case 'cell_position':
        desc = `行${mapping.row + 1}列${(mapping.col ?? 0) + 1}`
        break
      case 'regex':
        desc = `正则: ${(mapping.regex || '').slice(0, 20)}${mapping.regex?.length > 20 ? '...' : ''}`
        break
      case 'static':
        desc = `固定值"${mapping.staticValue || mapping.value || ''}"`
        break
      case 'transpose':
        desc = '转置取值'
        break
      default:
        desc = mapping.source
    }
    return { field, desc }
  })
  return {
    mode: MODE_LABELS[rule.mode] || rule.mode,
    headerRow: rule.headerRow ?? '?',
    dataStartRow: rule.dataStartRow ?? '?',
    dataEndPattern: rule.dataEndPattern || '(未设置)',
    mappings,
    skipCount: (rule.skipPatterns || []).length,
    hasTailRegion: !!rule.tailRegion,
  }
}

export default function AIRuleModal({
  templateKey,
  templateName,
  initialRule = null,
  fileAnalysis = '',
  onClose,
  onSave,
  onError,
}) {
  const [file, setFile] = useState(null)
  const [rule, setRule] = useState(initialRule)
  const [showRawJson, setShowRawJson] = useState(false)
  const [analysis, setAnalysis] = useState(fileAnalysis)
  const [feedback, setFeedback] = useState('')
  const [previewData, setPreviewData] = useState(null)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')

  const clearError = () => setError('')

  const handleGenerate = async () => {
    if (!file) { setError('请先选择样例文件'); return }
    setLoading('ai')
    clearError()
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('template_key', templateKey)
      const res = await apiClient.post('/admin/ai/generate-rule', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      const data = res.data
      setRule(data.rule)
      setAnalysis(data.reasoning || data.file_analysis || '')
      setPreviewData(null)
    } catch (e) {
      setError(e.message || 'AI生成失败')
    }
    setLoading('')
  }

  const handleRefine = async () => {
    if (!feedback.trim()) { setError('请输入修改要求'); return }
    if (!rule) { setError('请先生成规则'); return }
    setLoading('refine')
    clearError()
    try {
      const fd = new FormData()
      fd.append('rule_json', JSON.stringify(rule))
      fd.append('feedback', feedback)
      if (file) fd.append('file', file)
      const res = await apiClient.post('/admin/ai/refine-rule', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      const data = res.data
      setRule(data.rule)
      setFeedback('')
      if (data.reasoning) {
        setAnalysis(prev => prev ? prev + '\n\n---\n' + data.reasoning : data.reasoning)
      }
      setPreviewData(null)
    } catch (e) {
      setError(e.message || 'AI修改失败')
    }
    setLoading('')
  }

  const handlePreview = async () => {
    if (!file) { setError('请先选择文件进行预览'); return }
    if (!rule) { setError('请先生成规则'); return }
    setLoading('preview')
    clearError()
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('rule_json', JSON.stringify(rule))
      fd.append('template_key', templateKey)
      const res = await apiClient.post('/admin/ai/preview-parse', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      })
      setPreviewData(res.data)
    } catch (e) {
      setError(e.message || '预览失败')
    }
    setLoading('')
  }

  const handleSave = async () => {
    if (!rule) return
    setLoading('save')
    clearError()
    try {
      await apiClient.put(`/admin/templates/${templateKey}/rule`, {
        rule,
        rule_source: 'ai',
      })
      onSave && onSave()
      onClose && onClose()
    } catch (e) {
      setError(e.message || '保存失败')
    }
    setLoading('')
  }

  const handleUpdateRuleJson = (text) => {
    try {
      const parsed = JSON.parse(text)
      setRule(parsed)
    } catch {
    }
  }

  const summary = summarizeRule(rule)

  return (
    <div className="ui-modal__overlay" onClick={onClose}>
      <div className="ui-modal" style={{ width: 'min(900px, 100%)', maxHeight: '95vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
        <div className="ui-modal__header">
          <h3 className="ui-modal__title">{templateName} — AI解析规则</h3>
          <button className="ui-modal__close" onClick={onClose} type="button">✕</button>
        </div>

        <div className="ui-modal__body" style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {error && (
            <div style={{ padding: '8px 12px', background: 'var(--color-danger)', color: '#fff', borderRadius: 'var(--radius-sm)', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{error}</span>
              <button onClick={clearError} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 700 }}>✕</button>
            </div>
          )}

          {!rule && (
            <div>
              <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 12 }}>
                上传一个样例文件，AI将自动分析文件结构并生成解析规则。
              </p>
              <input
                type="file"
                accept=".xlsx,.xls,.pdf,.docx,.doc"
                onChange={e => setFile(e.target.files?.[0] || null)}
                style={{ marginBottom: 12, fontSize: 14 }}
              />
              <button
                className="ui-btn ui-btn--primary ui-btn--sm"
                disabled={loading === 'ai' || !file}
                onClick={handleGenerate}
                type="button"
              >
                {loading === 'ai' ? 'AI分析中...' : '生成规则'}
              </button>
            </div>
          )}

          {rule && (
            <>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)' }}>当前规则：</span>
                <span className="admin-tag admin-tag--active" style={{ background: 'var(--color-primary)', color: '#fff' }}>{summary?.mode}</span>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                  表头行 {summary?.headerRow} | 数据起始 {summary?.dataStartRow} | {summary?.mappings?.length || 0}个字段映射
                </span>
                {summary?.hasTailRegion && <span className="admin-tag">有尾部信息区</span>}
              </div>

              {analysis && (
                <details style={{ background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-sm)', padding: 12 }}>
                  <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 600, color: 'var(--color-text-secondary)' }}>AI分析说明</summary>
                  <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 8, color: 'var(--color-text-secondary)' }}>{analysis}</pre>
                </details>
              )}

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)' }}>字段映射</span>
                  <button
                    onClick={() => setShowRawJson(v => !v)}
                    style={{ fontSize: 11, color: 'var(--color-primary)', background: 'none', border: 'none', cursor: 'pointer' }}
                    type="button"
                  >
                    {showRawJson ? '关闭原始JSON' : '编辑原始JSON'}
                  </button>
                </div>

                {showRawJson ? (
                  <textarea
                    value={JSON.stringify(rule, null, 2)}
                    onChange={e => handleUpdateRuleJson(e.target.value)}
                    style={{
                      width: '100%',
                      height: 280,
                      fontFamily: 'monospace',
                      fontSize: 11,
                      padding: 10,
                      border: '1px solid var(--color-border-strong)',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--color-surface-muted)',
                      resize: 'vertical',
                    }}
                  />
                ) : (
                  <div style={{ background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-sm)', padding: 12, maxHeight: 200, overflow: 'auto' }}>
                    <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--color-text-muted)' }}>目标字段</th>
                          <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--color-text-muted)' }}>映射方式</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary?.mappings?.map((m, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--color-border-light, #f0f0f0)' }}>
                            <td style={{ padding: '4px 8px', fontWeight: 500 }}>{m.field}</td>
                            <td style={{ padding: '4px 8px', color: 'var(--color-text-secondary)' }}>{m.desc}</td>
                          </tr>
                        ))}
                        {!summary?.mappings?.length && (
                          <tr><td colSpan={2} style={{ padding: '8px', textAlign: 'center', color: 'var(--color-text-muted)' }}>无字段映射</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {previewData && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)' }}>
                      OMS 出库格式预览（{previewData.total || 0}条 · 与最终导出 Excel 完全一致）
                    </span>
                    {(previewData.merchant_code || previewData.warehouse_code) && (
                      <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>
                        货主: {previewData.merchant_code || '-'} | 仓库: {previewData.warehouse_code || '-'}
                      </span>
                    )}
                    {previewData.errors?.length > 0 && (
                      <span style={{ fontSize: 11, color: 'var(--color-danger)' }}>
                        {previewData.errors.length}个错误
                      </span>
                    )}
                  </div>
                  {previewData.errors?.length > 0 && (
                    <div style={{ background: '#fff1f0', border: '1px solid #ffccc7', borderRadius: 'var(--radius-sm)', padding: 8, fontSize: 12, marginBottom: 8 }}>
                      {previewData.errors.map((e, i) => <div key={i}>• {e}</div>)}
                    </div>
                  )}
                  <div style={{ overflowX: 'auto', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)' }}>
                    <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', minWidth: 880 }}>
                      <thead>
                        <tr style={{ position: 'sticky', top: 0, background: 'var(--color-surface)' }}>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>A 商家单号</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>B 货主编码</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>C 仓库编码</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>E 收件人信息</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>F 门店名称</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>G 备注</th>
                          <th style={{ padding: '4px 6px', textAlign: 'left', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>H 商品编码</th>
                          <th style={{ padding: '4px 6px', textAlign: 'right', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>I 二级单位数量</th>
                          <th style={{ padding: '4px 6px', textAlign: 'right', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>J 最小单位数量</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.data?.slice(0, 50).map((row, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--color-border-light, #f5f5f5)' }}>
                            <td style={{ padding: '4px 6px', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 10 }}>{row.A_order_no || '-'}</td>
                            <td style={{ padding: '4px 6px', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 10 }}>{row.B_merchant_code || '-'}</td>
                            <td style={{ padding: '4px 6px', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 10 }}>{row.C_warehouse_code || '-'}</td>
                            <td style={{ padding: '4px 6px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.E_receiver || '-'}</td>
                            <td style={{ padding: '4px 6px', whiteSpace: 'nowrap' }}>{row.F_store || '-'}</td>
                            <td style={{ padding: '4px 6px', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.G_item_name || '-'}</td>
                            <td style={{ padding: '4px 6px', fontFamily: 'monospace', fontSize: 10 }}>{row.H_item_code || '-'}</td>
                            <td style={{ padding: '4px 6px', textAlign: 'right', fontFamily: 'monospace' }}>{row.I_secondary_qty ?? ''}</td>
                            <td style={{ padding: '4px 6px', textAlign: 'right', fontFamily: 'monospace' }}>{row.J_min_unit_qty ?? ''}</td>
                          </tr>
                        ))}
                        {!previewData.data?.length && (
                          <tr><td colSpan={9} style={{ padding: '12px', textAlign: 'center', color: 'var(--color-text-muted)' }}>未解析到数据</td></tr>
                        )}
                      </tbody>
                    </table>
                    {previewData.data?.length > 50 && (
                      <div style={{ padding: 6, fontSize: 11, textAlign: 'center', color: 'var(--color-text-muted)' }}>
                        显示前50条，共{previewData.data.length}条
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', display: 'block', marginBottom: 6 }}>
                  用自然语言修改规则（如："商品编码在第4列"、"需要跳过第1-2行"）
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <textarea
                    value={feedback}
                    onChange={e => setFeedback(e.target.value)}
                    placeholder="例如：收货人电话在文件末尾的文本中；商品编码列名叫SKU；..."
                    style={{
                      flex: 1,
                      minHeight: 60,
                      padding: 10,
                      border: '1px solid var(--color-border-strong)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 13,
                      resize: 'vertical',
                    }}
                  />
                  <button
                    className="ui-btn ui-btn--secondary ui-btn--sm"
                    disabled={loading === 'refine' || !feedback.trim()}
                    onClick={handleRefine}
                    type="button"
                    style={{ alignSelf: 'flex-end' }}
                  >
                    {loading === 'refine' ? 'AI修改中...' : 'AI修改'}
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', paddingTop: 8, borderTop: '1px solid var(--color-border-light, #f0f0f0)' }}>
                {file && (
                  <>
                    <button
                      className="ui-btn ui-btn--secondary ui-btn--sm"
                      disabled={loading === 'preview'}
                      onClick={handlePreview}
                      type="button"
                    >
                      {loading === 'preview' ? '预览中...' : '预览解析效果'}
                    </button>
                    <span style={{ fontSize: 12, color: 'var(--color-text-muted)', alignSelf: 'center' }}>
                      使用文件: {file.name}
                    </span>
                  </>
                )}
                {!file && (
                  <input
                    type="file"
                    accept=".xlsx,.xls,.pdf,.docx,.doc"
                    onChange={e => setFile(e.target.files?.[0] || null)}
                    style={{ fontSize: 12, alignSelf: 'center' }}
                  />
                )}
                <div style={{ flex: 1 }} />
                <button
                  className="ui-btn ui-btn--secondary ui-btn--sm"
                  onClick={onClose}
                  type="button"
                >
                  取消
                </button>
                <button
                  className="ui-btn ui-btn--primary ui-btn--sm"
                  disabled={loading === 'save'}
                  onClick={handleSave}
                  type="button"
                >
                  {loading === 'save' ? '保存中...' : '保存规则'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
