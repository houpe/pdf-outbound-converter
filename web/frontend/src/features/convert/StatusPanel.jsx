import { IconCheck, IconDownload } from '../../Icons'
import { DOWNLOAD_BASE } from '../../lib/apiClient'

function EmptyState() {
  return (
      <div className="convert-empty-state">
        <div className="convert-empty-state__icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" opacity="0.3" />
            <circle cx="24" cy="24" r="12" stroke="currentColor" strokeWidth="1.5" />
            <path d="M24 18v6l4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="convert-empty-state__text">暂无转换数据</p>
        <span className="convert-empty-state__hint">上传文件并开始转换后<br />处理状态与结果将在此展示</span>
      </div>
  )
}

function ProgressBlock({ progress }) {
  if (!progress) return null

  const width =
    progress.status === 'done' ? '100%' :
    progress.status === 'converting' ? '55%' :
    progress.status === 'uploading' ? '25%' :
    '0%'

  return (
    <div className="convert-progress">
      <div className="convert-progress__bar">
        <div className="convert-progress__fill" style={{ width }} />
      </div>
      <div className="convert-progress__label">{progress.message}</div>
    </div>
  )
}

function formatDuration(ms) {
  if (ms == null) return null
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

export default function StatusPanel({ templateName, progress, result, durationMs, onDownload }) {
  const downloadUrl = result?.filename ? `${DOWNLOAD_BASE}/${result.filename}` : null
  const durationText = formatDuration(durationMs)

  return (
    <section className="convert-panel convert-status-panel">
      <div className="convert-panel__header">
        <span>状态</span>
        {result?.success && downloadUrl ? (
          <button className="convert-primary-btn convert-primary-btn--sm" type="button" onClick={onDownload}>
            <IconDownload /> 下载
          </button>
        ) : null}
      </div>

      <div className="convert-panel__body">
        <ProgressBlock progress={progress} />

        {!progress && !result && <EmptyState />}

        {result?.success ? (
          <div className="convert-result-card">
            <div className="convert-result-card__header">
              <IconCheck />
              <h3>转换成功</h3>
            </div>
            <div className="convert-result-card__body">
              <div className="convert-result-row"><span>模板</span><strong>{templateName}</strong></div>
              <div className="convert-result-row"><span>文件数</span><strong>{result.parsed_files ?? '-'} 个</strong></div>
              <div className="convert-result-row"><span>涉及店铺</span><strong>{result.store_count} 个</strong></div>
              <div className="convert-result-row"><span>商品合计</span><strong>{result.total_quantity} 件</strong></div>
              <div className="convert-result-row"><span>记录数</span><strong>{result.item_count} 条</strong></div>
              <div className="convert-result-row"><span>文件</span><strong className="filename">{result.filename}</strong></div>
              {durationText ? (
                <div className="convert-result-row"><span>耗时</span><strong>{durationText}</strong></div>
              ) : null}
            </div>
          </div>
        ) : null}

        {result?.error && !result?.success ? (
          <div className="convert-error-card">
            <span className="convert-error-icon">✕</span>
            <p>{result.error}</p>
          </div>
        ) : null}
      </div>
    </section>
  )
}
