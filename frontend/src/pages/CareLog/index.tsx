import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { createCareLog, fetchCareLogs } from '../../api/careLogs'
import type { CharacterBlock, CareLogItem } from '../../api/types'
import Loading from '../../components/Loading'
import CareActionButtons from './CareActionButtons'
import CareFeedbackCard from './CareFeedbackCard'
import CareNoteForm from './CareNoteForm'
import styles from './CareLog.module.css'
import RecentCareLogs from './RecentCareLogs'

export default function CareLogPage() {
  const { plantId } = useParams<{ plantId: string }>()

  const [logs, setLogs] = useState<CareLogItem[]>([])
  const [feedback, setFeedback] = useState<CharacterBlock | null>(null)
  const [loadingLogs, setLoadingLogs] = useState(true)
  const [actionBusy, setActionBusy] = useState(false)
  const [noteOpen, setNoteOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initial load — setState calls only in async callbacks, not the effect body
  useEffect(() => {
    if (!plantId) return
    fetchCareLogs(plantId)
      .then((res) => setLogs(res.logs))
      .catch(() => {})
      .finally(() => setLoadingLogs(false))
  }, [plantId])

  // Refetch helper called after water/note actions (not from effects)
  async function reloadLogs() {
    if (!plantId) return
    try {
      const res = await fetchCareLogs(plantId)
      setLogs(res.logs)
    } catch {
      // non-blocking — log list failure shouldn't block actions
    }
  }

  async function handleWater() {
    if (!plantId) return
    setActionBusy(true)
    setError(null)
    setFeedback(null)
    try {
      const res = await createCareLog(plantId, 'watering')
      if (res.character) setFeedback(res.character)
      await reloadLogs()
    } catch {
      setError('물 주기 기록에 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setActionBusy(false)
    }
  }

  async function handleNoteSubmit(note: string) {
    if (!plantId) return
    setActionBusy(true)
    setError(null)
    try {
      await createCareLog(plantId, 'note', note)
      setNoteOpen(false)
      await reloadLogs()
    } catch {
      setError('노트 저장에 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setActionBusy(false)
    }
  }

  if (loadingLogs) return <Loading message="관리 기록을 불러오는 중..." />

  return (
    <div className={styles.page}>
      <div className={styles.sectionTitle}>관리하기</div>

      <CareActionButtons
        disabled={actionBusy}
        onWater={handleWater}
        onToggleNote={() => {
          setNoteOpen((v) => !v)
          setError(null)
        }}
        noteOpen={noteOpen}
      />

      {noteOpen && (
        <CareNoteForm
          disabled={actionBusy}
          onSubmit={handleNoteSubmit}
          onCancel={() => setNoteOpen(false)}
        />
      )}

      {feedback && (
        <CareFeedbackCard
          character={feedback}
          onClose={() => setFeedback(null)}
        />
      )}

      {error && (
        <div className={styles.errorBanner} role="alert">
          {error}
        </div>
      )}

      <div className={styles.sectionTitle}>최근 기록</div>
      <RecentCareLogs logs={logs} />
    </div>
  )
}
