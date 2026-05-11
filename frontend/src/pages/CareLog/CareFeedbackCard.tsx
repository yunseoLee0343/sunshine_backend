import type { CharacterBlock } from '../../api/types'
import styles from './CareLog.module.css'

const MOOD_EMOJI: Record<string, string> = {
  happy:    '😊',
  thirsty:  '🥤',
  sleepy:   '😴',
  stressed: '😰',
  neutral:  '🌿',
}

const MOOD_LABEL: Record<string, string> = {
  happy:    '기분이 좋아졌어요',
  thirsty:  '아직 목말라요',
  sleepy:   '졸려요',
  stressed: '스트레스를 받고 있어요',
  neutral:  '보통이에요',
}

interface Props {
  character: CharacterBlock
  onClose: () => void
}

export default function CareFeedbackCard({ character, onClose }: Props) {
  const emoji = MOOD_EMOJI[character.mood] ?? '🌿'
  const moodLabel = MOOD_LABEL[character.mood] ?? character.mood

  return (
    <div className={styles.feedbackCard} role="status">
      <span className={styles.feedbackEmoji} aria-hidden="true">{emoji}</span>
      <div className={styles.feedbackBody}>
        <div className={styles.feedbackMessage}>
          "{character.status_message}"
        </div>
        <div className={styles.feedbackMood}>{moodLabel}</div>
      </div>
      <button
        type="button"
        className={styles.feedbackClose}
        onClick={onClose}
        aria-label="피드백 닫기"
      >
        ✕
      </button>
    </div>
  )
}
