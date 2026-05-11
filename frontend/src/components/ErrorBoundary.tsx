import { Component, type ErrorInfo, type ReactNode } from 'react'
import styles from './ErrorBoundary.module.css'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }

  handleReset = () => this.setState({ hasError: false, message: '' })

  render() {
    if (!this.state.hasError) return this.props.children
    if (this.props.fallback) return this.props.fallback

    return (
      <div className={styles.wrapper} role="alert">
        <p className={styles.icon}>⚠️</p>
        <h2 className={styles.title}>문제가 발생했어요</h2>
        <p className={styles.detail}>{this.state.message || '알 수 없는 오류입니다.'}</p>
        <button className={styles.button} onClick={this.handleReset}>
          다시 시도
        </button>
      </div>
    )
  }
}
