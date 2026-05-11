import type { ParsedAnswer } from '../../api/types'
import styles from './Chat.module.css'

interface SectionProps {
  icon: string
  label: string
  labelCls: string
  body: string
}

function AnswerSection({ icon, label, labelCls, body }: SectionProps) {
  return (
    <div className={styles.answerSection}>
      <div className={`${styles.answerSectionHeader} ${labelCls}`}>
        <span aria-hidden="true">{icon}</span>
        {label}
      </div>
      <div className={styles.answerSectionBody}>{body}</div>
    </div>
  )
}

interface Props {
  answer: ParsedAnswer
}

export default function FixedAnswerView({ answer }: Props) {
  return (
    <div className={styles.answerCard}>
      <AnswerSection
        icon="💡"
        label="결론"
        labelCls={styles.labelConclusion}
        body={answer.결론}
      />
      <AnswerSection
        icon="🔍"
        label="근거"
        labelCls={styles.labelEvidence}
        body={answer.근거}
      />
      <AnswerSection
        icon="✅"
        label="행동"
        labelCls={styles.labelAction}
        body={answer.행동}
      />
      <AnswerSection
        icon="⚠️"
        label="주의"
        labelCls={styles.labelCaution}
        body={answer.주의}
      />
    </div>
  )
}
