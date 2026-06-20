const BASE = '/api'

export async function fetchTelemetry() {
  const res = await fetch(`${BASE}/telemetry`)
  if (!res.ok) throw new Error('Failed to fetch telemetry')
  return res.json()
}

export async function startSimulation() {
  const res = await fetch(`${BASE}/start`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to start simulation')
  return res.json()
}

export async function updateConfig(config) {
  const res = await fetch(`${BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to update config')
  }
  return res.json()
}

export async function toggleClient(schoolName) {
  const res = await fetch(`${BASE}/client/${schoolName}/toggle`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to toggle client')
  return res.json()
}

export async function fetchPrivacyAccuracy() {
  try {
    const res = await fetch('/results/privacy_accuracy_tradeoff.json')
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchBaseline() {
  try {
    const res = await fetch(`${BASE}/baseline`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}
