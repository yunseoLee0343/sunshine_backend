import { Link } from 'react-router-dom'
import styles from './Page.module.css'

export default function NotFound() {
  return (
    <div className={styles.page} style={{ textAlign: 'center', paddingTop: '4rem' }}>
      <p style={{ fontSize: '2.5rem' }}>🌵</p>
      <h1 className={styles.title}>페이지를 찾을 수 없어요</h1>
      <Link to="/" style={{ color: '#2d6a4f', fontSize: '0.9rem' }}>홈으로 돌아가기</Link>
    </div>
  )
}
