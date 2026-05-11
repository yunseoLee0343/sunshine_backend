import client, { DEMO_USER_ID } from './client'
import type { CreatePlantResponse, SpeciesCandidatesResponse } from './types'

export interface CreatePlantParams {
  species_profile_id: string
  nickname: string
  room_name: string
}

export async function fetchSpeciesCandidates(imageRef: string): Promise<SpeciesCandidatesResponse> {
  const { data } = await client.post<SpeciesCandidatesResponse>('/plants/species-candidates', {
    user_id: DEMO_USER_ID,
    image_ref: imageRef,
    locale: 'ko-KR',
    top_k: 3,
  })
  return data
}

export async function createPlant(params: CreatePlantParams): Promise<CreatePlantResponse> {
  const { data } = await client.post<CreatePlantResponse>('/plants/', {
    user_id: DEMO_USER_ID,
    species_profile_id: params.species_profile_id,
    nickname: params.nickname.trim(),
    room_name: params.room_name,
  })
  return data
}
