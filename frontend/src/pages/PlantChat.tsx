import { useParams } from 'react-router-dom'
import styles from './Page.module.css'

export default function PlantChat() {
  const { plantId } = useParams<{ plantId: string }>()
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>지능형 채팅</h1>
      <p className={styles.meta}>plant ID: {plantId}</p>
      <p className={styles.placeholder}>AI 채팅 인터페이스가 여기에 구현됩니다. (T-040)</p>
    </div>
  )
}
