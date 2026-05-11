import { useState } from 'react'
import styles from './CareLog.module.css'

interface Props {
  disabled: boolean
  onSubmit: (note: string) => void
  onCancel: () => void
}

export default function CareNoteForm({ disabled, onSubmit, onCancel }: Props) {
  const [text, setText] = useState('')

  function handleSubmit() {
    const trimmed = text.trim()
    if (!trimmed) return
    onSubmit(trimmed)
    setText('')
  }

  return (
    <div className={styles.noteForm}>
      <textarea
        className={styles.noteTextarea}
        placeholder="오늘 식물 상태나 한 일을 기록해 보세요..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        rows={3}
      />
      <div className={styles.noteActions}>
        <button
          type="button"
          className={styles.btnCancelNote}
          onClick={onCancel}
          disabled={disabled}
        >
          취소
        </button>
        <button
          type="button"
          className={styles.btnSubmitNote}
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
        >
          기록하기
        </button>
      </div>
    </div>
  )
}
