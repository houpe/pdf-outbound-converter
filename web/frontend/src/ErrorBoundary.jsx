import { Component } from 'react'
import './ErrorBoundary.css'

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
        <div className="error-boundary">
          <h2>页面出现错误</h2>
          <p className="error-boundary__subtitle">请刷新页面重试</p>
          <details className="error-boundary__details">
            <summary className="error-boundary__summary">错误详情</summary>
            <pre className="error-boundary__trace">
              {this.state.error?.message || '未知错误'}
            </pre>
          </details>
          <button
            className="error-boundary__btn"
            onClick={() => window.location.reload()}
          >
            刷新页面
          </button>
        </div>
      )
    }
    return this.props.children
  }
}