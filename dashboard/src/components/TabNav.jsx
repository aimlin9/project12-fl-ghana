import styles from './TabNav.module.css'

export default function TabNav({ tabs, active, onChange }) {
  return (
    <nav className={styles.nav}>
      {tabs.map((tab, i) => (
        <button
          key={tab}
          className={i === active ? styles.tabActive : styles.tab}
          onClick={() => onChange(i)}
        >
          {tab}
        </button>
      ))}
    </nav>
  )
}
