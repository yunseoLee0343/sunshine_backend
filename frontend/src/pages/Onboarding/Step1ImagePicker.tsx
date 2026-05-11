import styles from './Onboarding.module.css'

interface MockImage {
  imageRef: string
  emoji: string
  labelKo: string
  hint: string
}

const MOCK_IMAGES: MockImage[] = [
  {
    imageRef: 'uploads/mock/monstera.jpg',
    emoji: '🌿',
    labelKo: '몬스테라',
    hint: '넓은 잎이 특징',
  },
  {
    imageRef: 'uploads/mock/pothos.jpg',
    emoji: '🍃',
    labelKo: '스킨답서스',
    hint: '하트 모양 잎',
  },
  {
    imageRef: 'uploads/mock/philodendron.jpg',
    emoji: '🌱',
    labelKo: '필로덴드론',
    hint: '덩굴성 관엽식물',
  },
  {
    imageRef: 'uploads/mock/unknown.jpg',
    emoji: '🪴',
    labelKo: '잘 모르겠어요',
    hint: '직접 분류해 줄게요',
  },
]

interface Props {
  selected: string | null
  onSelect: (imageRef: string) => void
}

export default function Step1ImagePicker({ selected, onSelect }: Props) {
  return (
    <>
      <h2 className={styles.title}>어떤 식물인가요?</h2>
      <p className={styles.subtitle}>식물 사진과 가장 비슷한 이미지를 선택해 주세요.</p>

      <div className={styles.imageGrid}>
        {MOCK_IMAGES.map((img) => (
          <button
            key={img.imageRef}
            type="button"
            className={`${styles.imageCard} ${selected === img.imageRef ? styles.selected : ''}`}
            onClick={() => onSelect(img.imageRef)}
            aria-pressed={selected === img.imageRef}
          >
            <span className={styles.imageEmoji} aria-hidden="true">{img.emoji}</span>
            <span className={styles.imageName}>{img.labelKo}</span>
            <span className={styles.imageHint}>{img.hint}</span>
          </button>
        ))}
      </div>
    </>
  )
}
