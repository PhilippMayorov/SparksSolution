/**
 * Main layout component with navigation.
 *
 * Provides consistent header/sidebar for all protected pages.
 * Shows flag count badge in navigation.
 */

import { Outlet, Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Flag, LogOut, Menu } from 'lucide-react'
import { getOpenFlags } from '../api/client'
import FlagBanner from './FlagBanner'

export default function Layout() {
  const location = useLocation()

  // Fetch open flags count for badge
  const { data: flags = [] } = useQuery({
    queryKey: ['flags', 'open'],
    queryFn: getOpenFlags,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const urgentFlags = flags.filter(
    (f) => f.priority === 'urgent' || f.priority === 'high',
  )

  const navItems = [
    { path: '/', icon: Calendar, label: 'Calendar' },
    {
      path: '/flags',
      icon: Flag,
      label: 'Flags',
      badge: flags.length || null,
    },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Urgent flags banner */}
      {urgentFlags.length > 0 && <FlagBanner flags={urgentFlags} />}

      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <span className="font-semibold text-xl text-gray-900">
                Nurse Dashboard
              </span>
            </div>

            {/* Navigation */}
            <nav className="flex items-center gap-1">
              {navItems.map(({ path, icon: Icon, label, badge }) => (
                <Link
                  key={path}
                  to={path}
                  className={`
                    relative flex items-center gap-2 px-4 py-2 rounded-lg
                    transition-colors
                    ${
                      location.pathname === path
                        ? 'bg-primary-50 text-primary-600'
                        : 'text-gray-600 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{label}</span>
                  {badge && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-danger text-white text-xs rounded-full flex items-center justify-center">
                      {badge}
                    </span>
                  )}
                </Link>
              ))}

              {/* Logout */}
              <button
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-100 ml-4"
                onClick={() => {
                  // TODO: Implement logout
                  localStorage.removeItem('auth_token')
                  window.location.href = '/login'
                }}
              >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Logout</span>
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t py-4 text-center text-sm text-gray-500">
        Nurse Appointment System © 2026
      </footer>
    </div>
  )
}
