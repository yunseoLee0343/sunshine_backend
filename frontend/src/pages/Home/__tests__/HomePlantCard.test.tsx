import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HomePlantCard from '../HomePlantCard'
import type { PlantHomeCard } from '../../../api/types'

vi.mock('../../../utils/plantImage', () => ({
  getPlantImageUrl: vi.fn(() => 'mocked-plant.png'),
}))

const basePlant: PlantHomeCard = {
  plant_id: 'abc-123',
  nickname: '몬이',
  room_name: '거실',
  species_name: '몬스테라',
  character: {
    mood: 'happy',
    expression: 'smile',
    status_message: '행복해요!',
    primary_action: 'none',
    reason_code: 'ok',
  },
  environment: null,
  today_recommended_action: 'none',
  care_status: 'good',
}

function renderCard(plant: PlantHomeCard = basePlant) {
  return render(
    <MemoryRouter>
      <HomePlantCard plant={plant} />
    </MemoryRouter>,
  )
}

describe('HomePlantCard', () => {
  it('renders plant nickname', () => {
    renderCard()
    expect(screen.getByText('몬이')).toBeTruthy()
  })

  it('renders species and room in meta', () => {
    renderCard()
    expect(screen.getByText('몬스테라 · 거실')).toBeTruthy()
  })

  it('renders status message', () => {
    renderCard()
    expect(screen.getByText('"행복해요!"')).toBeTruthy()
  })

  it('renders plant image with correct src from getPlantImageUrl', () => {
    renderCard()
    const img = screen.getByRole('img')
    expect(img.getAttribute('src')).toBe('mocked-plant.png')
  })

  it('renders mood badge emoji for happy mood', () => {
    renderCard()
    expect(screen.getByText('😊')).toBeTruthy()
  })

  it('does not render action banner when action is none', () => {
    renderCard()
    expect(screen.queryByText('오늘은 괜찮아요')).toBeNull()
  })

  it('renders action banner when action is water', () => {
    renderCard({ ...basePlant, today_recommended_action: 'water' })
    expect(screen.getByText('물 줄 시간이에요!')).toBeTruthy()
  })

  it('renders care status pill', () => {
    renderCard()
    expect(screen.getByText('양호')).toBeTruthy()
  })

  it('renders sensor badges when environment data present', () => {
    renderCard({
      ...basePlant,
      environment: {
        soil_moisture_avg_pct: 42,
        light_avg_lux: 500,
        humidity_avg_pct: 60,
        temperature_avg_c: 22,
      },
    })
    expect(screen.getByText('42% 수분')).toBeTruthy()
    expect(screen.getByText('22°C')).toBeTruthy()
  })

  it('links to plant detail page', () => {
    renderCard()
    const link = screen.getByRole('link')
    expect(link.getAttribute('href')).toBe('/plants/abc-123')
  })
})
