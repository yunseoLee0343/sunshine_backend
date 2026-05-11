import type { ChangeEvent } from 'react'
import styles from './Onboarding.module.css'

const ROOM_OPTIONS = ['거실', '침실', '발코니', '서재', '주방', '기타']

export interface ProfileValues {
  nickname: string
  roomName: string
}

interface Props {
  values: ProfileValues
  onChange: (values: ProfileValues) => void
  errors: Partial<Record<keyof ProfileValues, string>>
}

export default function Step3Profile({ values, onChange, errors }: Props) {
  function handleNickname(e: ChangeEvent<HTMLInputElement>) {
    onChange({ ...values, nickname: e.target.value })
  }

  function handleRoom(room: string) {
    onChange({ ...values, roomName: room })
  }

  return (
    <>
      <h2 className={styles.title}>식물 프로필을 설정해 주세요</h2>
      <p className={styles.subtitle}>식물의 이름과 키울 장소를 알려주세요.</p>

      <div className={styles.form}>
        {/* Nickname */}
        <div className={styles.fieldGroup}>
          <label htmlFor="nickname" className={styles.label}>
            식물 별명 <span aria-hidden="true">*</span>
          </label>
          <input
            id="nickname"
            type="text"
            className={`${styles.input} ${errors.nickname ? styles.error : ''}`}
            value={values.nickname}
            onChange={handleNickname}
            placeholder="예: 초록이, 잎이"
            maxLength={20}
            autoComplete="off"
          />
          {errors.nickname && (
            <span className={styles.fieldError} role="alert">{errors.nickname}</span>
          )}
        </div>

        {/* Room */}
        <div className={styles.fieldGroup}>
          <span className={styles.label}>키울 장소</span>
          <div className={styles.roomGrid} role="group" aria-label="키울 장소 선택">
            {ROOM_OPTIONS.map((room) => (
              <button
                key={room}
                type="button"
                className={`${styles.roomChip} ${values.roomName === room ? styles.selectedRoom : ''}`}
                onClick={() => handleRoom(room)}
                aria-pressed={values.roomName === room}
              >
                {room}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
