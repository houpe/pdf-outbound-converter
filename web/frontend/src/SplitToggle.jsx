function SplitToggle({ value, onChange }) {
  return (
    <div className="sm-toggle">
      <button type="button" className={`sm-toggle__btn ${value === '是' ? 'active' : ''}`} onClick={() => onChange('是')}>拆零</button>
      <button type="button" className={`sm-toggle__btn ${value === '否' ? 'active' : ''}`} onClick={() => onChange('否')}>不拆零</button>
    </div>
  )
}

export default SplitToggle