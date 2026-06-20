import styles from './ClientStatusCard.module.css'

const STATUS_COLOR = {
  Active:  '#10b981',
  Idle:    '#6366f1',
  Offline: '#ef4444',
  Failed:  '#f59e0b',
}

const STATUS_BG = {
  Active:  'rgba(16,185,129,0.12)',
  Idle:    'rgba(99,102,241,0.12)',
  Offline: 'rgba(239,68,68,0.12)',
  Failed:  'rgba(245,158,11,0.12)',
}

export default function ClientStatusCard({ name, info, rounds, onToggle }) {
  const { status, last_active, last_latency, last_epsilon } = info
  const color = STATUS_COLOR[status] ?? '#9ca3af'
  const bg    = STATUS_BG[status]    ?? 'rgba(156,163,175,0.1)'
  const label = name.replace('school_', 'School ').replace(/^\w/, c => c.toUpperCase())
  const isOffline = status === 'Offline'

  return (
    <div className={styles.card} style={{ '--c': color, '--bg': bg }}>
      <div className={styles.top}>
        <div>
          <div className={styles.name}>{label}</div>
          <div className={styles.nodeId}>{name}</div>
        </div>
        <div className={styles.badge} style={{ background: bg, color, borderColor: `${color}40` }}>
          <span className={styles.dot} style={{ background: color }} />
          {status}
        </div>
      </div>

      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Last Active</span>
          <span className={styles.statVal}>{last_active || '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Round Latency</span>
          <span className={styles.statVal}>{last_latency ? `${last_latency.toFixed(2)}s` : '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Privacy ε</span>
          <span className={styles.statVal}>{last_epsilon ? last_epsilon.toFixed(4) : '—'}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>Rounds</span>
          <span className={styles.statVal}>{rounds.length}</span>
        </div>
      </div>

      {isOffline && (
        <div className={styles.offlineNote}>
          OFFLINE — update queued for next round
        </div>
      )}

      <button
        className={isOffline ? styles.btnOnline : styles.btnOffline}
        onClick={onToggle}
      >
        {isOffline ? 'Bring Online' : 'Simulate Offline'}
      </button>
    </div>
  )
}
