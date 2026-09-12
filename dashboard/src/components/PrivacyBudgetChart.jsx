import { Line } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

const OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { labels: { color: '#a39a8d', font: { size: 11, family: 'Manrope' }, boxWidth: 12 } },
    title: {
      display: true,
      text: 'Cumulative Privacy Budget ε per Round',
      color: '#efe9df',
      font: { size: 13, weight: '600', family: 'Manrope' },
      padding: { bottom: 12 },
    },
  },
  scales: {
    x: {
      ticks: { color: '#756c60', maxTicksLimit: 15 },
      grid:  { color: 'rgba(240,235,225,0.05)' },
    },
    y: {
      title: { display: true, text: 'ε (epsilon)', color: '#756c60', font: { size: 11 } },
      ticks: { color: '#756c60' },
      grid:  { color: 'rgba(240,235,225,0.05)' },
      beginAtZero: true,
    },
  },
}

export default function PrivacyBudgetChart({ rounds, clients }) {
  if (rounds.length === 0) {
    return <div className={styles.empty}>No round data yet.</div>
  }

  const labels = rounds.map(r => `R${r.round}`)

  // Use max_epsilon per round as a proxy (server stores aggregate)
  const datasets = [{
    label: 'Max ε (all nodes)',
    data: rounds.map(r => r.max_epsilon ?? 0),
    borderColor: '#c79a53',
    backgroundColor: 'rgba(199,154,83,0.07)',
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.3,
    fill: true,
  }]

  return (
    <div className={styles.boxSmall}>
      <Line data={{ labels, datasets }} options={OPTS} />
    </div>
  )
}
