/**
 * Flag banner component for urgent notifications.
 *
 * Displayed at the top of the page when there are
 * urgent or high-priority flags requiring attention.
 */

import { Link } from 'react-router-dom'
import { AlertTriangle, X, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

/**
 * FlagBanner component
 * @param {Object} props
 * @param {Array} props.flags - Array of urgent/high priority flags
 */
export default function FlagBanner({ flags = [] }) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed || flags.length === 0) {
    return null
  }

  const urgentCount = flags.filter((f) => f.priority === 'urgent').length
  const highCount = flags.filter((f) => f.priority === 'high').length

  return (
    <div
      className={clsx(
        'px-4 py-3 flex items-center justify-between',
        urgentCount > 0 ? 'bg-red-600' : 'bg-yellow-500',
      )}
    >
      <div className="flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 text-white" />
        <div className="text-white">
          <span className="font-semibold">
            {flags.length} {flags.length === 1 ? 'flag' : 'flags'} need
            attention
          </span>
          <span className="ml-2 text-white/80">
            {urgentCount > 0 && `${urgentCount} urgent`}
            {urgentCount > 0 && highCount > 0 && ', '}
            {highCount > 0 && `${highCount} high priority`}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Link
          to="/flags"
          className={clsx(
            'flex items-center gap-1 px-3 py-1 rounded-lg text-sm font-medium transition-colors',
            urgentCount > 0
              ? 'bg-white text-red-600 hover:bg-red-50'
              : 'bg-white text-yellow-600 hover:bg-yellow-50',
          )}
        >
          View Flags
          <ChevronRight className="w-4 h-4" />
        </Link>

        <button
          onClick={() => setDismissed(true)}
          className="p-1 rounded hover:bg-white/20 text-white transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}

/**
 * Individual flag item component for the flags list.
 */
export function FlagItem({ flag, onResolve, onDismiss }) {
  const {
    id,
    title,
    description,
    priority,
    status,
    patient,
    appointment,
    created_at,
  } = flag

  const priorityStyles = {
    urgent: 'border-l-red-500 bg-red-50',
    high: 'border-l-orange-500 bg-orange-50',
    medium: 'border-l-yellow-500 bg-yellow-50',
    low: 'border-l-gray-400 bg-gray-50',
  }

  const priorityBadgeStyles = {
    urgent: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-gray-100 text-gray-800',
  }

  return (
    <div
      className={clsx(
        'p-4 rounded-lg border-l-4 shadow-sm',
        priorityStyles[priority],
      )}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={clsx(
              'w-5 h-5',
              priority === 'urgent'
                ? 'text-red-500'
                : priority === 'high'
                  ? 'text-orange-500'
                  : 'text-yellow-500',
            )}
          />
          <h3 className="font-semibold text-gray-900">{title}</h3>
        </div>
        <span
          className={clsx(
            'px-2 py-1 rounded-full text-xs font-medium capitalize',
            priorityBadgeStyles[priority],
          )}
        >
          {priority}
        </span>
      </div>

      {description && (
        <p className="text-gray-600 text-sm mb-3">{description}</p>
      )}

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          {patient && (
            <span className="mr-3">
              Patient: {patient.first_name} {patient.last_name}
            </span>
          )}
          {created_at && (
            <span>Created: {new Date(created_at).toLocaleDateString()}</span>
          )}
        </div>

        {status === 'open' && (
          <div className="flex gap-2">
            <button
              onClick={() => onDismiss?.(id)}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={() => onResolve?.(id)}
              className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              Resolve
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
