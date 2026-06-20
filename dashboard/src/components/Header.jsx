import styles from './Header.module.css'

export default function Header({ running, keyBits }) {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <div className={styles.icon}>FL</div>
        <div>
          <div className={styles.title}>Cross-School Federated Learning</div>
          <div className={styles.sub}>Ghanaian District Schools — Privacy-Preserving Admin Portal</div>
        </div>
      </div>
      <div className={styles.badges}>
        <span className={styles.badge}>Flower 1.8.0</span>
        <span className={styles.badge}>Paillier {keyBits ?? 2048}-bit</span>
        <span className={styles.badge}>DP-SGD Opacus 1.4</span>
        <span className={running ? styles.badgeActive : styles.badgeIdle}>
          {running ? '● Live' : '○ Idle'}
        </span>
      </div>
    </header>
  )
}
