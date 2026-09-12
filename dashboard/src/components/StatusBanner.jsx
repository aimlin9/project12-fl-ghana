import styles from './StatusBanner.module.css'

export default function StatusBanner({ rounds, totalRounds }) {
  const last = rounds.at(-1)
  return (
    <div className={styles.banner}>
      <span className={styles.dot} />
      <span className={`${styles.text} mono`}>
        {last
          ? `Round ${last.round} of ${totalRounds} completed · F1 ${(last.f1_score ?? 0).toFixed(3)} · Acc ${(last.accuracy ?? 0).toFixed(3)}`
          : `Simulation starting — waiting for school nodes to connect`}
      </span>
    </div>
  )
}
