import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchHistory } from '../../api/history'
import type { HistoryItem } from '../../api/types'
import Loading from '../../components/Loading'
import FilterTabs, { type FilterKey } from './FilterTabs'
import GrowthTimeline from './GrowthTimeline'
import styles from './GrowthHistory.module.css'

const TYPE_FOR_FILTER: Record<FilterKey, HistoryItem['type'] | null> = {
  all:    null,
  care:   'care_log',
  env:    'environment_summary',
  status: 'character_state',
}

export default function GrowthHistoryPage() {
  const { plantId } = useParams<{ plantId: string }>()

  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterKey>('all')

  useEffect(() => {
    if (!plantId) return
    setLoading(true)
    fetchHistory(plantId)
      .then((data) => {
        // Sort newest-first by timestamp
        const sorted = [...data].sort(
          (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        )
        setItems(sorted)
      })
      .catch(() => setError('이력을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))
      .finally(() => setLoading(false))
  }, [plantId])

  const filtered = useMemo(() => {
    const typeFilter = TYPE_FOR_FILTER[filter]
    if (!typeFilter) return items
    return items.filter((item) => item.type === typeFilter)
  }, [items, filter])

  if (loading) return <Loading message="이력을 불러오는 중..." />

  if (error) {
    return (
      <div className={styles.error}>
        <div>⚠️</div>
        <div>{error}</div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <FilterTabs active={filter} onChange={setFilter} />
      <GrowthTimeline items={filtered} />
    </div>
  )
}
