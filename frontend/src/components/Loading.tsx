import styles from './Loading.module.css'

interface LoadingProps {
  message?: string
}

export default function Loading({ message = '불러오는 중...' }: LoadingProps) {
  return (
    <div className={styles.wrapper} role="status" aria-live="polite">
      <div className={styles.spinner} aria-hidden="true" />
      <p className={styles.message}>{message}</p>
    </div>
  )
}
