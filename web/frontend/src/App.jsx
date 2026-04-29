import { useState, useCallback, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = import.meta.env.PROD ? '/wms/api' : '/api'
const DOWNLOAD_BASE = import.meta.env.PROD ? '/wms/downloads' : '/downloads'

// Fallback used only during initial load / network error
const FALLBACK_TEMPLATES = {
  qzz:  { name: '黔寨寨贵州烙锅', accept: '.pdf' },
  lmt:  { name: '黎明屯铁锅炖',   accept: '.xlsx,.xls' },
  hlmc: { name: '欢乐牧场',       accept: '.xlsx,.xls' },
}

const getAcceptExts = (accept) => accept.split(',').map(s => s.trim())

function IconUpload() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
      <path d="M24 32V16M24 16l-8 8M24 16l8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8 32v4a4 4 0 004 4h24a4 4 0 004-4v-4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconCheck() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="10" fill="#10B981"/>
      <path d="M6 10.5l2.5 2.5L13 8" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconFile() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 3a2 2 0 012-2h5l5 5v10a2 2 0 01-2 2H6a2 2 0 01-2-2V3z" fill="#E8F5EC" stroke="#217346" strokeWidth="1.5"/>
      <path d="M11 1v5h5" stroke="#217346" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function IconDownload() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 4v10M10 14l-4-4M10 14l4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 14v2a2 2 0 002 2h8a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function IconSparkle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <path d="M11 2l2.2 5.8L19 10l-5.8 2.2L11 18l-2.2-5.8L3 10l5.8-2.2L11 2z" fill="currentColor" opacity="0.15"/>
      <path d="M11 5l1.4 3.6L16 10l-3.6 1.4L11 15l-1.4-3.6L6 10l3.6-1.4L11 5z" fill="currentColor"/>
    </svg>
  )
}

export default function App() {
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES)
  const [templateKey, setTemplateKey] = useState('qzz')
  const [files, setFiles] = useState([])
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [logLines, setLogLines] = useState([])
  const logCounter = useRef(0)
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
    logCounter.current += 1
    setLogLines(prev => [...prev, { msg, type, id: logCounter.current }])
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
    setLogLines(p => [...p, { msg: `已选择${selected.length}个文件: ${names}`, type: 'info', id: ++logCounter.current }])
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
    fd.append('merchant_code', merchantCode)

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
      } else {
        setProgress(null)
        addLine(`❌ 转换失败: ${res.data.error}`, 'error')
        setResult({ success: false, error: res.data.error })
      }
    } catch (err) {
      setProgress(null)
      const msg = err?.response?.data?.detail || err?.response?.data?.error || err?.message || '未知错误'
      addLine(`❌ 请求失败: ${msg}`, 'error')
      setResult({ success: false, error: msg })
    }
  }

  const handleDownload = () => {
    if (!result?.filename) return
    window.open(`${DOWNLOAD_BASE}/${result.filename}`, '_blank')
  }

  if (!template) return <div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>

  return (
    <div className="app-root">
      <div className="bg-decoration" aria-hidden="true">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
      </div>

      <div className="app-inner">
        <header className="app-header fade-in-up">
          <div className="logo-badge"><IconSparkle /><span>出库单转换</span></div>
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
        </footer>
      </div>
    </div>
  )
}
