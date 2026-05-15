import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchHome } from '../../api/home'
import type { PlantHomeCard } from '../../api/types'
import Loading from '../../components/Loading'
import styles from './Home.module.css'
import HomePlantCard from './HomePlantCard'

export default function Home() {
  const [plants, setPlants] = useState<PlantHomeCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHome()
      .then((res) => setPlants(Array.isArray(res.plants) ? res.plants : []))
      .catch((err) => {
        console.error('[Home] failed to load plants', err)
        setPlants([])
        setError('식물 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="식물 목록을 불러오는 중..." />

  if (error) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyEmoji}>⚠️</div>
        <div className={styles.emptyTitle}>오류가 발생했어요</div>
        <div className={styles.emptyHint}>{error}</div>
      </div>
    )
  }

  if (plants.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyEmoji}>🌱</div>
        <div className={styles.emptyTitle}>아직 등록된 식물이 없어요</div>
        <div className={styles.emptyHint}>첫 번째 식물을 등록하고 케어를 시작해 보세요!</div>
        <Link to="/onboarding" className={styles.emptyBtn}>
          + 식물 등록하기
        </Link>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>내 식물</h1>
        <Link to="/onboarding" className={styles.addBtn}>
          + 추가
        </Link>
      </div>

      <div className={styles.grid}>
        {plants.map((plant) => (
          <HomePlantCard key={plant.plant_id} plant={plant} />
        ))}
      </div>
    </div>
  )
}
