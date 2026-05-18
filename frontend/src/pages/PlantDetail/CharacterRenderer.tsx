import type { PlantCard } from '../../api/types'
import { getPlantImageUrl } from '../../utils/plantImage'
import styles from './PlantDetail.module.css'

const MOOD_EMOJI: Record<string, string> = {
  happy:    '😊',
  thirsty:  '🥤',
  sleepy:   '😴',
  stressed: '😰',
  neutral:  '🌿',
}

const MOOD_BG_CLASS: Record<string, string> = {
  happy:    styles.characterHappy,
  thirsty:  styles.characterThirsty,
  sleepy:   styles.characterSleepy,
  stressed: styles.characterStressed,
  neutral:  styles.characterNeutral,
}

interface Props {
  plant: PlantCard
}

export default function CharacterRenderer({ plant }: Props) {
  const mood = plant.character.mood
  const emoji = MOOD_EMOJI[mood] ?? '🌿'
  const bgCls = MOOD_BG_CLASS[mood] ?? styles.characterNeutral

  const speciesName = plant.species?.korean_name ?? null
  const room = plant.room_name ?? null
  const metaParts = [speciesName, room].filter(Boolean)
  const imageUrl = getPlantImageUrl({
    scientificName: plant.species?.scientific_name,
    koreanName: plant.species?.korean_name,
  })

  return (
    <div className={`${styles.characterCard} ${bgCls}`}>
      <div className={styles.characterImageWrap}>
        <img
          src={imageUrl}
          alt={speciesName ?? plant.nickname}
          className={styles.characterImage}
        />
        <span className={styles.characterMoodBadge} aria-hidden="true">{emoji}</span>
      </div>
      <div className={styles.characterName}>{plant.nickname}</div>
      {metaParts.length > 0 && (
        <div className={styles.characterSpecies}>{metaParts.join(' · ')}</div>
      )}
      {plant.character.status_message && (
        <div className={styles.characterMessage}>
          "{plant.character.status_message}"
        </div>
      )}
    </div>
  )
}
