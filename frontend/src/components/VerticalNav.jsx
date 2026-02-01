/**
 * Vertical Navigation sidebar component.
 * 
 * Features:
 * - Nurse profile display with avatar
 * - Navigation links to Calendar and Dashboard
 * - Logout functionality
 */

import { Calendar, LayoutDashboard, LogOut, Flag } from 'lucide-react'
import { NavLink } from 'react-router-dom'

export default function VerticalNav({ nurseName, onLogout }) {
  const initials = nurseName
    ? nurseName.split(' ').map(n => n[0]).join('')
    : 'N'

  return (
    <nav className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-blue-700 font-semibold text-lg">
              {initials}
            </span>
          </div>
          <div>
            <p className="font-semibold text-gray-900">{nurseName || 'Nurse'}</p>
            <p className="text-sm text-gray-500">Registered Nurse</p>
          </div>
        </div>
      </div>

      <div className="flex-1 py-6">
        <div className="space-y-1 px-3">
          <NavLink
            to="/calendar"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`
            }
          >
            <Calendar size={20} />
            Calendar
          </NavLink>

          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`
            }
          >
            <LayoutDashboard size={20} />
            Dashboard
          </NavLink>

          <NavLink
            to="/flags"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`
            }
          >
            <Flag size={20} />
            Flags
          </NavLink>
        </div>
      </div>

      <div className="p-4 border-t border-gray-200">
        <button
          onClick={onLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors w-full"
        >
          <LogOut size={20} />
          Log Out
        </button>
      </div>
    </nav>
  )
}
