import { useState, useCallback, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import SplitManager from './SplitManager'
import { IconUpload, IconCheck, IconFile, IconDownload, IconSparkle } from './Icons'
import SplitToggle from './SplitToggle'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'
const DOWNLOAD_BASE = import.meta.env.PROD ? '/wms/downloads' : '/downloads'

const FALLBACK_TEMPLATES = {
  qzz:  { name: '黔寨寨贵州烙锅', accept: '.pdf' },
  lmt:  { name: '黎明屯铁锅炖',   accept: '.xlsx,.xls' },
  hlmc: { name: '欢乐牧场',       accept: '.xlsx,.xls' },
}

const CURRENT_VERSION = 'v3.7'

const VERSION_HISTORY = [
  {
    version: 'v3.7',
    date: '2025-05-01 22:30',
    changes: [
      '首页增加版本号徽章，点击即可查看完整更新记录弹窗',
      '修复欢乐牧场模板中无商品编码/名称的行被错误转换的问题',
    ],
  },
  {
    version: 'v3.6',
    date: '2026-04-29 18:58',
    changes: [
      '后端模块化重构：拆分单文件为 config/database/schemas/parsers/services/middleware',
      '前端提取共享 Icons/SplitToggle 组件，内联样式迁移到 CSS',
      '新增 70+ pytest 测试套件覆盖解析/转换/CRUD/限流',
      '启用 API 限流，收紧 CORS 策略',
    ],
  },
  {
    version: 'v3.5',
    date: '2025-05-01 12:00',
    changes: [
      '商品拆零配置改为 SQLite 页面维护',
      '拆零管理支持内联新增/编辑/保存、创建时间倒序、页面内确认删除',
      '黎明屯缺失编码支持弹窗内配置并重试',
      '仅黎明屯转换校验拆零配置',
    ],
  },
  {
    version: 'v3.4',
    date: '2025-04-28 16:54',
    changes: [
      '修复拆零路由：新增模板回退查找逻辑',
      'LMT门店信息从模板「收货机构」读取',
    ],
  },
  {
    version: 'v3.3',
    date: '2025-04-28 12:00',
    changes: [
      '新增转换日志（JSONL）、拆零模板自动路由',
      '转换成功后自动下载',
    ],
  },
  {
    version: 'v3.2',
    date: '2025-04-28 10:00',
    changes: [
      '安全加固：路径遍历防护、lifespan 替换废弃 API',
      '清理端点移除、requirements 合并',
    ],
  },
  {
    version: 'v3.1',
    date: '2025-04-27 18:00',
    changes: [
      'CORS 限定来源、动态模板获取',
      '流式上传、TTL 清理、文件限制',
    ],
  },
  {
    version: 'v3.0',
    date: '2025-04-27 14:00',
    changes: [
      '重构为Web应用（FastAPI + React），删除桌面端代码',
    ],
  },
  {
    version: 'v2.3',
    date: '2025-04-25 10:00',
    changes: [
      '重构项目目录 (src/assets/templates)，欢乐牧场合并输出',
    ],
  },
  {
    version: 'v2.2',
    date: '2025-04-24 16:00',
    changes: [
      '新增欢乐牧场模板',
    ],
  },
  {
    version: 'v2.1',
    date: '2025-04-24 10:00',
    changes: [
      '新增黎明屯铁锅炖模板',
    ],
  },
  {
    version: 'v2.0',
    date: '2025-04-23 15:00',
    changes: [
      '多模板下拉选择器',
    ],
  },
  {
    version: 'v1.3',
    date: '2025-04-20 10:00',
    changes: [
      '优化异步处理和日志显示',
    ],
  },
  {
    version: 'v1.2',
    date: '2025-04-18 12:00',
    changes: [
      '双平台打包支持',
    ],
  },
  {
    version: 'v1.1',
    date: '2025-04-15 09:00',
    changes: [
      'GUI界面',
    ],
  },
  {
    version: 'v1.0',
    date: '2025-04-10 08:00',
    changes: [
      '基础PDF转Excel',
    ],
  },
]

function VersionModal({ version, onClose }) {
  if (!version) return null
  return (
    <div className="version-overlay" onClick={onClose}>
      <div className="version-modal" onClick={e => e.stopPropagation()}>
        <div className="version-modal__header">
          <h3>版本更新记录</h3>
          <button className="version-modal__close" onClick={onClose}>✕</button>
        </div>
        <div className="version-modal__body">
          {VERSION_HISTORY.map(v => (
            <div key={v.version} className={`version-entry ${v.version === CURRENT_VERSION ? 'current' : ''}`}>
              <div className="version-entry__header">
                <div className="version-entry__version">
                  <span className={`version-tag ${v.version === CURRENT_VERSION ? 'current' : ''}`}>{v.version}</span>
                  <span className="version-date">{v.date}</span>
                </div>
                {v.version === CURRENT_VERSION && <span className="version-badge-latest">当前</span>}
              </div>
              <ul className="version-entry__changes">
                {v.changes.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const getAcceptExts = (accept) => accept.split(',').map(s => s.trim())

function MissingCodesDialog({ codes = [], onClose, onRetry }) {
  const [items, setItems] = useState(() => codes.map(c => ({ code: c.code, split: '是', source: c.source })))
  const [loading, setLoading] = useState(false)

  const handleSave = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/split-codes/batch`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items.map(i => ({ id: '', code: i.code, split: i.split }))),
      })
      if (!res.ok) throw new Error('请求失败')
      setLoading(false)
      onClose()
      if (onRetry) onRetry()
    } catch {
      setLoading(false)
    }
  }

  const updateItem = (index, field, value) => {
    setItems(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  return (
    <div className="missing-overlay" onClick={onClose}>
      <div className="missing-dialog" onClick={e => e.stopPropagation()}>
        <div className="missing-dialog__header">
          <h3>⚠️ 需配置拆零规则</h3>
          <button className="missing-dialog__close" onClick={onClose}>✕</button>
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
                <SplitToggle value={item.split} onChange={val => updateItem(i, 'split', val)} />
              </div>
            ))}
          </div>
        </div>
        <div className="missing-dialog__footer">
          <button className="missing-dialog__btn missing-dialog__btn--primary" onClick={handleSave} disabled={loading}>
            {loading ? '保存中...' : '保存并重试'}
          </button>
          <button className="missing-dialog__btn" onClick={onClose}>取消</button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState('convert')
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES)
  const [templateKey, setTemplateKey] = useState('qzz')
  const [files, setFiles] = useState([])
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [missingCodes, setMissingCodes] = useState(null)
  const [versionShow, setVersionShow] = useState(false)
  const fileInputRef = useRef(null)

  // Fetch templates from backend on mount
  useEffect(() => {
    axios.get(`${API_BASE}/templates`)
      .then(res => {
        const map = {}
        for (const t of res.data.templates) {
          map[t.key] = { name: t.name, accept: t.accept }
        }
        setTemplates(map)
        const firstKey = res.data.templates[0]?.key
        if (firstKey) setTemplateKey(firstKey)
      })
      .catch(() => setLogLines([{ msg: '⚠️ 无法获取模板列表，使用本地缓存', type: 'warn', id: Date.now() }]))
  }, [])

  const template = templates[templateKey] || FALLBACK_TEMPLATES[templateKey]
  const acceptExts = template ? getAcceptExts(template.accept) : ['.pdf']

  const addLine = useCallback((msg, type = 'info') => {
    setLogLines(prev => [...prev, { msg, type, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }])
  }, [])

  const handleTemplateChange = (key) => {
    setTemplateKey(key)
    setFiles([])
    setResult(null)
    setLogLines([])
    setProgress(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const checkExt = (f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    return acceptExts.includes(ext)
  }

  const onFilePick = useCallback((list) => {
    if (!list?.length) return
    const selected = Array.from(list)
    setFiles(selected)
    setResult(null)
    const names = selected.map(f => f.name).join('、')
    setLogLines(p => [...p, { msg: `已选择${selected.length}个文件: ${names}`, type: 'info', id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }])
  }, [])

  const onDragOver = (e) => { e.preventDefault(); setIsDragOver(true) }
  const onDragLeave = (e) => { e.preventDefault(); setIsDragOver(false) }
  const onDrop = (e) => {
    e.preventDefault(); setIsDragOver(false)
    if (e.dataTransfer.files?.length) onFilePick(e.dataTransfer.files)
  }

  const removeFile = (idx) => {
    setFiles(p => p.filter((_, i) => i !== idx))
  }

  const handleConvert = async () => {
    if (!files.length) { addLine('请先选择文件', 'warn'); return }
    const bad = files.find(f => !checkExt(f))
    if (bad) { addLine(`文件 '${bad.name}' 格式不匹配，该模板需要: ${template.accept.replace(/,/g, ' / ')}`, 'error'); return }

    setProgress({ status: 'uploading', message: `正在上传 ${files.length} 个文件...` })
    addLine(`📤 开始上传 ${files.length} 个文件...`, 'info')
    setResult(null)

    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    fd.append('template_key', templateKey)

    try {
      addLine('🔄 正在转换...', 'info')
      setProgress({ status: 'converting', message: '正在转换数据...' })

      const res = await axios.post(`${API_BASE}/convert`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120_000,
      })

      if (res.data.success) {
        setProgress({ status: 'done', message: '转换完成!' })
        setResult(res.data)
        addLine(`✅ 转换成功! 共 ${res.data.parsed_files} 个文件，${res.data.item_count} 条记录`, 'success')
        addLine(`📁 输出文件: ${res.data.filename}`, 'info')
        if (res.data.warnings && res.data.warnings.length > 0) {
          res.data.warnings.forEach(w => addLine(w, 'warn'))
        }
        const link = document.createElement('a')
        link.href = `${DOWNLOAD_BASE}/${res.data.filename}`
        link.download = res.data.filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else {
        setProgress(null)
        addLine(`❌ 转换失败: ${res.data.error}`, 'error')
        setResult({ success: false, error: res.data.error })
      }
    } catch (err) {
      setProgress(null)
      const detail = err?.response?.data?.detail
      if (detail && typeof detail === 'object' && detail.codes) {
        setMissingCodes(detail.codes)
        addLine(`❌ 转换已取消：${detail.codes.length} 个商品编码未在拆零管理表中配置`, 'error')
        setResult({ success: false, error: detail.message })
      } else {
        const msg = typeof detail === 'string' ? detail : (err?.response?.data?.error || err?.message || '未知错误')
        addLine(`❌ 请求失败: ${msg}`, 'error')
        setResult({ success: false, error: msg })
      }
    }
  }

  const handleDownload = () => {
    if (!result?.filename) return
    window.open(`${DOWNLOAD_BASE}/${result.filename}`, '_blank')
  }

  if (!template) return <div className="app-loading">加载中...</div>

  if (view === 'split') {
    return <SplitManager onBack={() => setView('convert')} />
  }

  return (
    <div className="app-root">
      <div className="bg-decoration" aria-hidden="true">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
      </div>

      <div className="app-inner">
        <header className="app-header fade-in-up">
          <div className="header-badges">
            <div className="logo-badge"><IconSparkle /><span>出库单转换</span></div>
            <button className="version-badge" onClick={() => setVersionShow(true)} type="button">{CURRENT_VERSION}</button>
          </div>
          <h1 className="app-title">PDF/Excel 出库单 <em>转 Excel</em></h1>
          <p className="app-subtitle">选择模板，上传文件，一键生成标准 OMS 出库表格</p>
        </header>

        <main className="main-card fade-in-up" style={{ animationDelay: '0.1s' }}>
          <section className="form-section">
            <label className="section-label"><span className="label-icon">①</span> 选择模板</label>
            <div className="template-grid">
              {Object.entries(templates).map(([key, t]) => (
                <button key={key} className={`template-btn ${templateKey === key ? 'active' : ''}`} onClick={() => handleTemplateChange(key)} type="button">
                  <span className="template-btn__check">{templateKey === key && <IconCheck />}</span>
                  <span className="template-btn__info">
                    <span className="template-btn__name">{t.name}</span>
                    <span className="template-btn__accept">支持 {t.accept.replace(/,/g, ' / ')}</span>
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="form-section">
            <label className="section-label"><span className="label-icon">②</span> 上传文件</label>
            <div className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${files.length ? 'has-files' : ''}`} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop} onClick={() => fileInputRef.current?.click()} role="button" tabIndex={0}>
              <input ref={fileInputRef} type="file" accept={template.accept} multiple onChange={(e) => onFilePick(e.target.files)} hidden />
              {files.length ? (
                <div className="uploaded-files">
                  {files.map((f, idx) => (
                    <div key={idx} className="uploaded-file">
                      <IconFile />
                      <div className="file-meta"><strong>{f.name}</strong><span>{(f.size / 1024).toFixed(1)} KB</span></div>
                      <button className="file-remove" onClick={(e) => { e.stopPropagation(); removeFile(idx) }}>✕</button>
                    </div>
                  ))}
                  <div className="file-counter">{files.length} 个文件</div>
                </div>
              ) : (
                <div className="upload-prompt">
                  <IconUpload />
                  <p>拖拽文件到此处，或 <em>点击选择</em></p>
                  <span className="file-types">支持格式: {template.accept.replace(/,/g, ' / ')}</span>
                </div>
              )}
            </div>
          </section>

          <section className="form-section form-actions">
            <button className="btn-convert" onClick={handleConvert} disabled={!files.length || progress?.status === 'uploading' || progress?.status === 'converting'}>
              {progress?.status === 'uploading' || progress?.status === 'converting' ? (
                <><span className="spinner" />{progress.message}</>
              ) : (
                <><IconDownload /> 开始转换</>
              )}
            </button>
          </section>

          {progress && (
            <div className="progress-wrap fade-in-up">
              <div className="progress-bar"><div className="progress-fill" style={{ width: progress.status === 'done' ? '100%' : progress.status === 'converting' ? '55%' : '25%' }} /></div>
              <span className="progress-label">{progress.message}</span>
            </div>
          )}

          {result?.success && (
            <section className="form-section form-actions">
              <button className="btn-download" onClick={handleDownload}><IconDownload /> 下载 Excel 文件</button>
            </section>
          )}

          {result?.success && (
            <section className="result-card fade-in-up">
              <div className="result-header"><IconCheck /><h3>转换成功</h3></div>
              <div className="result-body">
                <div className="result-row"><span>模板</span><strong>{template.name}</strong></div>
                <div className="result-row"><span>涉及店铺</span><strong>{result.store_count} 个</strong></div>
                <div className="result-row"><span>商品合计</span><strong>{result.total_quantity} 件</strong></div>
                <div className="result-row"><span>记录数</span><strong>{result.item_count} 条</strong></div>
                <div className="result-row"><span>文件</span><strong className="filename">{result.filename}</strong></div>
              </div>
            </section>
          )}

          {result?.error && !result.success && (
            <div className="error-card fade-in-up">
              <span className="error-icon">✕</span>
              <p>{result.error}</p>
            </div>
          )}
        </main>

        {logLines.length > 0 && (
          <div className="log-panel fade-in-up" style={{ animationDelay: '0.15s' }}>
            <div className="log-header"><span>处理日志</span><button className="log-clear" onClick={() => setLogLines([])}>清除</button></div>
            <div className="log-body">{logLines.map((l) => <div key={l.id} className={`log-line log-${l.type}`}>{l.msg}</div>)}</div>
          </div>
        )}

        <footer className="app-footer">
          <span>出库单转换工具</span><span className="footer-dot">·</span><span>Powered by WMS Converter</span>
          <span className="footer-dot">·</span>
          <button className="footer-link" onClick={() => setView('split')} type="button">拆零管理</button>
        </footer>
      </div>

      {missingCodes?.length ? (
        <MissingCodesDialog
          key={missingCodes.map(c => c.code).join('|')}
          codes={missingCodes}
          onClose={() => setMissingCodes(null)}
          onRetry={handleConvert}
        />
      ) : null}

      {versionShow && <VersionModal version={CURRENT_VERSION} onClose={() => setVersionShow(false)} />}
    </div>
  )
}