import client, { DEMO_USER_ID } from './client'
import type { ChatAnswerResponse } from './types'

export function createRequestId(): string {
  const randomUUID = globalThis.crypto?.randomUUID
  if (typeof randomUUID === 'function') {
    return randomUUID.call(globalThis.crypto)
  }

  // Fallback for non-HTTPS public dev origins where crypto.randomUUID
  // is unavailable. Sufficient for client-side request idempotency.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16)
    const value = char === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}

export async function sendChat(
  plantId: string,
  question: string,
): Promise<ChatAnswerResponse> {
  const { data } = await client.post<ChatAnswerResponse>(
    `/plants/${plantId}/chat`,
    {
      request_id: createRequestId(),
      user_id: DEMO_USER_ID,
      question,
    },
  )
  return data
}
