import type { WindowSnapshot } from '../../api/types'
import styles from './PlantDetail.module.css'

interface SensorCellProps {
  label: string
  value: number | null | undefined
  unit: string
  decimals?: number
}

function SensorCell({ label, value, unit, decimals = 0 }: SensorCellProps) {
  return (
    <div className={styles.sensorCell}>
      <span className={styles.sensorLabel}>{label}</span>
      {value != null ? (
        <span className={styles.sensorValue}>
          {value.toFixed(decimals)}
          <span className={styles.sensorUnit}>{unit}</span>
        </span>
      ) : (
        <span className={styles.sensorEmpty}>—</span>
      )}
    </div>
  )
}

interface Props {
  snapshot: WindowSnapshot | null | undefined
}

export default function SensorValueGrid({ snapshot }: Props) {
  return (
    <div className={styles.sensorGrid}>
      <SensorCell
        label="토양 수분"
        value={snapshot?.soil_moisture_pct.avg}
        unit="%"
      />
      <SensorCell
        label="온도"
        value={snapshot?.temperature_c.avg}
        unit="°C"
        decimals={1}
      />
      <SensorCell
        label="습도"
        value={snapshot?.humidity_pct.avg}
        unit="%"
      />
      <SensorCell
        label="조도"
        value={snapshot?.light_lux.avg}
        unit=" lux"
      />
    </div>
  )
}
