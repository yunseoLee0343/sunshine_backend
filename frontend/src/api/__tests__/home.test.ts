import { describe, it, expect, vi, beforeEach } from 'vitest'
import { normalizeHomePlants, fetchHome } from '../home'

const mockPlant = {
  plant_id: 'plant-1',
  nickname: '초록이',
  room_name: null,
  species_name: null,
  character: { mood: 'happy', expression: '😊', status_message: 'ok', primary_action: 'none', reason_code: 'ok' },
  environment: null,
  today_recommended_action: 'none' as const,
  care_status: 'good' as const,
}

// ---------------------------------------------------------------------------
// normalizeHomePlants
// ---------------------------------------------------------------------------
describe('normalizeHomePlants', () => {
  it('returns plants array from { plants: [...] }', () => {
    expect(normalizeHomePlants({ plants: [mockPlant] })).toEqual([mockPlant])
  })

  it('returns cards array from { cards: [...] }', () => {
    expect(normalizeHomePlants({ cards: [mockPlant] })).toEqual([mockPlant])
  })

  it('returns items array from { items: [...] }', () => {
    expect(normalizeHomePlants({ items: [mockPlant] })).toEqual([mockPlant])
  })

  it('returns the value itself when it is already an array', () => {
    expect(normalizeHomePlants([mockPlant])).toEqual([mockPlant])
  })

  it('returns [] for undefined', () => {
    expect(normalizeHomePlants(undefined)).toEqual([])
  })

  it('returns [] for empty object {}', () => {
    expect(normalizeHomePlants({})).toEqual([])
  })

  it('returns [] for null', () => {
    expect(normalizeHomePlants(null)).toEqual([])
  })

  it('returns [] when plants key is undefined', () => {
    expect(normalizeHomePlants({ plants: undefined })).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// fetchHome — fallback behaviour
// ---------------------------------------------------------------------------
vi.mock('../client', () => ({
  default: { get: vi.fn() },
  DEMO_USER_ID: 'demo-user',
}))

import client, { DEMO_USER_ID } from '../client'
const mockGet = client.get as ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.clearAllMocks()
})

describe('fetchHome', () => {
  it('returns plants from /home when response contains a valid plants array', async () => {
    mockGet.mockResolvedValueOnce({ data: { user_id: 'u1', plants: [mockPlant] } })
    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('falls back to /plants when /home returns 422', async () => {
    const err422 = Object.assign(new Error('422'), { response: { status: 422 } })
    mockGet
      .mockRejectedValueOnce(err422)
      .mockResolvedValueOnce({ data: { plants: [mockPlant] } })

    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenCalledTimes(2)
  })

  it('falls back to /plants when /home returns { plants: undefined }', async () => {
    mockGet
      .mockResolvedValueOnce({ data: { plants: undefined } })
      .mockResolvedValueOnce({ data: { plants: [mockPlant] } })

    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenCalledTimes(2)
  })

  it('returns empty plants when both /home and /plants fail', async () => {
    mockGet
      .mockRejectedValueOnce(new Error('home fail'))
      .mockRejectedValueOnce(new Error('plants fail'))

    await expect(fetchHome()).rejects.toThrow('plants fail')
  })

  it('plants result is always an array (never undefined)', async () => {
    mockGet.mockResolvedValueOnce({ data: { user_id: 'u1', plants: [mockPlant] } })
    const result = await fetchHome()
    expect(Array.isArray(result.plants)).toBe(true)
  })

  it('uses DEMO_USER_ID when /home response has no user_id', async () => {
    mockGet.mockResolvedValueOnce({ data: { plants: [mockPlant] } })
    const result = await fetchHome()
    expect(result.user_id).toBe(DEMO_USER_ID)
  })
})
