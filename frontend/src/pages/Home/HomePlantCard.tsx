import { Link } from 'react-router-dom'
import type { PlantHomeCard } from '../../api/types'
import { getPlantImageUrl } from '../../utils/plantImage'
import styles from './Home.module.css'

// ---------------------------------------------------------------------------
// Mood → emoji + avatar CSS class
// ---------------------------------------------------------------------------

const MOOD_EMOJI: Record<string, string> = {
  happy:    '😊',
  thirsty:  '🥤',
  sleepy:   '😴',
  stressed: '😰',
  neutral:  '🌿',
}

const MOOD_AVATAR_CLASS: Record<string, string> = {
  happy:    styles.avatarHappy,
  thirsty:  styles.avatarThirsty,
  sleepy:   styles.avatarSleepy,
  stressed: styles.avatarStressed,
  neutral:  styles.avatarNeutral,
}

// ---------------------------------------------------------------------------
// Care status → label + CSS class
// ---------------------------------------------------------------------------

const CARE_LABEL: Record<string, string> = {
  good:              '양호',
  needs_action:      '관리 필요',
  watch:             '주의 관찰',
  insufficient_data: '데이터 부족',
}

const CARE_CLASS: Record<string, string> = {
  good:              styles.careGood,
  needs_action:      styles.careAction,
  watch:             styles.careWatch,
  insufficient_data: styles.careInsufficient,
}

// ---------------------------------------------------------------------------
// Today action → Korean label + CSS class
// ---------------------------------------------------------------------------

interface ActionInfo { label: string; cls: string }

const ACTION_INFO: Record<string, ActionInfo> = {
  water:                { label: '물 줄 시간이에요!',     cls: styles.actionWater },
  increase_light:       { label: '빛이 부족해요',          cls: styles.actionLight },
  move_to_brighter_place: { label: '더 밝은 곳으로 옮겨줘요', cls: styles.actionLight },
  stabilize_humidity:   { label: '습도를 조절해 주세요',   cls: styles.actionHumidity },
  adjust_temperature:   { label: '온도를 확인해 주세요',   cls: styles.actionDefault },
  watch:                { label: '상태를 지켜봐요',        cls: styles.actionDefault },
  none:                 { label: '오늘은 괜찮아요',        cls: styles.actionDefault },
}

function getActionInfo(action: string): ActionInfo {
  return ACTION_INFO[action] ?? { label: action, cls: styles.actionDefault }
}

// ---------------------------------------------------------------------------
// Sensor badge helpers
// ---------------------------------------------------------------------------

function fmt(val: number | null | undefined, unit: string): string | null {
  if (val == null) return null
  return `${Math.round(val)}${unit}`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  plant: PlantHomeCard
}

export default function HomePlantCard({ plant }: Props) {
  const mood = plant.character.mood
  const emoji = MOOD_EMOJI[mood] ?? '🌿'
  const avatarCls = MOOD_AVATAR_CLASS[mood] ?? styles.avatarNeutral
  const imageUrl = getPlantImageUrl({ speciesName: plant.species_name })

  const careLabelText = CARE_LABEL[plant.care_status] ?? plant.care_status
  const careCls = CARE_CLASS[plant.care_status] ?? styles.careInsufficient

  const action = getActionInfo(plant.today_recommended_action)

  const env = plant.environment
  const badges: string[] = [
    fmt(env?.soil_moisture_avg_pct, '% 수분'),
    fmt(env?.temperature_avg_c,     '°C'),
    fmt(env?.humidity_avg_pct,      '% 습도'),
    fmt(env?.light_avg_lux,         ' lux'),
  ].filter((v): v is string => v !== null)

  return (
    <Link to={`/plants/${plant.plant_id}`} className={styles.card}>
      <div className={styles.cardTop}>
        <div className={`${styles.avatar} ${avatarCls}`}>
          <img
            src={imageUrl}
            alt={plant.species_name ?? plant.nickname}
            className={styles.plantImage}
          />
          <span className={styles.moodBadge} aria-hidden="true">{emoji}</span>
        </div>
        <div className={styles.cardInfo}>
          <div className={styles.cardName}>{plant.nickname}</div>
          <div className={styles.cardMeta}>
            {[plant.species_name, plant.room_name].filter(Boolean).join(' · ')}
          </div>
          <div className={styles.statusMsg}>
            "{plant.character.status_message}"
          </div>
        </div>
        <span className={`${styles.careStatus} ${careCls}`}>
          {careLabelText}
        </span>
      </div>

      {plant.today_recommended_action !== 'none' && (
        <div className={`${styles.actionBanner} ${action.cls}`}>
          {action.label}
        </div>
      )}

      {badges.length > 0 && (
        <div className={styles.envRow}>
          {badges.map((b) => (
            <span key={b} className={styles.envBadge}>{b}</span>
          ))}
        </div>
      )}
    </Link>
  )
}
