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
      color: '#efe9df',
      font: { size: 13, weight: '600', family: 'Manrope' },
      padding: { bottom: 12 },
    },
  },
  scales: {
    x: {
      ticks: { color: '#756c60', maxTicksLimit: 12 },
      grid:  { display: false },
    },
    y: {
      title: { display: true, text: 'MB', color: '#756c60', font: { size: 11 } },
      ticks: { color: '#756c60' },
      grid:  { color: 'rgba(240,235,225,0.05)' },
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
      backgroundColor: 'rgba(114,145,171,0.55)',
      borderColor: '#7291ab',
      borderWidth: 1,
      borderRadius: 4,
    }],
  }

  return (
    <div className={styles.boxLarge}>
      <Bar data={data} options={OPTS} />
    </div>
  )
}
