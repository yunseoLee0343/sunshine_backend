import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Home from '../index'

vi.mock('../../../api/home', () => ({
  fetchHome: vi.fn(),
}))

import { fetchHome } from '../../../api/home'
const mockFetchHome = fetchHome as ReturnType<typeof vi.fn>

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

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Home page', () => {
  it('renders without throwing on initial mount', () => {
    mockFetchHome.mockResolvedValueOnce({ user_id: 'u1', plants: [] })
    expect(() => renderHome()).not.toThrow()
  })

  it('renders plant cards when fetchHome returns { plants: [...] }', async () => {
    mockFetchHome.mockResolvedValueOnce({ user_id: 'u1', plants: [mockPlant] })
    renderHome()
    await waitFor(() => expect(screen.getByText('초록이')).toBeInTheDocument())
  })

  it('renders empty state (not a crash) when plants is undefined in response', async () => {
    mockFetchHome.mockResolvedValueOnce({ user_id: 'u1', plants: undefined })
    renderHome()
    await waitFor(() =>
      expect(screen.getByText('아직 등록된 식물이 없어요')).toBeInTheDocument(),
    )
  })

  it('renders cards when response uses cards key', async () => {
    mockFetchHome.mockResolvedValueOnce({ user_id: 'u1', plants: [mockPlant] })
    renderHome()
    await waitFor(() => expect(screen.getByText('초록이')).toBeInTheDocument())
  })

  it('renders error state without crashing when fetchHome rejects', async () => {
    mockFetchHome.mockRejectedValueOnce(new Error('network error'))
    renderHome()
    await waitFor(() =>
      expect(screen.getByText('식물 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')).toBeInTheDocument(),
    )
  })

  it('plants state is never undefined — empty state shown instead of crash', async () => {
    mockFetchHome.mockResolvedValueOnce({ user_id: 'u1', plants: undefined })
    let caughtError: Error | null = null
    try {
      renderHome()
      await waitFor(() => expect(screen.queryByText('식물 목록을 불러오는 중...')).not.toBeInTheDocument())
    } catch (e: any) {
      caughtError = e
    }
    expect(caughtError).toBeNull()
  })
})
