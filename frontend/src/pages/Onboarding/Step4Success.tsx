import { useNavigate } from 'react-router-dom'
import type { PlantCard } from '../../api/types'
import { getPlantImageUrl } from '../../utils/plantImage'
import styles from './Onboarding.module.css'

interface Props {
  plant: PlantCard
}

export default function Step4Success({ plant }: Props) {
  const navigate = useNavigate()

  const speciesName = plant.species?.korean_name ?? '알 수 없는 식물'
  const room = plant.room_name ?? '장소 미지정'
  const imageUrl = getPlantImageUrl({
    scientificName: plant.species?.scientific_name,
    koreanName: plant.species?.korean_name,
  })

  return (
    <>
      <h2 className={styles.title}>등록 완료!</h2>
      <p className={styles.subtitle}>새 식물 친구가 생겼어요 🎉</p>

      <div className={styles.successCard}>
        <div className={styles.successImageWrap}>
          <img
            src={imageUrl}
            alt={speciesName}
            className={styles.successPlantImg}
          />
        </div>
        <div className={styles.successName}>{plant.nickname}</div>
        <div className={styles.successMeta}>
          {speciesName} · {room}
        </div>
        {plant.character.status_message && (
          <div className={styles.successMessage}>
            "{plant.character.status_message}"
          </div>
        )}
      </div>

      <div className={styles.navBar}>
        <button
          type="button"
          className={styles.btnNext}
          onClick={() => navigate('/', { replace: true })}
        >
          홈으로 가기
        </button>
      </div>
    </>
  )
}
