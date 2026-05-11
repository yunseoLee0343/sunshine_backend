import styles from './Chat.module.css'

const PRESETS = [
  '물 언제 줘야 해?',
  '잎이 노란색이야',
  '병충해가 생긴 것 같아',
  '흙이 너무 건조해',
  '같이 키우면 좋은 식물 추천해줘',
]

interface Props {
  disabled: boolean
  onSelect: (question: string) => void
}

export default function QuestionPresetBar({ disabled, onSelect }: Props) {
  return (
    <div className={styles.presetBar}>
      {PRESETS.map((q) => (
        <button
          key={q}
          type="button"
          className={styles.presetBtn}
          onClick={() => onSelect(q)}
          disabled={disabled}
        >
          {q}
        </button>
      ))}
    </div>
  )
}
