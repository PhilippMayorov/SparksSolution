/**
 * View Switcher component for calendar views.
 * 
 * Allows switching between Day, Week, and Month views.
 */

import { Calendar as CalendarIcon, List, Columns3 } from 'lucide-react'

export default function ViewSwitcher({ currentView, onViewChange }) {
  return (
    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
      <button
        onClick={() => onViewChange('day')}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          currentView === 'day'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        <List size={16} />
        Day
      </button>
      <button
        onClick={() => onViewChange('week')}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          currentView === 'week'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        <Columns3 size={16} />
        Week
      </button>
      <button
        onClick={() => onViewChange('month')}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          currentView === 'month'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        <CalendarIcon size={16} />
        Month
      </button>
    </div>
  )
}
