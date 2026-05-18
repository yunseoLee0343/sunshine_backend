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
          const isRegisterable = !!c.species_profile_id
          const isSelected =
            isRegisterable &&
            selected !== null &&
            selected.species_profile_id === c.species_profile_id &&
            selected.label_ko === c.label_ko

          // Prefer catalog-resolved name over raw classifier label
          const displayName = c.display_name ?? c.label_ko

          return (
            <button
              key={c.species_profile_id ?? `${c.label_en}-${i}`}
              type="button"
              className={`${styles.candidateCard} ${isSelected ? styles.selected : ''}`}
              onClick={() => { if (isRegisterable) onSelect(c) }}
              disabled={!isRegisterable}
              aria-pressed={isRegisterable ? isSelected : undefined}
            >
              <div className={styles.candidateInfo}>
                <span className={styles.candidateName}>{displayName}</span>
                {c.scientific_name && (
                  <span className={styles.candidateScientific}>{c.scientific_name}</span>
                )}
                <span className={c.catalog_matched ? styles.catalogMatched : styles.catalogUnmatched}>
                  {c.catalog_matched ? '카탈로그 일치' : '미일치'}
                  {c.source && ` · ${c.source}`}
                  {c.match_reason && ` · ${c.match_reason}`}
                </span>
                {!isRegisterable && (
                  <span className={styles.candidateUnavailable}>
                    카탈로그에 등록되지 않은 후보입니다. 다른 후보를 선택해 주세요.
                  </span>
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
