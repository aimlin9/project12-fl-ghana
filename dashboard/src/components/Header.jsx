import styles from './Header.module.css'

export default function Header({ running, source }) {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <div className={styles.mark}>FL</div>
        <div>
          <div className={styles.title}>Cross-School Federated Learning</div>
          <div className={styles.sub}>Ghanaian District Schools — Privacy-Preserving Admin Console</div>
        </div>
      </div>

      <div className={styles.status}>
        <span className={running ? styles.dotLive : styles.dotIdle} />
        <span className={styles.statusText}>
          {running
            ? (source === 'cli' ? 'Live — started from CLI' : 'Live — simulation running')
            : 'Idle'}
        </span>
      </div>
    </header>
  )
}
