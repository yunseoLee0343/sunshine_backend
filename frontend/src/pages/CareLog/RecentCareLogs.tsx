import type { CareLogItem } from '../../api/types'
import styles from './CareLog.module.css'

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffMin < 1) return '방금 전'
  if (diffMin < 60) return `${diffMin}분 전`
  if (diffHour < 24) return `${diffHour}시간 전`
  if (diffDay < 7) return `${diffDay}일 전`

  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

const ACTION_LABEL: Record<string, string> = {
  watering: '물 주기',
  note:     '노트',
}

interface Props {
  logs: CareLogItem[]
}

export default function RecentCareLogs({ logs }: Props) {
  if (logs.length === 0) {
    return <div className={styles.emptyLogs}>아직 기록이 없어요. 첫 관리를 시작해 보세요!</div>
  }

  return (
    <div className={styles.timeline}>
      {logs.map((log) => (
        <div key={log.log_id} className={styles.timelineItem}>
          <div
            className={`${styles.timelineIcon} ${
              log.action_type === 'watering' ? styles.iconWatering : styles.iconNote
            }`}
            aria-hidden="true"
          >
            {log.action_type === 'watering' ? '💧' : '📝'}
          </div>
          <div className={styles.timelineContent}>
            <div className={styles.timelineAction}>
              {ACTION_LABEL[log.action_type] ?? log.action_type}
            </div>
            <div className={styles.timelineTime}>{formatTime(log.acted_at)}</div>
            {log.note && (
              <div className={styles.timelineNote}>{log.note}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
