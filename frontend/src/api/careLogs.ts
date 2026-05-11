import client, { DEMO_USER_ID } from './client'
import type { CareActionType, CareLogCreateResponse, CareLogListResponse } from './types'

export async function createCareLog(
  plantId: string,
  actionType: CareActionType,
  note?: string,
): Promise<CareLogCreateResponse> {
  const { data } = await client.post<CareLogCreateResponse>(
    `/plants/${plantId}/care-logs`,
    {
      user_id: DEMO_USER_ID,
      action_type: actionType,
      note: note ?? null,
      acted_at: new Date().toISOString(),
    },
  )
  return data
}

export async function fetchCareLogs(plantId: string): Promise<CareLogListResponse> {
  const { data } = await client.get<CareLogListResponse>(`/plants/${plantId}/care-logs`)
  return data
}
