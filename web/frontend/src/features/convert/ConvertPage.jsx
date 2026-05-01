import { useCallback, useEffect, useMemo, useState } from 'react'
import { IconDownload, IconSparkle } from '../../Icons'
import { apiClient, DOWNLOAD_BASE } from '../../lib/apiClient'
import './convert.css'
import TemplatePicker from './TemplatePicker'
import FileDropzone from './FileDropzone'
import StatusPanel from './StatusPanel'
import LogPanel from './LogPanel'
import MissingCodesDialog from './MissingCodesDialog'

const FALLBACK_TEMPLATES = {
  qzz: { name: '黔寨寨贵州烙锅', accept: '.pdf' },
  lmt: { name: '黎明屯铁锅炖', accept: '.xlsx,.xls' },
  hlmc: { name: '欢乐牧场', accept: '.xlsx,.xls' },
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
    changes: ['重构为Web应用（FastAPI + React），删除桌面端代码'],
  },
  {
    version: 'v2.3',
    date: '2025-04-25 10:00',
    changes: ['重构项目目录 (src/assets/templates)，欢乐牧场合并输出'],
  },
  {
    version: 'v2.2',
    date: '2025-04-24 16:00',
    changes: ['新增欢乐牧场模板'],
  },
  {
    version: 'v2.1',
    date: '2025-04-24 10:00',
    changes: ['新增黎明屯铁锅炖模板'],
  },
  {
    version: 'v2.0',
    date: '2025-04-23 15:00',
    changes: ['多模板下拉选择器'],
  },
  {
    version: 'v1.3',
    date: '2025-04-20 10:00',
    changes: ['优化异步处理和日志显示'],
  },
  {
    version: 'v1.2',
    date: '2025-04-18 12:00',
    changes: ['双平台打包支持'],
  },
  {
    version: 'v1.1',
    date: '2025-04-15 09:00',
    changes: ['GUI界面'],
  },
  {
    version: 'v1.0',
    date: '2025-04-10 08:00',
    changes: ['基础PDF转Excel'],
  },
]

function VersionModal({ onClose }) {
  return (
    <div className="version-overlay" onClick={onClose}>
      <div className="version-modal" onClick={e => e.stopPropagation()}>
        <div className="version-modal__header">
          <h3>版本更新记录</h3>
          <button className="version-modal__close" onClick={onClose} type="button">✕</button>
        </div>
        <div className="version-modal__body">
          {VERSION_HISTORY.map(v => (
            <div key={v.version} className={`version-entry ${v.version === CURRENT_VERSION ? 'current' : ''}`}>
              <div className="version-entry__header">
                <div className="version-entry__version">
                  <span className={`version-tag ${v.version === CURRENT_VERSION ? 'current' : ''}`}>{v.version}</span>
                  <span className="version-date">{v.date}</span>
                </div>
                {v.version === CURRENT_VERSION ? <span className="version-badge-latest">当前</span> : null}
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

export default function ConvertPage({ onOpenSplit }) {
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES)
  const [templateKey, setTemplateKey] = useState('qzz')
  const [files, setFiles] = useState([])
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [logLines, setLogLines] = useState([])
  const [missingCodes, setMissingCodes] = useState(null)
  const [versionShow, setVersionShow] = useState(false)
  const [durationMs, setDurationMs] = useState(null)

  const addLine = useCallback((msg, type = 'info') => {
    setLogLines(prev => [
      ...prev,
      { msg, type, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` },
    ])
  }, [])

  useEffect(() => {
    apiClient.get('/templates')
      .then(res => {
        const list = res?.data?.templates
        if (!Array.isArray(list) || list.length === 0) {
          // 后端返回空数组时不要覆盖前端 fallback，否则下拉会变空
          addLine('⚠️ 模板列表为空，使用内置模板列表', 'warn')
          return
        }
        const map = {}
        for (const t of list) {
          map[t.key] = { name: t.name, accept: t.accept }
        }
        setTemplates(map)
        const firstKey = list[0]?.key
        if (firstKey) setTemplateKey(firstKey)
      })
      .catch(() => addLine('⚠️ 无法获取模板列表，使用内置模板列表', 'warn'))
  }, [addLine])

  const template = templates[templateKey] || FALLBACK_TEMPLATES[templateKey]
  const acceptExts = useMemo(() => getAcceptExts(template?.accept || '.pdf'), [template?.accept])

  const handleTemplateChange = (key) => {
    setTemplateKey(key)
    setFiles([])
    setResult(null)
    setLogLines([])
    setProgress(null)
    setDurationMs(null)
    setMissingCodes(null)
  }

  const checkExt = useCallback((f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    return acceptExts.includes(ext)
  }, [acceptExts])

  const onFilePick = useCallback((list) => {
    if (!list?.length) return
    const selected = Array.from(list)
    setFiles(selected)
    setResult(null)
    const names = selected.map(f => f.name).join('、')
    setLogLines(p => [
      ...p,
      { msg: `已选择${selected.length}个文件: ${names}`, type: 'info', id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` },
    ])
  }, [])

  const removeFile = (idx) => setFiles(p => p.filter((_, i) => i !== idx))

  const isBusy = progress?.status === 'uploading' || progress?.status === 'converting'

  const handleConvert = async () => {
    if (!files.length) { addLine('请先选择文件', 'warn'); return }
    const bad = files.find(f => !checkExt(f))
    if (bad) {
      addLine(`文件 '${bad.name}' 格式不匹配，该模板需要: ${template.accept.replace(/,/g, ' / ')}`, 'error')
      return
    }

    setMissingCodes(null)
    setProgress({ status: 'uploading', message: `正在上传 ${files.length} 个文件...` })
    addLine(`📤 开始上传 ${files.length} 个文件...`, 'info')
    setResult(null)
    setDurationMs(null)

    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    fd.append('template_key', templateKey)

    let t0 = null
    try {
      addLine('🔄 正在转换...', 'info')
      setProgress({ status: 'converting', message: '正在转换数据...' })
      t0 = Date.now()

      const res = await apiClient.post('/convert', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120_000,
      })
      setDurationMs(Date.now() - t0)

      if (res.data.success) {
        setProgress({ status: 'done', message: '转换完成!' })
        setResult(res.data)
        addLine(`✅ 转换成功! 共 ${res.data.parsed_files} 个文件，${res.data.item_count} 条记录`, 'success')
        addLine(`📁 输出文件: ${res.data.filename}`, 'info')
        if (res.data.warnings && res.data.warnings.length > 0) {
          res.data.warnings.forEach(w => addLine(w, 'warn'))
        }

        // 保留：转换成功后自动下载
        try {
          const link = document.createElement('a')
          link.href = `${DOWNLOAD_BASE}/${res.data.filename}`
          link.download = res.data.filename
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        } catch (err) {
          addLine(`⚠️ 自动下载失败，请点击“下载结果”手动下载（${err?.message || '未知原因'}）`, 'warn')
        }
      } else {
        setProgress(null)
        addLine(`❌ 转换失败: ${res.data.error}`, 'error')
        setResult({ success: false, error: res.data.error })
      }
    } catch (e) {
      setProgress(null)
      if (t0 != null) setDurationMs(Date.now() - t0)

      // 保留：缺失编码弹窗保存并重试
      if (Array.isArray(e?.codes) && e.codes.length) {
        setMissingCodes(e.codes)
        addLine(`❌ 转换已取消：${e.codes.length} 个商品编码未在拆零管理表中配置`, 'error')
        setResult({ success: false, error: e.message })
        return
      }

      addLine(`❌ 请求失败: ${e?.message || '未知错误'}`, 'error')
      setResult({ success: false, error: e?.message || '未知错误' })
    }
  }

  const handleDownload = () => {
    if (!result?.filename) return
    window.open(`${DOWNLOAD_BASE}/${result.filename}`, '_blank')
  }

  if (!template) return <div className="app-loading">加载中...</div>

  return (
    <div className="convert-root">
      <div className="convert-bg-decoration" aria-hidden="true">
        <div className="convert-blob convert-blob-1" />
        <div className="convert-blob convert-blob-2" />
      </div>

      <div className="convert-inner">
        <header className="convert-header">
          <div className="convert-header-badges">
            <div className="convert-logo-badge"><IconSparkle /><span>出库单转换</span></div>
            <button className="convert-version-badge" onClick={() => setVersionShow(true)} type="button">{CURRENT_VERSION}</button>
          </div>
          <h1 className="convert-title">PDF/Excel 出库单 <em>转 Excel</em></h1>
          <p className="convert-subtitle">选择模板，上传文件，一键生成标准 OMS 出库表格</p>
        </header>

        <main className="convert-grid">
          <section className="convert-left convert-card">
            <div className="convert-section">
              <label className="convert-section-label"><span className="convert-label-icon">①</span> 选择模板</label>
              <TemplatePicker
                templates={templates}
                templateKey={templateKey}
                onChange={handleTemplateChange}
                disabled={isBusy}
              />
            </div>

            <div className="convert-section">
              <label className="convert-section-label"><span className="convert-label-icon">②</span> 上传文件</label>
              <FileDropzone
                key={templateKey}
                accept={template.accept}
                files={files}
                onPick={onFilePick}
                onRemove={removeFile}
                disabled={isBusy}
              />
            </div>

            <div className="convert-section">
              <button
                className="convert-primary-btn convert-primary-btn--wide"
                onClick={handleConvert}
                disabled={!files.length || isBusy}
                type="button"
              >
                {isBusy ? (
                  <><span className="spinner" />{progress?.message || '处理中...'}</>
                ) : (
                  <><IconDownload /> 开始转换</>
                )}
              </button>
            </div>
          </section>

          <aside className="convert-right">
            <StatusPanel
              templateName={template.name}
              progress={progress}
              result={result}
              durationMs={durationMs}
              onDownload={handleDownload}
            />
            <div style={{ height: 12 }} aria-hidden="true" />
            <LogPanel lines={logLines} onClear={() => setLogLines([])} />
          </aside>
        </main>

        <footer className="convert-footer">
          <span>出库单转换工具</span><span className="footer-dot">·</span><span>Powered by WMS Converter</span>
          <span className="footer-dot">·</span>
          <button className="footer-link" onClick={onOpenSplit} type="button">拆零管理</button>
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

      {versionShow ? <VersionModal onClose={() => setVersionShow(false)} /> : null}
    </div>
  )
}
