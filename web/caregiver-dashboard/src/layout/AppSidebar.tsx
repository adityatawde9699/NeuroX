import type { ComponentType } from 'react'
import { MoreHorizontal, Settings, X } from 'lucide-react'

export type SidebarItem = {
  label: string
  path: string
  icon: ComponentType<{ size?: number }>
}

type Props = {
  items: SidebarItem[]
  activePath: string
  openAlerts: number
  userName: string
  onSignOut: () => void
  onNavigate: (path: string) => void
  mobileOpen?: boolean
  onClose?: () => void
}

function initials(name: string) {
  return name
    .split(' ')
    .map(part => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function AppSidebar({
  items,
  activePath,
  openAlerts,
  userName,
  onSignOut,
  onNavigate,
  mobileOpen = false,
  onClose,
}: Props) {
  const handleNavigation = (path: string) => {
    onNavigate(path)
    onClose?.()
  }

  return (
    <aside
      className={mobileOpen ? 'sidebar-open' : ''}
      aria-label="Main navigation"
    >
      {/* Brand */}
      <div className="brand">
        <span className="logo" aria-hidden="true">N</span>
        <span>neuro<span>X</span></span>
        <button
          className="sidebar-close"
          aria-label="Close navigation"
          onClick={onClose}
        >
          <X size={19} />
        </button>
      </div>

      {/* Navigation items */}
      <nav aria-label="Dashboard sections">
        {items.map(({ label, path, icon: Icon }) => (
          <button
            key={path}
            className={activePath === path ? 'selected' : ''}
            onClick={() => handleNavigation(path)}
            aria-current={activePath === path ? 'page' : undefined}
            aria-label={label === 'Alerts' && openAlerts > 0
              ? `${label} — ${openAlerts} open`
              : label}
          >
            <Icon size={19} aria-hidden="true" />
            {label}
            {label === 'Alerts' && openAlerts > 0 && (
              <i aria-hidden="true">{openAlerts}</i>
            )}
          </button>
        ))}
      </nav>

      {/* Bottom controls */}
      <div className="sidebar-bottom">
        <button
          onClick={() => handleNavigation('/settings')}
          aria-label="Settings"
        >
          <Settings size={19} aria-hidden="true" />
          Settings
        </button>

        <button
          className="user"
          onClick={onSignOut}
          aria-label={`Sign out of ${userName}'s account`}
        >
          <div className="avatar" aria-hidden="true">{initials(userName)}</div>
          <div>
            <b>{userName}</b>
            <small>Caregiver · Sign out</small>
          </div>
          <MoreHorizontal size={18} aria-hidden="true" />
        </button>
      </div>
    </aside>
  )
}
