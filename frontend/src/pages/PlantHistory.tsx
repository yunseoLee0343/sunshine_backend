import { useParams } from 'react-router-dom'
import styles from './Page.module.css'

export default function PlantHistory() {
  const { plantId } = useParams<{ plantId: string }>()
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>성장 이력</h1>
      <p className={styles.meta}>plant ID: {plantId}</p>
      <p className={styles.placeholder}>성장 이력 타임라인이 여기에 표시됩니다. (T-041)</p>
    </div>
  )
}
