import { useState, useEffect } from 'react'
import MetricCards from './MetricCards.jsx'
import ConvergenceChart from './ConvergenceChart.jsx'
import CommOverheadChart from './CommOverheadChart.jsx'
import PrivacyAccuracyScatter from './PrivacyAccuracyScatter.jsx'
import { fetchBaseline } from '../api.js'
import styles from './DistrictView.module.css'

function PlayIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
      <path d="M2 1.2c0-.66.72-1.06 1.28-.72l7 4.3c.54.33.54 1.13 0 1.46l-7 4.3C2.72 10.86 2 10.46 2 9.8V1.2z" />
    </svg>
  )
}

function StopIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" rx="1.5" />
    </svg>
  )
}

export default function DistrictView({ telemetry, onStart, onStop, running }) {
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

      <div className={styles.controlBar}>
        <div className={styles.controlLeft}>
          <span className={styles.viewLabel}>District Officer View</span>
          {baseline && (
            <span className={styles.baselineBadge}>
              Centralised baseline — F1 <strong className="mono">{baseF1.toFixed(4)}</strong>
              {' '}· Acc <strong className="mono">{baseline.accuracy.toFixed(4)}</strong>
              {' '}· AUC <strong className="mono">{baseline.auc_roc.toFixed(4)}</strong>
              {lastF1 != null && (
                <span className={withinTarget ? styles.withinTarget : styles.belowTarget}>
                  {withinTarget ? ' · within 5pp target' : ` · Δ ${(baseF1 - lastF1).toFixed(4)} from baseline`}
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
        <div className={styles.controlActions}>
          <button
            className={running ? styles.startBtnRunning : styles.startBtn}
            onClick={onStart}
            disabled={running}
          >
            {running ? <><span className={styles.pulseDot} /> Simulation running</> : <><PlayIcon /> Start FL simulation</>}
          </button>
          {running && (
            <button className={styles.stopBtn} onClick={onStop}>
              <StopIcon /> Stop
            </button>
          )}
        </div>
      </div>

      <MetricCards rounds={rounds} last={last} clients={clients} config={config}
                   liveAccuracy={telemetry?.live_accuracy} running={running} />

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
