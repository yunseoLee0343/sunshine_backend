import client from './client'
import type { CompanionRecommendationResponse } from './types'

export async function fetchCompanionRecommendations(
  plantId: string,
  topK = 5,
): Promise<CompanionRecommendationResponse> {
  const { data } = await client.get<CompanionRecommendationResponse>(
    `/plants/${plantId}/companion-recommendations`,
    { params: { top_k: topK } },
  )
  return data
}
