import { useEffect, useState } from 'react'
import { Line } from 'react-chartjs-2'
import styles from './ChartCard.module.css'

function buildOpts(yMin, yMax) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#9ca3af', font: { size: 11 } } },
      title: {
        display: true,
        text: 'Privacy-Accuracy Trade-off (ε vs F1-score)',
        color: '#f3f4f6',
        font: { size: 13, weight: '600' },
        padding: { bottom: 12 },
      },
      tooltip: {
        callbacks: {
          label: ctx => {
            const d = ctx.raw
            return `σ=${d.sigma}  ε=${d.x.toFixed(3)}  F1=${d.y.toFixed(4)}`
          },
        },
      },
    },
    scales: {
      x: {
        type: 'logarithmic',
        title: { display: true, text: 'Privacy Budget (ε)  ←  stronger privacy', color: '#6b7280', font: { size: 11 } },
        ticks: {
          color: '#6b7280',
          callback: v => Number.isInteger(Math.log10(v)) || [1,2,5,10,20,50].includes(v) ? v : '',
        },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      // min/max zoom to the actual data range (with padding) rather than a fixed
      // 0-1 scale — F1 across the tested noise range often only moves by a few
      // points, which is invisible on a full 0-1 axis and makes a real trade-off
      // look like a flat line.
      y: {
        min: yMin, max: yMax,
        title: { display: true, text: 'F1-score (macro)', color: '#6b7280', font: { size: 11 } },
        ticks: { color: '#6b7280' },
        grid:  { color: 'rgba(255,255,255,0.04)' },
      },
    },
  }
}

export default function PrivacyAccuracyScatter() {
  const [sweepData, setSweepData] = useState(null)

  useEffect(() => {
    fetch('/api/privacy-sweep')
      .then(r => r.ok ? r.json() : null)
      .catch(() => null)
      .then(d => setSweepData(d))
  }, [])

  if (!sweepData?.sweep?.length) {
    return (
      <div className={styles.empty}>
        Privacy-accuracy scatter not available yet.{' '}
        Run <code>python scripts/privacy_accuracy_sweep.py</code> then refresh.
      </div>
    )
  }

  const pts = sweepData.sweep.map(d => ({ x: d.epsilon, y: d.f1_score_macro, sigma: d.noise_multiplier }))
  pts.sort((a, b) => a.x - b.x)

  const allYVals = sweepData.sweep.flatMap(d => [d.f1_score_macro, d.accuracy])
  const yMin = Math.max(0, Math.min(...allYVals) - 0.05)
  const yMax = Math.min(1, Math.max(...allYVals) + 0.02)
  const opts = buildOpts(yMin, yMax)

  const data = {
    datasets: [
      {
        label: 'F1 vs ε',
        data: pts,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.15)',
        borderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8,
        tension: 0.2,
        fill: false,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
      },
      {
        label: 'Accuracy vs ε',
        data: sweepData.sweep.map(d => ({ x: d.epsilon, y: d.accuracy, sigma: d.noise_multiplier })).sort((a,b)=>a.x-b.x),
        borderColor: '#10b981',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        borderDash: [5, 3],
        pointRadius: 4,
        tension: 0.2,
        fill: false,
        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
      },
    ],
  }

  return (
    <div style={{ height: '260px' }}>
      <Line data={data} options={opts} />
    </div>
  )
}
