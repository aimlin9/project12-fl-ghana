import { Line } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      labels: { color: '#9ca3af', font: { size: 11 }, boxWidth: 12 },
    },
    title: {
      display: true,
      text: 'FL Convergence — F1, Accuracy & AUC-ROC per Round',
      color: '#f3f4f6',
      font: { size: 13, weight: '600' },
      padding: { bottom: 16 },
    },
  },
  scales: {
    x: {
      title: { display: true, text: 'FL Round', color: '#6b7280', font: { size: 11 } },
      ticks: { color: '#6b7280', maxTicksLimit: 15 },
      grid:  { color: 'rgba(255,255,255,0.04)' },
    },
    y: {
      min: 0, max: 1,
      title: { display: true, text: 'Score / Loss', color: '#6b7280', font: { size: 11 } },
      ticks: { color: '#6b7280' },
      grid:  { color: 'rgba(255,255,255,0.06)' },
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
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.08)',
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.3,
      fill: true,
    },
    {
      label: 'Balanced Accuracy',
      data: acc,
      borderColor: '#10b981',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.3,
    },
    {
      label: 'AUC-ROC',
      data: auc,
      borderColor: '#a855f7',
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      borderDash: [4, 3],
      pointRadius: 2,
      tension: 0.3,
    },
    {
      label: 'Loss',
      data: loss,
      borderColor: '#ef4444',
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
      borderColor: '#f97316',
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
          <div style={{ marginTop: '0.5rem', color: '#f97316', fontSize: '0.85rem' }}>
            Centralised baseline F1: <strong>{baseline.f1_score_macro.toFixed(4)}</strong> — federated target: ≥ {(baseline.f1_score_macro - 0.05).toFixed(4)}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ height: '320px' }}>
      <Line data={{ labels, datasets }} options={BASE_OPTS} />
    </div>
  )
}
