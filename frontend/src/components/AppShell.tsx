import {
  CheckSquare,
  FileText,
  Folder,
  Home,
  Inbox,
  LayoutGrid,
  Plus,
  Settings,
  UserRound,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { Brand } from './Brand'

const desktopNav = [
  { to: '/', label: '概览', icon: LayoutGrid },
  { to: '/content', label: '内容', icon: FileText },
  { to: '/tasks', label: '任务', icon: CheckSquare },
  { to: '/sources', label: '来源', icon: Folder },
  { to: '/settings', label: '设置', icon: Settings },
]

const mobileNav = [
  { to: '/', label: '首页', icon: Home },
  { to: '/content', label: '内容', icon: FileText },
  { to: '/capture', label: '投递', icon: Plus, primary: true },
  { to: '/todos', label: '待办', icon: CheckSquare },
  { to: '/profile', label: '我的', icon: UserRound },
]

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <nav className="sidebar__nav" aria-label="管理导航">
          {desktopNav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} className="nav-link">
              <Icon size={21} strokeWidth={1.6} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__status">
          <span className="status-dot" />
          <div>
            <strong>Mac mini 在线</strong>
            <span>所有内容仅存于本机</span>
          </div>
        </div>
      </aside>
      <main className="app-main">{children}</main>
      <nav className="bottom-nav" aria-label="主要导航">
        {mobileNav.map(({ to, label, icon: Icon, primary }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={`bottom-nav__item ${primary ? 'bottom-nav__item--primary' : ''}`}
          >
            <span className="bottom-nav__icon"><Icon size={primary ? 28 : 23} strokeWidth={1.7} /></span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <Inbox size={28} strokeWidth={1.5} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  )
}

export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <Brand compact />
      <h1>{title}</h1>
      <div className="page-header__actions">{actions}</div>
    </header>
  )
}
