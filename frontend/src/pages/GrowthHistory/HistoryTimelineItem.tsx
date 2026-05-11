import type { HistoryItem } from '../../api/types'
import styles from './GrowthHistory.module.css'

// ---------------------------------------------------------------------------
// Type → dot class / badge class / icon
// ---------------------------------------------------------------------------

const TYPE_META: Record<
  HistoryItem['type'],
  { dotCls: string; badgeCls: string; badgeLabel: string; icon: string }
> = {
  care_log: {
    dotCls:     styles.dotCare,
    badgeCls:   styles.badgeCare,
    badgeLabel: '관리',
    icon:       '💧',
  },
  environment_summary: {
    dotCls:     styles.dotEnv,
    badgeCls:   styles.badgeEnv,
    badgeLabel: '환경',
    icon:       '🌡️',
  },
  character_state: {
    dotCls:     styles.dotStatus,
    badgeCls:   styles.badgeStatus,
    badgeLabel: '상태',
    icon:       '😊',
  },
}

// ---------------------------------------------------------------------------
// Time formatting
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffMin < 1)   return '방금 전'
  if (diffMin < 60)  return `${diffMin}분 전`
  if (diffHour < 24) return `${diffHour}시간 전`
  if (diffDay < 7)   return `${diffDay}일 전`

  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  item: HistoryItem
}

export default function HistoryTimelineItem({ item }: Props) {
  const meta = TYPE_META[item.type] ?? TYPE_META.care_log

  return (
    <div className={styles.item}>
      <div className={`${styles.dot} ${meta.dotCls}`} aria-hidden="true">
        {meta.icon}
      </div>
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <span className={`${styles.badge} ${meta.badgeCls}`}>
            {meta.badgeLabel}
          </span>
          <span className={styles.time}>{formatTime(item.timestamp)}</span>
        </div>
        <div className={styles.title}>{item.title}</div>
        {item.summary && (
          <div className={styles.summary}>{item.summary}</div>
        )}
      </div>
    </div>
  )
}
