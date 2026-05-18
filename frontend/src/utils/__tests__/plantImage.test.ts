import { describe, it, expect, vi } from 'vitest'

vi.mock('../../assets/plants/default.png', () => ({ default: 'default.png' }))
vi.mock('../../assets/plants/monstera-deliciosa.png', () => ({ default: 'monstera-deliciosa.png' }))
vi.mock('../../assets/plants/epipremnum-aureum.png', () => ({ default: 'epipremnum-aureum.png' }))
vi.mock('../../assets/plants/philodendron-hederaceum.png', () => ({ default: 'philodendron-hederaceum.png' }))
vi.mock('../../assets/plants/spathiphyllum-wallisii.png', () => ({ default: 'spathiphyllum-wallisii.png' }))
vi.mock('../../assets/plants/sansevieria-trifasciata.png', () => ({ default: 'sansevieria-trifasciata.png' }))

import { getPlantImageUrl } from '../plantImage'

describe('getPlantImageUrl', () => {
  it('resolves by scientific name (lowercase, trimmed)', () => {
    expect(getPlantImageUrl({ scientificName: 'Monstera deliciosa' })).toBe('monstera-deliciosa.png')
  })

  it('resolves by scientific name with extra whitespace', () => {
    expect(getPlantImageUrl({ scientificName: '  epipremnum  aureum  ' })).toBe('epipremnum-aureum.png')
  })

  it('scientific name takes priority over korean name', () => {
    expect(getPlantImageUrl({ scientificName: 'spathiphyllum wallisii', koreanName: '산세비에리아' }))
      .toBe('spathiphyllum-wallisii.png')
  })

  it('resolves by korean name when scientific name absent', () => {
    expect(getPlantImageUrl({ koreanName: '몬스테라' })).toBe('monstera-deliciosa.png')
  })

  it('resolves by speciesName (korean) fallback', () => {
    expect(getPlantImageUrl({ speciesName: '스킨답서스' })).toBe('epipremnum-aureum.png')
  })

  it('koreanName takes priority over speciesName', () => {
    expect(getPlantImageUrl({ koreanName: '산세비에리아', speciesName: '몬스테라' }))
      .toBe('sansevieria-trifasciata.png')
  })

  it('returns default for unknown scientific name', () => {
    expect(getPlantImageUrl({ scientificName: 'unknown plant' })).toBe('default.png')
  })

  it('returns default for unknown korean name', () => {
    expect(getPlantImageUrl({ koreanName: '알 수 없는 식물' })).toBe('default.png')
  })

  it('returns default when all inputs are null', () => {
    expect(getPlantImageUrl({ scientificName: null, koreanName: null, speciesName: null })).toBe('default.png')
  })

  it('returns default when all inputs are undefined', () => {
    expect(getPlantImageUrl({})).toBe('default.png')
  })

  it('resolves 호랑이 산세비에리아 alias', () => {
    expect(getPlantImageUrl({ koreanName: '호랑이 산세비에리아' })).toBe('sansevieria-trifasciata.png')
  })

  it('resolves 하트잎 필로덴드론 alias', () => {
    expect(getPlantImageUrl({ koreanName: '하트잎 필로덴드론' })).toBe('philodendron-hederaceum.png')
  })

  it('resolves 황금 스킨답서스 alias', () => {
    expect(getPlantImageUrl({ koreanName: '황금 스킨답서스' })).toBe('epipremnum-aureum.png')
  })

  it('resolves 몬스테라 델리시오사 alias', () => {
    expect(getPlantImageUrl({ koreanName: '몬스테라 델리시오사' })).toBe('monstera-deliciosa.png')
  })
})
