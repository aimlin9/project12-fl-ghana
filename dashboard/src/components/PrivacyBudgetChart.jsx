import { Line } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#a855f7', '#06b6d4']

const OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { labels: { color: '#9ca3af', font: { size: 11 }, boxWidth: 12 } },
    title: {
      display: true,
      text: 'Cumulative Privacy Budget ε per Round',
      color: '#f3f4f6',
      font: { size: 13, weight: '600' },
      padding: { bottom: 12 },
    },
  },
  scales: {
    x: {
      ticks: { color: '#6b7280', maxTicksLimit: 15 },
      grid:  { color: 'rgba(255,255,255,0.04)' },
    },
    y: {
      title: { display: true, text: 'ε (epsilon)', color: '#6b7280', font: { size: 11 } },
      ticks: { color: '#6b7280' },
      grid:  { color: 'rgba(255,255,255,0.04)' },
      beginAtZero: true,
    },
  },
}

export default function PrivacyBudgetChart({ rounds, clients }) {
  if (rounds.length === 0) {
    return <div className={styles.empty}>No round data yet.</div>
  }

  const schoolNames = Object.keys(clients)
  const labels = rounds.map(r => `R${r.round}`)

  // Use max_epsilon per round as a proxy (server stores aggregate)
  const datasets = [{
    label: 'Max ε (all nodes)',
    data: rounds.map(r => r.max_epsilon ?? 0),
    borderColor: COLORS[0],
    backgroundColor: 'rgba(99,102,241,0.07)',
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.3,
    fill: true,
  }]

  return (
    <div style={{ height: '260px' }}>
      <Line data={{ labels, datasets }} options={OPTS} />
    </div>
  )
}
