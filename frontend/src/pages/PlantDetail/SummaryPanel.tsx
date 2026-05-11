import type { EnvMetricStats, WindowSnapshot } from '../../api/types'
import styles from './PlantDetail.module.css'

interface MetricRowProps {
  label: string
  stats: EnvMetricStats | undefined
  unit: string
  decimals?: number
}

function fmt(v: number | null | undefined, decimals: number): string {
  return v != null ? v.toFixed(decimals) : '—'
}

function MetricRow({ label, stats, unit, decimals = 0 }: MetricRowProps) {
  if (!stats || (stats.avg == null && stats.min == null && stats.max == null)) {
    return null
  }
  return (
    <div className={styles.summaryRow}>
      <span className={styles.summaryMetric}>{label}</span>
      <div className={styles.summaryStats}>
        <span className={styles.statChip}>
          <span className={styles.statChipLabel}>평균</span>
          {fmt(stats.avg, decimals)}{unit}
        </span>
        <span className={styles.statChip}>
          <span className={styles.statChipLabel}>최소</span>
          {fmt(stats.min, decimals)}{unit}
        </span>
        <span className={styles.statChip}>
          <span className={styles.statChipLabel}>최대</span>
          {fmt(stats.max, decimals)}{unit}
        </span>
      </div>
    </div>
  )
}

interface Props {
  title: string
  snapshot: WindowSnapshot | null | undefined
}

export default function SummaryPanel({ title, snapshot }: Props) {
  return (
    <div className={styles.summaryPanel}>
      <div className={styles.summaryPanelTitle}>{title}</div>
      {snapshot ? (
        <>
          <MetricRow label="토양 수분" stats={snapshot.soil_moisture_pct} unit="%" />
          <MetricRow label="온도"      stats={snapshot.temperature_c}     unit="°C" decimals={1} />
          <MetricRow label="습도"      stats={snapshot.humidity_pct}      unit="%" />
          <MetricRow label="조도"      stats={snapshot.light_lux}         unit=" lux" />
        </>
      ) : (
        <div className={styles.summaryEmpty}>데이터가 없어요</div>
      )}
    </div>
  )
}
