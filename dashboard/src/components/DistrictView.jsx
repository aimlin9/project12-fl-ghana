import { useState, useEffect } from 'react'
import MetricCards from './MetricCards.jsx'
import ConvergenceChart from './ConvergenceChart.jsx'
import CommOverheadChart from './CommOverheadChart.jsx'
import PrivacyAccuracyScatter from './PrivacyAccuracyScatter.jsx'
import { fetchBaseline } from '../api.js'
import styles from './DistrictView.module.css'

export default function DistrictView({ telemetry, onStart, running }) {
  const rounds  = telemetry?.rounds ?? []
  const clients = telemetry?.clients ?? {}
  const config  = telemetry?.config ?? {}
  const last    = rounds.at(-1) ?? {}

  const [baseline, setBaseline] = useState(null)

  useEffect(() => {
    fetchBaseline().then(b => setBaseline(b))
  }, [])

  const lastF1 = last.f1_score
  const baseF1 = baseline?.f1_score_macro
  const withinTarget = lastF1 != null && baseF1 != null && (baseF1 - lastF1) <= 0.05

  return (
    <div className={styles.grid}>

      {/* Top control bar */}
      <div className={styles.controlBar}>
        <div className={styles.controlLeft}>
          <span className={styles.viewLabel}>District Officer View</span>
          {baseline && (
            <span className={styles.baselineBadge}>
              Centralised baseline — F1: <strong>{baseF1.toFixed(4)}</strong>
              {' '}| Acc: <strong>{baseline.accuracy.toFixed(4)}</strong>
              {' '}| AUC: <strong>{baseline.auc_roc.toFixed(4)}</strong>
              {lastF1 != null && (
                <span className={withinTarget ? styles.withinTarget : styles.belowTarget}>
                  {withinTarget ? '  ✓ Within 5 pp target' : `  Δ ${(baseF1 - lastF1).toFixed(4)} from baseline`}
                </span>
              )}
            </span>
          )}
          {!baseline && (
            <span className={styles.baselineMissing}>
              No baseline — run <code>python scripts/train_baseline.py</code>
            </span>
          )}
        </div>
        <button
          className={running ? styles.startBtnRunning : styles.startBtn}
          onClick={onStart}
          disabled={running}
        >
          {running ? '● Simulation Running…' : '▶  Start FL Simulation'}
        </button>
      </div>

      <MetricCards rounds={rounds} last={last} clients={clients} config={config} />

      <div className={styles.row}>
        <div className={styles.chartLarge}>
          <ConvergenceChart rounds={rounds} baseline={baseline} />
        </div>
        <div className={styles.chartSmall}>
          <CommOverheadChart rounds={rounds} />
        </div>
      </div>

      <div className={styles.fullWidth}>
        <PrivacyAccuracyScatter />
      </div>
    </div>
  )
}
