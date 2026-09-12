import styles from './MetricCards.module.css'

function Card({ label, value, sub, tone = 'neutral' }) {
  return (
    <div className={`${styles.card} ${styles[tone]}`}>
      <div className={styles.label}>{label}</div>
      <div className={`${styles.value} mono`}>{value}</div>
      {sub && <div className={styles.sub}>{sub}</div>}
    </div>
  )
}

export default function MetricCards({ rounds, last, clients, config, liveAccuracy, running }) {
  const totalRounds    = rounds.length
  const hasRounds      = totalRounds > 0
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
      />
      <Card
        label="F1-Score (macro)"
        value={last.f1_score != null ? last.f1_score.toFixed(4) : '—'}
        sub="federated global model"
        tone="accent"
      />
      <Card
        label="Balanced Accuracy"
        value={
          running && hasRounds && liveAccuracy != null
            ? (liveAccuracy * 100).toFixed(1) + '%'
            : last.accuracy != null ? (last.accuracy * 100).toFixed(1) + '%' : '—'
        }
        sub={running && hasRounds && liveAccuracy != null ? 'training in progress' : `AUC: ${last.auc_roc != null ? last.auc_roc.toFixed(3) : '—'}`}
      />
      <Card
        label="Privacy Budget ε"
        value={last.max_epsilon != null ? last.max_epsilon.toFixed(3) : '—'}
        sub="max across clients (δ=1e-5)"
        tone="accent"
      />
      <Card
        label="Comm. Overhead"
        value={last.comm_overhead_mb != null ? last.comm_overhead_mb.toFixed(2) + ' MB' : '—'}
        sub="per round, Paillier-encrypted"
      />
      <Card
        label="School Nodes"
        value={`${idleClients + activeClients} / ${Object.keys(clients).length}`}
        sub={offlineClients > 0 ? `${offlineClients} offline` : 'all connected'}
        tone={offlineClients > 0 ? 'danger' : 'success'}
      />
    </div>
  )
}
