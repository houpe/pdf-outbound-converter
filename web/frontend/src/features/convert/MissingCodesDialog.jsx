import { useState } from 'react'
import SplitToggle from '../../SplitToggle'
import { apiClient } from '../../lib/apiClient'

export default function MissingCodesDialog({ codes = [], onClose, onRetry }) {
  const [items, setItems] = useState(() =>
    codes.map(c => ({ code: c.code, split: '是', source: c.source }))
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const updateItem = (index, field, value) => {
    setItems(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  const handleSave = async () => {
    if (loading) return
    setError('')
    setLoading(true)
    try {
      await apiClient.patch('/split-codes/batch',
        items.map(i => ({ id: '', code: i.code, split: i.split })),
        { headers: { 'Content-Type': 'application/json' } }
      )
      setLoading(false)
      onClose()
      if (onRetry) onRetry()
    } catch (e) {
      setError(e?.message || '保存失败，请稍后重试')
      setLoading(false)
    }
  }

  const handleDialogClose = () => {
    if (loading) return
    onClose?.()
  }

  return (
    <div className="missing-overlay" onClick={handleDialogClose}>
      <div className="missing-dialog" onClick={e => e.stopPropagation()}>
        <div className="missing-dialog__header">
          <h3>⚠️ 需配置拆零规则</h3>
          <button className="missing-dialog__close" onClick={handleDialogClose} disabled={loading} type="button">✕</button>
        </div>
        <div className="missing-dialog__body">
          <p className="missing-dialog__desc">以下 {items.length} 个商品编码未配置，请设置拆零规则：</p>
          <div className="missing-dialog__codes missing-dialog__codes--scroll">
            {items.map((item, i) => (
              <div key={i} className="missing-dialog__code-row">
                <div>
                  <code className="missing-dialog__code">{item.code}</code>
                  <div className="missing-dialog__source">来自 {item.source}</div>
                </div>
                <SplitToggle value={item.split} onChange={val => (!loading ? updateItem(i, 'split', val) : null)} />
              </div>
            ))}
          </div>
          {error ? <div className="missing-dialog__error" role="alert">{error}</div> : null}
        </div>
        <div className="missing-dialog__footer">
          <button className="missing-dialog__btn missing-dialog__btn--primary" onClick={handleSave} disabled={loading} type="button">
            {loading ? '保存中...' : '保存并重试'}
          </button>
          <button className="missing-dialog__btn" onClick={handleDialogClose} disabled={loading} type="button">取消</button>
        </div>
      </div>
    </div>
  )
}
