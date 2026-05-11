import styles from './Chat.module.css'

export default function PestCautionBanner() {
  return (
    <div className={styles.pestBanner} role="alert">
      <span className={styles.pestBannerIcon}>⚠️</span>
      <div className={styles.pestBannerText}>
        <div className={styles.pestBannerTitle}>병충해 참고 정보</div>
        이 답변은 일반 참고용입니다. 정확한 진단은 전문가에게 문의해 주세요.
      </div>
    </div>
  )
}
