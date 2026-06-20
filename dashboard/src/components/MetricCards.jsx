import styles from './MetricCards.module.css'

function Card({ label, value, sub, color }) {
  return (
    <div className={styles.card} style={{ '--accent': color }}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>{value}</div>
      {sub && <div className={styles.sub}>{sub}</div>}
    </div>
  )
}

export default function MetricCards({ rounds, last, clients, config }) {
  const totalRounds    = rounds.length
  const configRounds   = config?.total_rounds ?? 50
  const activeClients  = Object.values(clients).filter(c => c.status === 'Active').length
  const idleClients    = Object.values(clients).filter(c => c.status === 'Idle').length
  const offlineClients = Object.values(clients).filter(c => c.status === 'Offline').length

  return (
    <div className={styles.grid}>
      <Card
        label="Current Round"
        value={totalRounds > 0 ? totalRounds : '—'}
        sub={`of ${configRounds} total rounds`}
        color="#6366f1"
      />
      <Card
        label="F1-Score (macro)"
        value={last.f1_score != null ? last.f1_score.toFixed(4) : '—'}
        sub="federated global model"
        color="#10b981"
      />
      <Card
        label="Accuracy"
        value={last.accuracy != null ? (last.accuracy * 100).toFixed(1) + '%' : '—'}
        sub={`AUC: ${last.auc_roc != null ? last.auc_roc.toFixed(3) : '—'}`}
        color="#a855f7"
      />
      <Card
        label="Privacy Budget ε"
        value={last.max_epsilon != null ? last.max_epsilon.toFixed(3) : '—'}
        sub="max across clients (δ=1e-5)"
        color="#f59e0b"
      />
      <Card
        label="Comm. Overhead"
        value={last.comm_overhead_mb != null ? last.comm_overhead_mb.toFixed(2) + ' MB' : '—'}
        sub="per round (Paillier encrypted)"
        color="#06b6d4"
      />
      <Card
        label="School Nodes"
        value={`${idleClients + activeClients} / ${Object.keys(clients).length}`}
        sub={`${offlineClients} offline`}
        color={offlineClients > 0 ? '#ef4444' : '#10b981'}
      />
    </div>
  )
}
