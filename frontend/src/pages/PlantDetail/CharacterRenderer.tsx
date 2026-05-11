import type { PlantCard } from '../../api/types'
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

  return (
    <div className={`${styles.characterCard} ${bgCls}`}>
      <div className={styles.characterEmoji} aria-hidden="true">{emoji}</div>
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
