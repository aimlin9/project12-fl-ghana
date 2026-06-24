import { useState, useEffect, useRef } from 'react'
import styles from './ConfigPanel.module.css'

export default function ConfigPanel({ telemetry, onSave, onStart, onStop, running }) {
  const cfg = telemetry?.config ?? {}
  const initialized = useRef(false)

  const [form, setForm] = useState({
    use_dp:            'True',
    use_paillier:      'True',
    local_epochs:      3,
    lr:                0.01,
    total_rounds:      10,
    num_nodes:         3,
    paillier_key_bits: 1024,
    noise_multiplier:  1.1,
    max_grad_norm:     1.0,
  })

  useEffect(() => {
    if (!initialized.current && cfg && Object.keys(cfg).length) {
      setForm({
        use_dp:            cfg.use_dp            ?? 'True',
        use_paillier:      cfg.use_paillier      ?? 'True',
        local_epochs:      cfg.local_epochs      ?? 3,
        lr:                cfg.lr                ?? 0.01,
        total_rounds:      cfg.total_rounds      ?? 10,
        num_nodes:         cfg.num_nodes         ?? 3,
        paillier_key_bits: cfg.paillier_key_bits ?? 2048,
        noise_multiplier:  cfg.noise_multiplier  ?? 1.1,
        max_grad_norm:     cfg.max_grad_norm     ?? 1.0,
      })
      initialized.current = true
    }
  }, [telemetry])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = () => onSave({
    use_dp:            form.use_dp,
    use_paillier:      form.use_paillier,
    local_epochs:      Number(form.local_epochs),
    lr:                Number(form.lr),
    total_rounds:      Number(form.total_rounds),
    num_nodes:         Number(form.num_nodes),
    paillier_key_bits: Number(form.paillier_key_bits),
    noise_multiplier:  Number(form.noise_multiplier),
    max_grad_norm:     Number(form.max_grad_norm),
  })

  return (
    <div className={styles.layout}>
      <div className={styles.card}>
        <div className={styles.cardTitle}>Simulation Configuration</div>

        <div className={styles.switchRow}>
          <label>Differential Privacy (DP-SGD)</label>
          <Toggle
            checked={form.use_dp === 'True'}
            onChange={v => set('use_dp', v ? 'True' : 'False')}
            disabled={running}
          />
        </div>

        <div className={styles.switchRow}>
          <label>Paillier Homomorphic Encryption</label>
          <Toggle
            checked={form.use_paillier === 'True'}
            onChange={v => set('use_paillier', v ? 'True' : 'False')}
            disabled={running}
          />
        </div>

        <div className={styles.field}>
          <label>Paillier Key Size</label>
          <select
            value={form.paillier_key_bits}
            onChange={e => set('paillier_key_bits', e.target.value)}
            disabled={running}
            className={styles.input}
          >
            <option value={512}>512-bit (fast demo)</option>
            <option value={1024}>1024-bit (medium)</option>
            <option value={2048}>2048-bit (production)</option>
          </select>
        </div>

        <div className={styles.field}>
          <label>School Nodes (3 – 5)</label>
          <input
            type="number" min={3} max={5}
            value={form.num_nodes}
            onChange={e => set('num_nodes', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Total FL Rounds</label>
          <input
            type="number" min={1} max={200}
            value={form.total_rounds}
            onChange={e => set('total_rounds', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Local Epochs per Round</label>
          <input
            type="number" min={1} max={20}
            value={form.local_epochs}
            onChange={e => set('local_epochs', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Learning Rate</label>
          <input
            type="number" step="0.001" min={0.0001} max={1}
            value={form.lr}
            onChange={e => set('lr', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>DP Noise Multiplier (σ) — higher = more private</label>
          <input
            type="number" step="0.1" min={0.1} max={5}
            value={form.noise_multiplier}
            onChange={e => set('noise_multiplier', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Max Gradient Norm — gradient clipping threshold</label>
          <input
            type="number" step="0.1" min={0.1} max={10}
            value={form.max_grad_norm}
            onChange={e => set('max_grad_norm', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <button className={styles.btnSave} onClick={handleSave} disabled={running}>
          Save Configuration
        </button>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Simulation Control</div>

        <div className={styles.statusRow}>
          <span>Status</span>
          <span className={running ? styles.statusRunning : styles.statusIdle}>
            {running ? '● Running' : '○ Idle'}
          </span>
        </div>

        <div className={styles.infoBox}>
          <div className={styles.infoRow}><span>DP Noise σ</span><span>{form.noise_multiplier} (Opacus 1.4)</span></div>
          <div className={styles.infoRow}><span>Max Grad Norm</span><span>{form.max_grad_norm}</span></div>
          <div className={styles.infoRow}><span>Key Size</span><span>{form.paillier_key_bits}-bit Paillier</span></div>
          <div className={styles.infoRow}><span>Target ε / round</span><span>≤ 3.0 (δ=1e-5)</span></div>
          <div className={styles.infoRow}><span>FL Framework</span><span>Flower 1.8.0</span></div>
          <div className={styles.infoRow}><span>FL Port</span><span>127.0.0.1:8088</span></div>
        </div>

        <button
          className={styles.btnStart}
          onClick={onStart}
          disabled={running}
        >
          {running ? 'Simulation Running…' : '▶ Start FL Simulation'}
        </button>

        {running && (
          <button
            onClick={onStop}
            style={{
              background: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.4)',
              color: '#fca5a5',
              borderRadius: '0.5rem',
              padding: '0.65rem',
              fontSize: '0.875rem',
              fontWeight: 600,
              width: '100%',
              cursor: 'pointer',
            }}
          >
            ■ Stop Simulation
          </button>
        )}

        <p className={styles.note}>
          Proposal target: federated F1 within 5 pp of centralised baseline after {form.total_rounds} rounds.
          Run <code>python scripts/train_baseline.py</code> to generate the baseline first.
        </p>
      </div>
    </div>
  )
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: disabled ? 'not-allowed' : 'pointer' }}>
      <div
        onClick={() => !disabled && onChange(!checked)}
        style={{
          width: 44, height: 24, borderRadius: 12,
          background: checked ? 'var(--primary)' : 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.1)',
          position: 'relative', transition: 'background 0.25s',
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <div style={{
          position: 'absolute',
          width: 16, height: 16, borderRadius: '50%',
          background: 'white',
          top: 3, left: checked ? 23 : 3,
          transition: 'left 0.25s',
        }} />
      </div>
      <span style={{ fontSize: '0.8rem', color: checked ? '#a5b4fc' : 'var(--muted)' }}>
        {checked ? 'ON' : 'OFF'}
      </span>
    </label>
  )
}
