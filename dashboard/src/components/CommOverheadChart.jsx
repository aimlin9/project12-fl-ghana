import { Bar } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

const OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    title: {
      display: true,
      text: 'Communication Overhead (MB / round)',
      color: '#f3f4f6',
      font: { size: 13, weight: '600' },
      padding: { bottom: 12 },
    },
  },
  scales: {
    x: {
      ticks: { color: '#6b7280', maxTicksLimit: 12 },
      grid:  { display: false },
    },
    y: {
      title: { display: true, text: 'MB', color: '#6b7280', font: { size: 11 } },
      ticks: { color: '#6b7280' },
      grid:  { color: 'rgba(255,255,255,0.04)' },
      beginAtZero: true,
    },
  },
}

export default function CommOverheadChart({ rounds }) {
  if (rounds.length === 0) {
    return <div className={styles.empty}>No data yet.</div>
  }

  const data = {
    labels: rounds.map(r => `R${r.round}`),
    datasets: [{
      data: rounds.map(r => r.comm_overhead_mb ?? 0),
      backgroundColor: 'rgba(6,182,212,0.6)',
      borderColor: '#06b6d4',
      borderWidth: 1,
      borderRadius: 4,
    }],
  }

  return (
    <div style={{ height: '320px' }}>
      <Bar data={data} options={OPTS} />
    </div>
  )
}
