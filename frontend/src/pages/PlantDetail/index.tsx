import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchEnvironment, fetchPlant } from '../../api/home'
import type { EnvironmentDetailResponse, PlantCard } from '../../api/types'
import Loading from '../../components/Loading'
import styles from './PlantDetail.module.css'
import CharacterRenderer from './CharacterRenderer'
import SensorValueGrid from './SensorValueGrid'
import SummaryPanel from './SummaryPanel'

export default function PlantDetail() {
  const { plantId } = useParams<{ plantId: string }>()

  const [plant, setPlant] = useState<PlantCard | null>(null)
  const [env, setEnv] = useState<EnvironmentDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!plantId) return
    setLoading(true)

    Promise.all([fetchPlant(plantId), fetchEnvironment(plantId)])
      .then(([plantRes, envRes]) => {
        setPlant(plantRes.plant)
        setEnv(envRes)
      })
      .catch(() => setError('식물 정보를 불러오지 못했어요.'))
      .finally(() => setLoading(false))
  }, [plantId])

  if (loading) return <Loading message="식물 정보를 불러오는 중..." />

  if (error || !plant) {
    return (
      <div className={styles.error}>
        {error ?? '식물 정보를 찾을 수 없어요.'}
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <CharacterRenderer plant={plant} />

      <div className={styles.sectionTitle}>현재 환경</div>
      <SensorValueGrid snapshot={env?.latest} />

      <div className={styles.sectionTitle}>24시간 요약</div>
      <SummaryPanel title="최근 24시간" snapshot={env?.summary_24h} />

      <div className={styles.sectionTitle}>7일 요약</div>
      <SummaryPanel title="최근 7일" snapshot={env?.summary_7d} />

      {env?.character_explanation && (
        <>
          <div className={styles.sectionTitle}>상태 설명</div>
          <div className={styles.explanationBox}>
            {env.character_explanation.explanation}
          </div>
        </>
      )}
    </div>
  )
}
