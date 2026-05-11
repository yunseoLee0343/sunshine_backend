import { useParams } from 'react-router-dom'
import styles from './Page.module.css'

export default function PlantCare() {
  const { plantId } = useParams<{ plantId: string }>()
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>관리 기록</h1>
      <p className={styles.meta}>plant ID: {plantId}</p>
      <p className={styles.placeholder}>관리 기록 UI가 여기에 구현됩니다. (T-039)</p>
    </div>
  )
}
