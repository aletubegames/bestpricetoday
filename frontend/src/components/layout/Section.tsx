import styles from "./Section.module.css"

interface SectionProps {
  children: React.ReactNode
  bg?: "white" | "muted" | "dark"
  title?: string
  subtitle?: string
  className?: string
}

export default function Section({ children, bg = "white", title, subtitle, className = "" }: SectionProps) {
  return (
    <section className={`${styles.section} ${styles[bg]} ${className}`}>
      <div className={styles.inner}>
        {title && <h2 className={styles.sectionTitle}>{title}</h2>}
        {subtitle && <p className={styles.sectionSubtitle}>{subtitle}</p>}
        {children}
      </div>
    </section>
  )
}
