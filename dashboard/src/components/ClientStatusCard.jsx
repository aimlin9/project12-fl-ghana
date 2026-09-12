import styles from './ClientStatusCard.module.css'

const STATUS_TONE = {
  Active:  'success',
  Idle:    'neutral',
  Offline: 'danger',
  Failed:  'accent',
}

export default function ClientStatusCard({ name, info, rounds, onToggle }) {
  const { status, last_active, last_latency, last_epsilon } = info
  const tone = STATUS_TONE[status] ?? 'neutral'
  const label = name.replace('school_', 'School ').replace(/^\w/, c => c.toUpperCase())
  const isOffline = status === 'Offline'

  return (
    <div className={`${styles.card} ${styles[tone]}`}>
      <div className={styles.top}>
        <div className={styles.identity}>
          <div className={styles.name}>{label}</div>
          <div className={`${styles.nodeId} mono`}>{name}</div>
        </div>
        <div className={styles.tag}>
          <span className={styles.dot} />
          {status}
        </div>
      </div>

      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Last active</span>
          <span className={`${styles.statVal} mono`}>{last_active || '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Round latency</span>
          <span className={`${styles.statVal} mono`}>{last_latency ? `${last_latency.toFixed(2)}s` : '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Privacy ε</span>
          <span className={`${styles.statVal} mono`}>{last_epsilon ? last_epsilon.toFixed(4) : '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Rounds</span>
          <span className={`${styles.statVal} mono`}>{rounds.length}</span>
        </div>
      </div>

      {isOffline && (
        <div className={styles.offlineNote}>
          Offline — update queued for next round
        </div>
      )}

      <button
        className={isOffline ? styles.btnOnline : styles.btnOffline}
        onClick={onToggle}
      >
        {isOffline ? 'Bring online' : 'Simulate offline'}
      </button>
    </div>
  )
}
