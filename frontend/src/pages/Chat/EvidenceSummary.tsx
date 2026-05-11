import type { ChatAnswerResponse } from '../../api/types'
import styles from './Chat.module.css'

const INTENT_LABEL: Record<string, string> = {
  watering_question:       '물주기 질문',
  pest_reference_question: '병충해 질문',
  companion_plant_question:'동반 식물 질문',
  unknown_question:        '일반 질문',
}

interface Props {
  response: ChatAnswerResponse
}

export default function EvidenceSummary({ response }: Props) {
  const intentLabel = INTENT_LABEL[response.intent] ?? response.intent

  return (
    <div className={styles.evidenceSummary}>
      <span className={styles.evidenceBadge}>{intentLabel}</span>
      <span className={styles.evidenceBadge}>{response.model_name}</span>
      {response.from_cache && (
        <span className={`${styles.evidenceBadge} ${styles.evidenceBadgeCached}`}>
          캐시 응답
        </span>
      )}
      {response.guardrails_applied.map((g) => (
        <span key={g} className={styles.evidenceBadge}>
          가드레일: {g}
        </span>
      ))}
    </div>
  )
}
