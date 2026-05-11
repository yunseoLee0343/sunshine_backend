import styles from './GrowthHistory.module.css'

export type FilterKey = 'all' | 'care' | 'env' | 'status'

const TABS: { key: FilterKey; label: string }[] = [
  { key: 'all',    label: '전체' },
  { key: 'care',   label: '관리' },
  { key: 'env',    label: '환경' },
  { key: 'status', label: '상태' },
]

interface Props {
  active: FilterKey
  onChange: (key: FilterKey) => void
}

export default function FilterTabs({ active, onChange }: Props) {
  return (
    <div className={styles.filterTabs}>
      {TABS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          className={`${styles.filterBtn} ${active === key ? styles.filterBtnActive : ''}`}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
