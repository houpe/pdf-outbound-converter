import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: 'center', fontFamily: 'system-ui' }}>
          <h2>页面出现错误</h2>
          <p style={{ color: '#666' }}>请刷新页面重试</p>
          <details style={{ marginTop: 16, textAlign: 'left', maxWidth: 500, margin: '16px auto 0' }}>
            <summary style={{ cursor: 'pointer', color: '#999' }}>错误详情</summary>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, fontSize: 12, overflow: 'auto', marginTop: 8 }}>
              {this.state.error?.message || '未知错误'}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 20, padding: '8px 24px', background: '#217346', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
          >
            刷新页面
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
