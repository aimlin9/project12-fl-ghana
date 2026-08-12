import styles from './CompletionSummaryModal.module.css'

export default function CompletionSummaryModal({ rounds, baseline, config, clients, onClose }) {
  const last = rounds.at(-1) ?? {}
  const totalRounds = rounds.length
  const nodeNames = Object.keys(clients ?? {})
  const onlineCount = nodeNames.filter(n => clients[n].status !== 'Offline').length

  const baseF1 = baseline?.f1_score_macro
  const lastF1 = last.f1_score
  const gap = baseF1 != null && lastF1 != null ? baseF1 - lastF1 : null
  const withinTarget = gap != null && gap <= 0.05

  const totalCommMb = rounds.reduce((sum, r) => sum + (r.comm_overhead_mb ?? 0), 0)
  const maxEpsilon = Math.max(0, ...rounds.map(r => r.max_epsilon ?? 0))

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.checkIcon}>✓</span>
          <div>
            <div className={styles.title}>Simulation Complete</div>
            <div className={styles.subtitle}>
              {totalRounds} round{totalRounds === 1 ? '' : 's'} finished · {onlineCount}/{nodeNames.length} nodes participated
            </div>
          </div>
        </div>

        <div className={styles.statGrid}>
          <Stat label="Final F1 (macro)" value={lastF1?.toFixed(4) ?? '—'} accent="#6366f1" />
          <Stat label="Balanced Accuracy" value={last.accuracy != null ? `${(last.accuracy * 100).toFixed(1)}%` : '—'} accent="#a855f7" />
          <Stat label="AUC-ROC" value={last.auc_roc?.toFixed(4) ?? '—'} accent="#a855f7" />
          <Stat label="Max Privacy Budget ε" value={maxEpsilon.toFixed(3)} accent="#f59e0b" sub="worst case across nodes" />
          <Stat label="Total Comm. Overhead" value={`${totalCommMb.toFixed(2)} MB`} accent="#06b6d4" sub={`${totalRounds} round${totalRounds === 1 ? '' : 's'}, Paillier-encrypted`} />
          <Stat
            label="Config"
            value={`${config?.use_dp === 'True' ? 'DP' : 'no DP'} · ${config?.use_paillier === 'True' ? `Paillier ${config?.paillier_key_bits ?? '?'}-bit` : 'no Paillier'}`}
            accent="#10b981"
          />
        </div>

        {baseline && lastF1 != null && (
          <div className={withinTarget ? styles.targetOk : styles.targetMiss}>
            {withinTarget
              ? `✓ Within the 5pp target — federated F1 (${lastF1.toFixed(4)}) vs centralised baseline (${baseF1.toFixed(4)}), gap ${gap.toFixed(4)}`
              : `⚠ Outside the 5pp target — federated F1 (${lastF1.toFixed(4)}) vs centralised baseline (${baseF1.toFixed(4)}), gap ${gap.toFixed(4)}`}
          </div>
        )}

        <button className={styles.closeBtn} onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

function Stat({ label, value, accent, sub }) {
  return (
    <div className={styles.stat} style={{ borderLeftColor: accent }}>
      <div className={styles.statLabel}>{label}</div>
      <div className={styles.statValue} style={{ color: accent }}>{value}</div>
      {sub && <div className={styles.statSub}>{sub}</div>}
    </div>
  )
}
