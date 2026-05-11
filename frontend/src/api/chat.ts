import client, { DEMO_USER_ID } from './client'
import type { ChatAnswerResponse } from './types'

export async function sendChat(
  plantId: string,
  question: string,
): Promise<ChatAnswerResponse> {
  const { data } = await client.post<ChatAnswerResponse>(
    `/plants/${plantId}/chat`,
    {
      request_id: crypto.randomUUID(),
      user_id: DEMO_USER_ID,
      question,
    },
  )
  return data
}
