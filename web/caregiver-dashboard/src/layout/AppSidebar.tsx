import type { ComponentType } from 'react'
import { MoreHorizontal, Settings } from 'lucide-react'

export type SidebarItem = { label: string; path: string; icon: ComponentType<{size?: number}> }

type Props = { items: SidebarItem[]; activePath: string; openAlerts: number; userName: string; onSignOut: () => void; onNavigate: (path: string) => void }

export function AppSidebar({items, activePath, openAlerts, userName, onSignOut, onNavigate}: Props) {
  const initials = userName.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase()
  return <aside><div className="brand"><span className="logo">N</span><span>neuro<span>X</span></span></div><nav>{items.map(({label, path, icon: Icon}) => <button key={path} className={activePath === path ? 'selected' : ''} onClick={() => onNavigate(path)}><Icon size={20}/>{label}{label === 'Alerts' && openAlerts > 0 && <i>{openAlerts}</i>}</button>)}</nav><div className="sidebar-bottom"><button onClick={() => onNavigate('/settings')}><Settings size={20}/>Settings</button><button className="user" onClick={onSignOut} title="Sign out"><div className="avatar">{initials}</div><div><b>{userName}</b><small>Caregiver - Sign out</small></div><MoreHorizontal size={20}/></button></div></aside>
}
