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
  it('calls /home with { params: { user_id: DEMO_USER_ID } }', async () => {
    mockGet.mockResolvedValueOnce({ data: { user_id: 'u1', plants: [mockPlant] } })
    await fetchHome()
    expect(mockGet).toHaveBeenNthCalledWith(1, '/home', { params: { user_id: DEMO_USER_ID } })
  })

  it('returns plants from /home when response contains a valid plants array (no fallback)', async () => {
    mockGet.mockResolvedValueOnce({ data: { user_id: 'u1', plants: [mockPlant] } })
    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('falls back to /plants with user_id param when /home returns 500', async () => {
    const err500 = Object.assign(new Error('500'), { response: { status: 500 } })
    mockGet
      .mockRejectedValueOnce(err500)
      .mockResolvedValueOnce({ data: { plants: [mockPlant] } })

    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenNthCalledWith(2, '/plants', { params: { user_id: DEMO_USER_ID } })
  })

  it('falls back to /plants with user_id param when /home returns { plants: undefined }', async () => {
    mockGet
      .mockResolvedValueOnce({ data: { plants: undefined } })
      .mockResolvedValueOnce({ data: { plants: [mockPlant] } })

    const result = await fetchHome()
    expect(result.plants).toEqual([mockPlant])
    expect(mockGet).toHaveBeenNthCalledWith(2, '/plants', { params: { user_id: DEMO_USER_ID } })
  })

  it('rejects when both /home and /plants fail', async () => {
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
