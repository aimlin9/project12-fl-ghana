import ClientStatusCard from './ClientStatusCard.jsx'
import PrivacyBudgetChart from './PrivacyBudgetChart.jsx'
import styles from './SchoolAdminView.module.css'

export default function SchoolAdminView({ telemetry, onToggle }) {
  const clients = telemetry?.clients ?? {}
  const rounds  = telemetry?.rounds  ?? []

  return (
    <div className={styles.layout}>
      <section>
        <div className={styles.sectionTitle}>School Node Status</div>
        <div className={styles.cardGrid}>
          {Object.entries(clients).map(([name, info]) => (
            <ClientStatusCard
              key={name}
              name={name}
              info={info}
              rounds={rounds}
              onToggle={() => onToggle(name)}
            />
          ))}
          {Object.keys(clients).length === 0 && (
            <p className={styles.empty}>No nodes configured — start a simulation first.</p>
          )}
        </div>
      </section>

      <section>
        <div className={styles.sectionTitle}>Cumulative Privacy Budget (ε) per Node</div>
        <div className={styles.chartWrap}>
          <PrivacyBudgetChart rounds={rounds} clients={clients} />
        </div>
      </section>
    </div>
  )
}
