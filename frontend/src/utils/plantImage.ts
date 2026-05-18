import defaultPlant from '../assets/plants/default.png'
import monsteraDeliciosa from '../assets/plants/monstera-deliciosa.png'
import epipremnumAureum from '../assets/plants/epipremnum-aureum.png'
import philodendronHederaceum from '../assets/plants/philodendron-hederaceum.png'
import spathiphyllumWallisii from '../assets/plants/spathiphyllum-wallisii.png'
import sansevieriaTrifasciata from '../assets/plants/sansevieria-trifasciata.png'

const BY_SCIENTIFIC_NAME: Record<string, string> = {
  'monstera deliciosa':      monsteraDeliciosa,
  'epipremnum aureum':       epipremnumAureum,
  'philodendron hederaceum': philodendronHederaceum,
  'spathiphyllum wallisii':  spathiphyllumWallisii,
  'sansevieria trifasciata': sansevieriaTrifasciata,
}

const BY_KOREAN_NAME: Record<string, string> = {
  '몬스테라':           monsteraDeliciosa,
  '몬스테라 델리시오사': monsteraDeliciosa,
  '스킨답서스':         epipremnumAureum,
  '황금 스킨답서스':    epipremnumAureum,
  '필로덴드론':         philodendronHederaceum,
  '하트잎 필로덴드론':  philodendronHederaceum,
  '스파티필름':         spathiphyllumWallisii,
  '산세비에리아':       sansevieriaTrifasciata,
  '호랑이 산세비에리아': sansevieriaTrifasciata,
}

function norm(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase().replace(/\s+/g, ' ')
}

export function getPlantImageUrl(input: {
  scientificName?: string | null
  koreanName?: string | null
  speciesName?: string | null
}): string {
  const scientific = norm(input.scientificName)
  if (scientific && BY_SCIENTIFIC_NAME[scientific]) return BY_SCIENTIFIC_NAME[scientific]

  const korean = (input.koreanName ?? input.speciesName ?? '').trim()
  if (korean && BY_KOREAN_NAME[korean]) return BY_KOREAN_NAME[korean]

  return defaultPlant
}
