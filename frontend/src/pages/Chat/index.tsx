import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { sendChat } from '../../api/chat'
import type { ChatAnswerResponse } from '../../api/types'
import EvidenceSummary from './EvidenceSummary'
import FixedAnswerView from './FixedAnswerView'
import PestCautionBanner from './PestCautionBanner'
import QuestionPresetBar from './QuestionPresetBar'
import styles from './Chat.module.css'

// ---------------------------------------------------------------------------
// Local message types
// ---------------------------------------------------------------------------

interface UserMsg  { type: 'user';      text: string }
interface BotMsg   { type: 'assistant'; response: ChatAnswerResponse }
type Msg = UserMsg | BotMsg

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const { plantId } = useParams<{ plantId: string }>()

  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom whenever messages or thinking state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  async function submit(question: string) {
    const q = question.trim()
    if (!q || !plantId || thinking) return

    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { type: 'user', text: q }])
    setThinking(true)

    try {
      const res = await sendChat(plantId, q)
      setMessages((prev) => [...prev, { type: 'assistant', response: res }])
    } catch {
      setError('답변을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setThinking(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(input)
    }
  }

  const isIdle = !thinking

  return (
    <div className={styles.chatPage}>
      {/* ── Message list ── */}
      <div className={styles.messageList}>
        {messages.length === 0 && !thinking && (
          <div className={styles.intro}>
            <div className={styles.introEmoji}>🌿</div>
            <div className={styles.introTitle}>식물 케어 도우미</div>
            <div className={styles.introHint}>
              물주기, 잎 상태, 병충해 등 무엇이든 물어보세요!
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.type === 'user') {
            return (
              <div key={i} className={styles.userBubble}>
                {msg.text}
              </div>
            )
          }

          const res = msg.response
          return (
            <div key={i} className={styles.assistantBlock}>
              {res.is_reference_only && <PestCautionBanner />}
              <FixedAnswerView answer={res.answer} />
              <EvidenceSummary response={res} />
            </div>
          )
        })}

        {thinking && (
          <div className={styles.thinking}>
            <div className={styles.thinkingDots}>
              <span /><span /><span />
            </div>
            생각하는 중...
          </div>
        )}

        {error && (
          <div className={styles.errorBanner} role="alert">{error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input area ── */}
      <div className={styles.inputArea}>
        <QuestionPresetBar
          disabled={!isIdle}
          onSelect={(q) => submit(q)}
        />
        <div className={styles.inputRow}>
          <textarea
            ref={textareaRef}
            className={styles.inputBox}
            placeholder="질문을 입력하세요... (Shift+Enter 줄바꿈)"
            value={input}
            rows={1}
            disabled={!isIdle}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            type="button"
            className={styles.sendBtn}
            onClick={() => submit(input)}
            disabled={!isIdle || !input.trim()}
            aria-label="전송"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}
