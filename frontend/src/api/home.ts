import client, { DEMO_USER_ID } from './client'
import type {
  EnvironmentDetailResponse,
  GetPlantResponse,
  HomeResponse,
  PlantHomeCard,
} from './types'

export function normalizeHomePlants(data: unknown): PlantHomeCard[] {
  const value = data as any
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.plants)) return value.plants
  if (Array.isArray(value?.cards)) return value.cards
  if (Array.isArray(value?.items)) return value.items
  return []
}

export async function fetchHome(): Promise<HomeResponse> {
  try {
    const { data } = await client.get<HomeResponse>('/home', {
      params: { user_id: DEMO_USER_ID },
    })
    const plants = normalizeHomePlants(data)
    if (plants.length > 0 || Array.isArray((data as any)?.plants)) {
      return {
        user_id: (data as any)?.user_id ?? DEMO_USER_ID,
        plants,
      }
    }
  } catch (err) {
    console.warn('[fetchHome] /home failed; falling back to /plants', err)
  }

  const { data } = await client.get('/plants', {
    params: { user_id: DEMO_USER_ID },
  })
  return {
    user_id: (data as any)?.user_id ?? DEMO_USER_ID,
    plants: normalizeHomePlants(data),
  }
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
