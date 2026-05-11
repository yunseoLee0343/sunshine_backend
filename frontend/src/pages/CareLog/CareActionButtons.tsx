import styles from './CareLog.module.css'

interface Props {
  disabled: boolean
  onWater: () => void
  onToggleNote: () => void
  noteOpen: boolean
}

export default function CareActionButtons({ disabled, onWater, onToggleNote, noteOpen }: Props) {
  return (
    <div className={styles.actionRow}>
      <button
        type="button"
        className={styles.btnWater}
        onClick={onWater}
        disabled={disabled}
      >
        💧 물 주었어요
      </button>
      <button
        type="button"
        className={styles.btnNote}
        onClick={onToggleNote}
        disabled={disabled}
      >
        {noteOpen ? '✕ 취소' : '📝 노트'}
      </button>
    </div>
  )
}
