import { useCallback, useRef, useState } from 'react'
import { IconUpload, IconFile } from '../../Icons'

export default function FileDropzone({
  accept,
  files,
  onPick,
  onRemove,
  onClearAll,
  disabled = false,
}) {
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef(null)

  const onDragOver = (e) => {
    e.preventDefault()
    if (disabled) return
    setIsDragOver(true)
  }

  const onDragLeave = (e) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const onDrop = (e) => {
    e.preventDefault()
    if (disabled) return
    setIsDragOver(false)
    if (e.dataTransfer.files?.length) onPick(e.dataTransfer.files)
  }

  const handleClick = () => {
    if (disabled) return
    inputRef.current?.click()
  }

  const handleKeyDown = useCallback((e) => {
    if (disabled) return
    if (e.key === 'Enter' || e.key === ' ') handleClick()
  }, [disabled])

  return (
    <div
      className={`convert-upload-zone ${isDragOver ? 'drag-over' : ''} ${files.length ? 'has-files' : ''}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        onChange={(e) => onPick(e.target.files)}
        hidden
        disabled={disabled}
      />

      {files.length ? (
        <div className="convert-uploaded-files">
          {files.map((f, idx) => (
            <div key={`${f.name}-${f.size}-${idx}`} className="convert-uploaded-file">
              <IconFile />
              <div className="convert-file-meta">
                <strong>{f.name}</strong>
                <span>{(f.size / 1024).toFixed(1)} KB</span>
              </div>
              <button
                className="convert-file-remove"
                onClick={(e) => { e.stopPropagation(); onRemove(idx) }}
                type="button"
                disabled={disabled}
              >
                ✕
              </button>
            </div>
          ))}
          <div className="convert-file-counter">
            {files.length} 个文件
            {onClearAll && files.length >= 1 ? (
              <button className="convert-file-clear-all" onClick={(e) => { e.stopPropagation(); onClearAll() }} type="button">清除全部</button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="convert-upload-prompt">
          <IconUpload />
          <p>拖拽文件到此处，或 <em>点击选择</em></p>
          <span className="convert-file-types">支持格式: {accept?.replace(/,/g, ' / ')}</span>
        </div>
      )}
    </div>
  )
}
