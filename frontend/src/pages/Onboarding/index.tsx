import { useState } from 'react'
import { createPlant, fetchSpeciesCandidates } from '../../api/onboarding'
import type { PlantCard, SpeciesCandidateItem } from '../../api/types'
import Loading from '../../components/Loading'
import styles from './Onboarding.module.css'
import Step1ImagePicker from './Step1ImagePicker'
import Step2Candidates from './Step2Candidates'
import Step3Profile, { type ProfileValues } from './Step3Profile'
import Step4Success from './Step4Success'

type Step = 1 | 2 | 3 | 4

const STEP_LABELS = ['사진 선택', '종 확인', '프로필', '완료']

// ---------------------------------------------------------------------------
// Progress indicator
// ---------------------------------------------------------------------------

function ProgressBar({ current }: { current: Step }) {
  return (
    <div className={styles.progress} aria-label="온보딩 진행 단계">
      {STEP_LABELS.map((label, i) => {
        const stepNum = (i + 1) as Step
        const state =
          stepNum < current ? 'done' : stepNum === current ? 'active' : ''
        return (
          <div key={label} className={`${styles.step} ${state}`}>
            <div className={styles.dot}>
              {stepNum < current ? '✓' : stepNum}
            </div>
            <span className={styles.stepLabel}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main orchestrator
// ---------------------------------------------------------------------------

export default function Onboarding() {
  const [step, setStep] = useState<Step>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Step 1
  const [selectedImageRef, setSelectedImageRef] = useState<string | null>(null)

  // Step 2
  const [candidates, setCandidates] = useState<SpeciesCandidateItem[]>([])
  const [selectedCandidate, setSelectedCandidate] = useState<SpeciesCandidateItem | null>(null)

  // Step 3
  const [profile, setProfile] = useState<ProfileValues>({ nickname: '', roomName: '거실' })
  const [profileErrors, setProfileErrors] = useState<Partial<Record<keyof ProfileValues, string>>>({})

  // Step 4
  const [createdPlant, setCreatedPlant] = useState<PlantCard | null>(null)

  // ------------------------------------------------------------------
  // Navigation helpers
  // ------------------------------------------------------------------

  function back() {
    setError(null)
    setStep((s) => (s > 1 ? ((s - 1) as Step) : s))
  }

  // Step 1 → 2: call species-candidates API
  async function advanceFromStep1() {
    if (!selectedImageRef) return
    setError(null)
    setLoading(true)
    try {
      const res = await fetchSpeciesCandidates(selectedImageRef)
      setCandidates(res.candidates)
      // Auto-select the first registerable candidate; skip null-profile fallbacks
      setSelectedCandidate(res.candidates.find((c) => c.species_profile_id != null) ?? null)
      setStep(2)
    } catch {
      setError('종 후보 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  // Step 2 → 3
  function advanceFromStep2() {
    if (!selectedCandidate) return
    setStep(3)
  }

  // Step 3 → 4: call create-plant API
  async function advanceFromStep3() {
    const errors: Partial<Record<keyof ProfileValues, string>> = {}
    if (!profile.nickname.trim()) {
      errors.nickname = '별명을 입력해 주세요.'
    } else if (profile.nickname.trim().length > 20) {
      errors.nickname = '별명은 최대 20자까지 가능해요.'
    }
    if (Object.keys(errors).length > 0) {
      setProfileErrors(errors)
      return
    }
    setProfileErrors({})

    if (!selectedCandidate?.species_profile_id) {
      setError('선택된 식물의 종 정보가 없어요. 이전 단계로 돌아가 다시 선택해 주세요.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      const res = await createPlant({
        species_profile_id: selectedCandidate.species_profile_id,
        nickname: profile.nickname.trim(),
        room_name: profile.roomName,
      })
      setCreatedPlant(res.plant)
      setStep(4)
    } catch {
      setError('식물 등록에 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  function handleNext() {
    if (step === 1) advanceFromStep1()
    else if (step === 2) advanceFromStep2()
    else if (step === 3) advanceFromStep3()
  }

  // ------------------------------------------------------------------
  // Next button state
  // ------------------------------------------------------------------

  const nextDisabled =
    (step === 1 && !selectedImageRef) ||
    (step === 2 && (!selectedCandidate || !selectedCandidate.species_profile_id)) ||
    loading

  const nextLabel =
    step === 1 ? '종 분석하기' :
    step === 2 ? '이 식물이 맞아요' :
    step === 3 ? '등록 완료' : ''

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <div className={styles.container}>
      {/* Progress bar is hidden on the success step */}
      {step < 4 && <ProgressBar current={step} />}

      {/* Error banner */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          {error}
        </div>
      )}

      {/* Step content */}
      {loading ? (
        <Loading message={step === 1 ? '식물 종을 분석하는 중...' : '식물을 등록하는 중...'} />
      ) : (
        <>
          {step === 1 && (
            <Step1ImagePicker
              selected={selectedImageRef}
              onSelect={setSelectedImageRef}
            />
          )}
          {step === 2 && (
            <Step2Candidates
              candidates={candidates}
              selected={selectedCandidate}
              onSelect={setSelectedCandidate}
            />
          )}
          {step === 3 && (
            <Step3Profile
              values={profile}
              onChange={(v) => { setProfile(v); setProfileErrors({}) }}
              errors={profileErrors}
            />
          )}
          {step === 4 && createdPlant && (
            <Step4Success plant={createdPlant} />
          )}
        </>
      )}

      {/* Navigation bar — hidden on loading and success step */}
      {!loading && step < 4 && (
        <div className={`${styles.navBar} ${step > 1 ? styles.hasBack : ''}`}>
          {step > 1 && (
            <button type="button" className={styles.btnBack} onClick={back}>
              이전
            </button>
          )}
          <button
            type="button"
            className={styles.btnNext}
            onClick={handleNext}
            disabled={nextDisabled}
          >
            {nextLabel}
          </button>
        </div>
      )}
    </div>
  )
}
