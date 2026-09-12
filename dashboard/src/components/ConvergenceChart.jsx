import { Line } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      labels: { color: '#a39a8d', font: { size: 11, family: 'Manrope' }, boxWidth: 12 },
    },
    title: {
      display: true,
      text: 'FL Convergence — F1, Accuracy & AUC-ROC per Round',
      color: '#efe9df',
      font: { size: 13, weight: '600', family: 'Manrope' },
      padding: { bottom: 16 },
    },
  },
  scales: {
    x: {
      title: { display: true, text: 'FL Round', color: '#756c60', font: { size: 11 } },
      ticks: { color: '#756c60', maxTicksLimit: 15 },
      grid:  { color: 'rgba(240,235,225,0.05)' },
    },
    y: {
      min: 0, max: 1,
      title: { display: true, text: 'Score / Loss', color: '#756c60', font: { size: 11 } },
      ticks: { color: '#756c60' },
      grid:  { color: 'rgba(240,235,225,0.07)' },
    },
  },
}

export default function ConvergenceChart({ rounds, baseline }) {
  const labels = rounds.map(r => `R${r.round}`)
  const f1     = rounds.map(r => r.f1_score   ?? null)
  const acc    = rounds.map(r => r.accuracy    ?? null)
  const loss   = rounds.map(r => r.loss        ?? null)
  const auc    = rounds.map(r => r.auc_roc     ?? null)

  const datasets = [
    {
      label: 'F1-score (federated)',
      data: f1,
      borderColor: '#c79a53',
      backgroundColor: 'rgba(199,154,83,0.08)',
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.3,
      fill: true,
    },
    {
      label: 'Balanced accuracy',
      data: acc,
      borderColor: '#5fab7e',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.3,
    },
    {
      label: 'AUC-ROC',
      data: auc,
      borderColor: '#7291ab',
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      borderDash: [4, 3],
      pointRadius: 2,
      tension: 0.3,
    },
    {
      label: 'Loss',
      data: loss,
      borderColor: '#c96b5c',
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      borderDash: [6, 3],
      pointRadius: 2,
      tension: 0.3,
    },
  ]

  // Centralised baseline reference line (Proposal Obj.1 — federated must be within 5 pp)
  if (baseline?.f1_score_macro != null && labels.length > 0) {
    const bVal = baseline.f1_score_macro
    datasets.push({
      label: `Centralised baseline F1 (${bVal.toFixed(4)})`,
      data: Array(labels.length).fill(bVal),
      borderColor: '#ddb46e',
      backgroundColor: 'transparent',
      borderWidth: 2,
      borderDash: [8, 5],
      pointRadius: 0,
      tension: 0,
    })
  }

  if (rounds.length === 0) {
    return (
      <div className={styles.empty}>
        No rounds completed yet. Start a simulation to see the convergence curve.
        {baseline?.f1_score_macro != null && (
          <div className={styles.baselineNote}>
            Centralised baseline F1: <strong>{baseline.f1_score_macro.toFixed(4)}</strong> — federated target: ≥ {(baseline.f1_score_macro - 0.05).toFixed(4)}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={styles.boxLarge}>
      <Line data={{ labels, datasets }} options={BASE_OPTS} />
    </div>
  )
}
