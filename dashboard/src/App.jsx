import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, LogarithmicScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { fetchTelemetry, startSimulation, updateConfig, toggleClient } from './api.js'
import Header from './components/Header.jsx'
import TabNav from './components/TabNav.jsx'
import DistrictView from './components/DistrictView.jsx'
import SchoolAdminView from './components/SchoolAdminView.jsx'
import ConfigPanel from './components/ConfigPanel.jsx'
import StatusBanner from './components/StatusBanner.jsx'
import styles from './App.module.css'

ChartJS.register(
  CategoryScale, LinearScale, LogarithmicScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, Filler
)

const TABS = ['District View', 'School Admin', 'Configuration']
const POLL_MS = 3000

export default function App() {
  const [telemetry, setTelemetry]   = useState(null)
  const [activeTab, setActiveTab]   = useState(0)
  const [error, setError]           = useState(null)
  const [actionMsg, setActionMsg]   = useState(null)
  const pollRef = useRef(null)

  const poll = useCallback(async () => {
    try {
      const data = await fetchTelemetry()
      setTelemetry(data)
      setError(null)
    } catch (e) {
      setError('Cannot reach FL server at localhost:8000 — is it running?')
    }
  }, [])

  useEffect(() => {
    poll()
    pollRef.current = setInterval(poll, POLL_MS)
    return () => clearInterval(pollRef.current)
  }, [poll])

  const notify = (msg, isError = false) => {
    setActionMsg({ msg, isError })
    setTimeout(() => setActionMsg(null), 4000)
  }

  const handleStart = async () => {
    try {
      await startSimulation()
      notify('Simulation started — polling for updates…')
    } catch (e) {
      notify(e.message, true)
    }
  }

  const handleConfigSave = async (cfg) => {
    try {
      await updateConfig(cfg)
      await poll()
      notify('Configuration saved.')
    } catch (e) {
      notify(e.message, true)
    }
  }

  const handleToggle = async (schoolName) => {
    try {
      await toggleClient(schoolName)
      await poll()
    } catch (e) {
      notify(e.message, true)
    }
  }

  const running = telemetry?.simulation_running ?? false

  return (
    <div className={styles.app}>
      <Header running={running} keyBits={telemetry?.config?.paillier_key_bits} />

      {actionMsg && (
        <div className={actionMsg.isError ? styles.toastError : styles.toastOk}>
          {actionMsg.msg}
        </div>
      )}

      {error && (
        <div className={styles.errorBar}>{error}</div>
      )}

      {running && <StatusBanner rounds={telemetry?.rounds ?? []} totalRounds={telemetry?.config?.total_rounds ?? '?'} />}

      <TabNav tabs={TABS} active={activeTab} onChange={setActiveTab} />

      <main className={styles.main}>
        {activeTab === 0 && (
          <DistrictView telemetry={telemetry} onStart={handleStart} running={running} />
        )}
        {activeTab === 1 && (
          <SchoolAdminView
            telemetry={telemetry}
            onToggle={handleToggle}
          />
        )}
        {activeTab === 2 && (
          <ConfigPanel
            telemetry={telemetry}
            onSave={handleConfigSave}
            onStart={handleStart}
            running={running}
          />
        )}
      </main>
    </div>
  )
}
