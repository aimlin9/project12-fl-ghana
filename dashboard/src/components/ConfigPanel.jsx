import { useState, useEffect, useRef } from 'react'
import styles from './ConfigPanel.module.css'

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
    paillier_key_bits: 2048,
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
        <div className={styles.cardTitle}>Simulation configuration</div>

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
          <label>Paillier key size</label>
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
          <label>School nodes (3–5)</label>
          <input
            type="number" min={3} max={5}
            value={form.num_nodes}
            onChange={e => set('num_nodes', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Total FL rounds</label>
          <input
            type="number" min={1} max={200}
            value={form.total_rounds}
            onChange={e => set('total_rounds', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Local epochs per round</label>
          <input
            type="number" min={1} max={20}
            value={form.local_epochs}
            onChange={e => set('local_epochs', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Learning rate</label>
          <input
            type="number" step="0.001" min={0.0001} max={1}
            value={form.lr}
            onChange={e => set('lr', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>DP noise multiplier (σ) — higher = more private</label>
          <input
            type="number" step="0.1" min={0.1} max={5}
            value={form.noise_multiplier}
            onChange={e => set('noise_multiplier', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <div className={styles.field}>
          <label>Max gradient norm — gradient clipping threshold</label>
          <input
            type="number" step="0.1" min={0.1} max={10}
            value={form.max_grad_norm}
            onChange={e => set('max_grad_norm', e.target.value)}
            disabled={running}
            className={styles.input}
          />
        </div>

        <button className={styles.btnSave} onClick={handleSave} disabled={running}>
          Save configuration
        </button>
      </div>

      <div className={styles.card}>
        <div className={styles.cardTitle}>Simulation control</div>

        <div className={styles.statusRow}>
          <span>Status</span>
          <span className={running ? styles.statusRunning : styles.statusIdle}>
            <span className={running ? styles.dotLive : styles.dotIdle} />
            {running ? 'Running' : 'Idle'}
          </span>
        </div>

        <div className={styles.infoBox}>
          <div className={styles.infoRow}><span>DP noise σ</span><span className="mono">{form.noise_multiplier} (Opacus 1.4)</span></div>
          <div className={styles.infoRow}><span>Max grad norm</span><span className="mono">{form.max_grad_norm}</span></div>
          <div className={styles.infoRow}><span>Key size</span><span className="mono">{form.paillier_key_bits}-bit Paillier</span></div>
          <div className={styles.infoRow}><span>Target ε / round</span><span className="mono">≤ 3.0 (δ=1e-5)</span></div>
          <div className={styles.infoRow}><span>FL framework</span><span className="mono">Flower 1.8.0</span></div>
          <div className={styles.infoRow}><span>FL port</span><span className="mono">127.0.0.1:8088</span></div>
        </div>

        <button
          className={styles.btnStart}
          onClick={onStart}
          disabled={running}
        >
          {running ? 'Simulation running…' : <><PlayIcon /> Start FL simulation</>}
        </button>

        {running && (
          <button onClick={onStop} className={styles.btnStop}>
            <StopIcon /> Stop simulation
          </button>
        )}

        <p className={styles.note}>
          Proposal target: federated F1 within 5pp of centralised baseline after {form.total_rounds} rounds.
          Run <code>python scripts/train_baseline.py</code> to generate the baseline first.
        </p>
      </div>
    </div>
  )
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <label className={styles.toggleWrap} data-disabled={disabled || undefined}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={styles.toggleTrack}
        data-checked={checked || undefined}
      >
        <span className={styles.toggleThumb} />
      </button>
      <span className={styles.toggleLabel} data-checked={checked || undefined}>
        {checked ? 'On' : 'Off'}
      </span>
    </label>
  )
}
