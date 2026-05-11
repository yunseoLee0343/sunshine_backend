import type { HistoryItem } from '../../api/types'
import styles from './GrowthHistory.module.css'
import HistoryTimelineItem from './HistoryTimelineItem'

interface Props {
  items: HistoryItem[]
}

export default function GrowthTimeline({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyEmoji}>🌱</div>
        <div className={styles.emptyText}>아직 기록된 이력이 없어요</div>
      </div>
    )
  }

  return (
    <div className={styles.timeline}>
      {items.map((item, i) => (
        <HistoryTimelineItem key={`${item.timestamp}-${i}`} item={item} />
      ))}
    </div>
  )
}
