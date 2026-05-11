import client, { DEMO_USER_ID } from './client'
import type {
  EnvironmentDetailResponse,
  GetPlantResponse,
  HomeResponse,
} from './types'

export async function fetchHome(): Promise<HomeResponse> {
  const { data } = await client.get<HomeResponse>('/home')
  return data
}

export async function fetchPlant(plantId: string): Promise<GetPlantResponse> {
  const { data } = await client.get<GetPlantResponse>(`/plants/${plantId}`)
  return data
}

export async function fetchEnvironment(plantId: string): Promise<EnvironmentDetailResponse> {
  // environment endpoint requires user_id as a query param (Query(...) — required)
  const { data } = await client.get<EnvironmentDetailResponse>(
    `/plants/${plantId}/environment`,
    { params: { user_id: DEMO_USER_ID } },
  )
  return data
}
