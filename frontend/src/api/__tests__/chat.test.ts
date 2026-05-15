import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRequestId, sendChat } from '../chat'

vi.mock('../client', () => ({
  default: { post: vi.fn() },
  DEMO_USER_ID: '7507fdac-da23-5956-a5a4-9239de655be0',
}))

import client, { DEMO_USER_ID } from '../client'
const mockPost = client.post as ReturnType<typeof vi.fn>

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

const mockResponse = {
  data: {
    request_id: 'req',
    plant_id: 'plant-1',
    intent: 'watering_question',
    answer: { 결론: '', 근거: '', 행동: '', 주의: '' },
    guardrails_applied: [],
    prompt_hash: '',
    model_name: 'mock',
    input_tokens: 0,
    output_tokens: 0,
    from_cache: false,
    created_at: new Date().toISOString(),
    is_reference_only: false,
    diagnosis_allowed: true,
  },
}

beforeEach(() => {
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// createRequestId
// ---------------------------------------------------------------------------
describe('createRequestId', () => {
  it('uses crypto.randomUUID when available', () => {
    const original = globalThis.crypto
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: { randomUUID: () => '11111111-1111-4111-8111-111111111111' },
    })

    expect(createRequestId()).toBe('11111111-1111-4111-8111-111111111111')

    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original })
  })

  it('falls back to UUID-shaped value when crypto.randomUUID is undefined', () => {
    const original = globalThis.crypto
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {} })

    expect(createRequestId()).toMatch(UUID_RE)

    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original })
  })

  it('falls back when crypto itself is undefined', () => {
    const original = globalThis.crypto
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: undefined })

    expect(createRequestId()).toMatch(UUID_RE)

    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original })
  })

  it('always returns a non-empty string', () => {
    expect(createRequestId()).toBeTruthy()
  })

  it('fallback produces different values on successive calls', () => {
    const original = globalThis.crypto
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {} })

    const ids = new Set(Array.from({ length: 10 }, () => createRequestId()))
    expect(ids.size).toBeGreaterThan(1)

    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: original })
  })
})

// ---------------------------------------------------------------------------
// sendChat
// ---------------------------------------------------------------------------
describe('sendChat', () => {
  it('posts to the correct endpoint', async () => {
    mockPost.mockResolvedValueOnce(mockResponse)
    await sendChat('plant-1', '물 언제 줘?')
    expect(mockPost).toHaveBeenCalledWith(
      '/plants/plant-1/chat',
      expect.any(Object),
    )
  })

  it('request body contains user_id, question, and request_id', async () => {
    mockPost.mockResolvedValueOnce(mockResponse)
    await sendChat('plant-1', '물 언제 줘?')
    expect(mockPost).toHaveBeenCalledWith(
      '/plants/plant-1/chat',
      expect.objectContaining({
        user_id: DEMO_USER_ID,
        question: '물 언제 줘?',
        request_id: expect.any(String),
      }),
    )
  })

  it('request_id in body is a non-empty string', async () => {
    mockPost.mockResolvedValueOnce(mockResponse)
    await sendChat('plant-1', '물 언제 줘?')
    const body = mockPost.mock.calls[0][1]
    expect(body.request_id).toBeTruthy()
    expect(typeof body.request_id).toBe('string')
  })

  it('returns the data from the response', async () => {
    mockPost.mockResolvedValueOnce(mockResponse)
    const result = await sendChat('plant-1', '물 언제 줘?')
    expect(result).toEqual(mockResponse.data)
  })
})
