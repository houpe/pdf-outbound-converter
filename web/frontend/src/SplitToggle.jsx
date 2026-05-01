function SplitToggle({ value, onChange, disabled = false }) {
  return (
    <div className="sm-toggle">
      <button
        type="button"
        className={`sm-toggle__btn ${value === '是' ? 'active' : ''}`}
        onClick={() => !disabled && onChange('是')}
        disabled={disabled}
        aria-disabled={disabled}
      >
        拆零
      </button>
      <button
        type="button"
        className={`sm-toggle__btn ${value === '否' ? 'active' : ''}`}
        onClick={() => !disabled && onChange('否')}
        disabled={disabled}
        aria-disabled={disabled}
      >
        不拆零
      </button>
    </div>
  )
}

export default SplitToggle
