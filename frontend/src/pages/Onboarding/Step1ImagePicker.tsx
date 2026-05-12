import { useMemo, useRef } from 'react'
import styles from './Onboarding.module.css'

interface Props {
  selectedFile: File | null
  onSelect: (file: File) => void
}

export default function Step1ImagePicker({ selectedFile, onSelect }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const previewUrl = useMemo(
    () => (selectedFile ? URL.createObjectURL(selectedFile) : null),
    [selectedFile],
  )

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onSelect(file)
  }

  return (
    <>
      <h2 className={styles.title}>식물 사진을 선택해 주세요</h2>
      <p className={styles.subtitle}>갤러리에서 선택하거나 카메라로 촬영해 주세요.</p>

      <div
        className={styles.uploadArea}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        aria-label="식물 사진 업로드"
      >
        {previewUrl ? (
          <img src={previewUrl} alt="식물 미리보기" className={styles.previewImage} />
        ) : (
          <div className={styles.uploadEmpty}>
            <span className={styles.uploadIcon} aria-hidden="true">📷</span>
            <span className={styles.uploadEmptyText}>식물 사진을 업로드해 주세요</span>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className={styles.hiddenInput}
        onChange={handleChange}
      />

      {selectedFile && (
        <button
          type="button"
          className={styles.changeImageBtn}
          onClick={() => inputRef.current?.click()}
        >
          다른 사진 선택
        </button>
      )}
    </>
  )
}
