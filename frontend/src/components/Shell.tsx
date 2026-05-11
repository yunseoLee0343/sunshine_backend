import { NavLink, Outlet, useParams } from 'react-router-dom'
import styles from './Shell.module.css'

export default function Shell() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <NavLink to="/" className={styles.logo}>
          🌿 Sunshine
        </NavLink>
        <nav className={styles.nav}>
          <NavLink to="/" end className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            홈
          </NavLink>
          <NavLink to="/onboarding" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            식물 등록
          </NavLink>
        </nav>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

// Sub-shell with plant-level tabs (used inside /plants/:plantId/*)
export function PlantShell() {
  const { plantId } = useParams<{ plantId: string }>()

  return (
    <div>
      <nav className={styles.tabNav}>
        <NavLink to={`/plants/${plantId}`} end className={({ isActive }) => isActive ? styles.activeTab : styles.tab}>
          상세
        </NavLink>
        <NavLink to={`/plants/${plantId}/care`} className={({ isActive }) => isActive ? styles.activeTab : styles.tab}>
          관리
        </NavLink>
        <NavLink to={`/plants/${plantId}/chat`} className={({ isActive }) => isActive ? styles.activeTab : styles.tab}>
          채팅
        </NavLink>
        <NavLink to={`/plants/${plantId}/history`} className={({ isActive }) => isActive ? styles.activeTab : styles.tab}>
          이력
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}
