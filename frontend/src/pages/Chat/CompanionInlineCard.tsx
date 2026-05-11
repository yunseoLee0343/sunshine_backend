import { useEffect, useState } from 'react'
import { fetchCompanionRecommendations } from '../../api/companion'
import type { CompanionRecommendationItem } from '../../api/types'
import styles from './Chat.module.css'

interface Props {
  plantId: string
}

export default function CompanionInlineCard({ plantId }: Props) {
  const [items, setItems] = useState<CompanionRecommendationItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCompanionRecommendations(plantId, 3)
      .then((res) => setItems(res.recommendations))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [plantId])

  if (loading) return null
  if (items.length === 0) {
    return (
      <div className={styles.companionSection}>
        <div className={styles.companionSectionTitle}>🌿 동반 식물 추천</div>
        <div className={styles.companionEmpty}>추천 가능한 동반 식물이 없어요.</div>
      </div>
    )
  }

  return (
    <div className={styles.companionSection}>
      <div className={styles.companionSectionTitle}>🌿 동반 식물 추천</div>
      <div className={styles.companionList}>
        {items.map((item) => (
          <div key={item.species_id} className={styles.companionCard}>
            <div className={styles.companionCardHeader}>
              <span className={styles.companionName}>{item.common_name}</span>
              <span className={styles.companionScore}>
                {Math.round(item.compatibility_score * 100)}%
              </span>
            </div>
            {item.scientific_name && (
              <div className={styles.companionScientific}>{item.scientific_name}</div>
            )}
            {item.match_reasons.length > 0 && (
              <div className={styles.companionReasons}>
                {item.match_reasons.map((r) => (
                  <span key={r} className={styles.companionReason}>{r}</span>
                ))}
              </div>
            )}
            {item.caution_notes.length > 0 && (
              <div className={styles.companionCaution}>
                ⚠️ {item.caution_notes[0]}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
