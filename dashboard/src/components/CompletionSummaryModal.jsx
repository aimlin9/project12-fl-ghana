import styles from './CompletionSummaryModal.module.css'

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8.5l3.2 3.2L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

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
          <span className={styles.checkIcon}><CheckIcon /></span>
          <div>
            <div className={styles.title}>Simulation complete</div>
            <div className={styles.subtitle}>
              {totalRounds} round{totalRounds === 1 ? '' : 's'} finished · {onlineCount}/{nodeNames.length} nodes participated
            </div>
          </div>
        </div>

        <div className={styles.statGrid}>
          <Stat label="Final F1 (macro)" value={lastF1?.toFixed(4) ?? '—'} tone="accent" />
          <Stat label="Balanced accuracy" value={last.accuracy != null ? `${(last.accuracy * 100).toFixed(1)}%` : '—'} />
          <Stat label="AUC-ROC" value={last.auc_roc?.toFixed(4) ?? '—'} />
          <Stat label="Max privacy budget ε" value={maxEpsilon.toFixed(3)} tone="accent" sub="worst case across nodes" />
          <Stat label="Total comm. overhead" value={`${totalCommMb.toFixed(2)} MB`} sub={`${totalRounds} round${totalRounds === 1 ? '' : 's'}, Paillier-encrypted`} />
          <Stat
            label="Config"
            value={`${config?.use_dp === 'True' ? 'DP' : 'no DP'} · ${config?.use_paillier === 'True' ? `Paillier ${config?.paillier_key_bits ?? '?'}-bit` : 'no Paillier'}`}
            tone="success"
          />
        </div>

        {baseline && lastF1 != null && (
          <div className={withinTarget ? styles.targetOk : styles.targetMiss}>
            {withinTarget
              ? `Within the 5pp target — federated F1 (${lastF1.toFixed(4)}) vs centralised baseline (${baseF1.toFixed(4)}), gap ${gap.toFixed(4)}`
              : `Outside the 5pp target — federated F1 (${lastF1.toFixed(4)}) vs centralised baseline (${baseF1.toFixed(4)}), gap ${gap.toFixed(4)}`}
          </div>
        )}

        <button className={styles.closeBtn} onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

function Stat({ label, value, tone = 'neutral', sub }) {
  return (
    <div className={`${styles.stat} ${styles[tone]}`}>
      <div className={styles.statLabel}>{label}</div>
      <div className={`${styles.statValue} mono`}>{value}</div>
      {sub && <div className={styles.statSub}>{sub}</div>}
    </div>
  )
}
