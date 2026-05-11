import type { SpeciesCandidateItem } from '../../api/types'
import styles from './Onboarding.module.css'

const CONFIDENCE_LABEL: Record<string, string> = {
  high: '일치율 높음',
  medium: '일치율 보통',
  low: '일치율 낮음',
}

const CONFIDENCE_CLASS: Record<string, string> = {
  high: styles.confidenceHigh,
  medium: styles.confidenceMedium,
  low: styles.confidenceLow,
}

interface Props {
  candidates: SpeciesCandidateItem[]
  selected: SpeciesCandidateItem | null
  onSelect: (candidate: SpeciesCandidateItem) => void
}

export default function Step2Candidates({ candidates, selected, onSelect }: Props) {
  return (
    <>
      <h2 className={styles.title}>어떤 식물인지 확인해 주세요</h2>
      <p className={styles.subtitle}>AI가 분석한 후보 식물들입니다. 정확한 종을 선택해 주세요.</p>

      <div className={styles.candidateList}>
        {candidates.map((c, i) => {
          const isSelected =
            selected !== null &&
            selected.species_profile_id === c.species_profile_id &&
            selected.label_ko === c.label_ko

          return (
            <button
              key={c.species_profile_id ?? `${c.label_en}-${i}`}
              type="button"
              className={`${styles.candidateCard} ${isSelected ? styles.selected : ''}`}
              onClick={() => onSelect(c)}
              aria-pressed={isSelected}
            >
              <div className={styles.candidateInfo}>
                <span className={styles.candidateName}>{c.label_ko}</span>
                {c.scientific_name && (
                  <span className={styles.candidateScientific}>{c.scientific_name}</span>
                )}
              </div>
              <span
                className={`${styles.confidenceBadge} ${CONFIDENCE_CLASS[c.confidence_label] ?? styles.confidenceMedium}`}
              >
                {CONFIDENCE_LABEL[c.confidence_label] ?? c.confidence_label}
              </span>
            </button>
          )
        })}
      </div>
    </>
  )
}
