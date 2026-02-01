/**
 * Status Badge component for appointments.
 * 
 * Displays appointment status (Upcoming, Missed, Flagged)
 * based on date and type.
 */

import { isBefore } from 'date-fns'

export function StatusBadge({ date, type, status }) {
  // If status is explicitly provided, use it
  if (status) {
    const statusConfig = {
      scheduled: { className: 'bg-blue-100 text-blue-700', label: 'Upcoming' },
      completed: { className: 'bg-green-100 text-green-700', label: 'Completed' },
      missed: { className: 'bg-orange-100 text-orange-700', label: 'Missed' },
      cancelled: { className: 'bg-gray-100 text-gray-700', label: 'Cancelled' },
      flagged: { className: 'bg-red-100 text-red-700', label: 'Flagged' },
    }
    const config = statusConfig[status] || statusConfig.scheduled
    return (
      <span className={`px-2 py-1 ${config.className} text-xs font-medium rounded`}>
        {config.label}
      </span>
    )
  }

  // Fall back to date/type logic
  const isEmergency = type === 'Emergency'
  const isMissed = date && isBefore(new Date(date), new Date())

  if (isEmergency) {
    return (
      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded">
        Flagged
      </span>
    )
  }

  if (isMissed) {
    return (
      <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">
        Missed
      </span>
    )
  }

  return (
    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
      Upcoming
    </span>
  )
}

export function getStatusColor(date, type, status) {
  if (status === 'flagged' || type === 'Emergency') {
    return 'border-l-4 border-red-500 bg-red-50'
  }

  if (status === 'missed' || (date && isBefore(new Date(date), new Date()))) {
    return 'border-l-4 border-orange-500 bg-orange-50'
  }

  if (status === 'completed') {
    return 'border-l-4 border-green-500 bg-green-50'
  }

  return 'border-l-4 border-blue-500 bg-blue-50'
}

export default StatusBadge
