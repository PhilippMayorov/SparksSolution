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
        urgentCount > 0
          ? 'bg-gradient-to-r from-red-600 to-red-500'
          : 'bg-gradient-to-r from-amber-500 to-amber-400',
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center',
            urgentCount > 0 ? 'bg-white/20' : 'bg-white/25',
          )}
        >
          <AlertTriangle className="w-5 h-5 text-white" />
        </div>
        <div className="text-white">
          <span className="font-semibold">
            {flags.length} {flags.length === 1 ? 'flag' : 'flags'} need
            attention
          </span>
          <span className="ml-2 text-white/80 text-sm">
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
            'flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition-all shadow-sm',
            urgentCount > 0
              ? 'bg-white text-red-600 hover:bg-red-50'
              : 'bg-white text-amber-600 hover:bg-amber-50',
          )}
        >
          View Flags
          <ChevronRight className="w-4 h-4" />
        </Link>

        <button
          onClick={() => setDismissed(true)}
          className="p-2 rounded-lg hover:bg-white/20 text-white transition-colors"
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
    urgent: 'border-l-red-500 bg-gradient-to-r from-red-50 to-white',
    high: 'border-l-orange-500 bg-gradient-to-r from-orange-50 to-white',
    medium: 'border-l-amber-500 bg-gradient-to-r from-amber-50 to-white',
    low: 'border-l-gray-400 bg-gradient-to-r from-gray-50 to-white',
  }

  const priorityBadgeStyles = {
    urgent: 'bg-red-100 text-red-700 border-red-200',
    high: 'bg-orange-100 text-orange-700 border-orange-200',
    medium: 'bg-amber-100 text-amber-700 border-amber-200',
    low: 'bg-gray-100 text-gray-600 border-gray-200',
  }

  return (
    <div
      className={clsx(
        'p-5 rounded-2xl border-l-4 border border-gray-200 shadow-sm hover:shadow-md transition-all',
        priorityStyles[priority],
      )}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              'w-10 h-10 rounded-xl flex items-center justify-center',
              priority === 'urgent'
                ? 'bg-red-100'
                : priority === 'high'
                  ? 'bg-orange-100'
                  : priority === 'medium'
                    ? 'bg-amber-100'
                    : 'bg-gray-100',
            )}
          >
            <AlertTriangle
              className={clsx(
                'w-5 h-5',
                priority === 'urgent'
                  ? 'text-red-500'
                  : priority === 'high'
                    ? 'text-orange-500'
                    : priority === 'medium'
                      ? 'text-amber-500'
                      : 'text-gray-500',
              )}
            />
          </div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
        </div>
        <span
          className={clsx(
            'px-3 py-1 rounded-full text-xs font-semibold capitalize border',
            priorityBadgeStyles[priority],
          )}
        >
          {priority}
        </span>
      </div>

      {description && (
        <p className="text-gray-600 text-sm mb-4 ml-13 pl-13">{description}</p>
      )}

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          {patient && (
            <span className="mr-3">
              Patient:{' '}
              <span className="font-medium text-gray-700">
                {patient.first_name} {patient.last_name}
              </span>
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
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={() => onResolve?.(id)}
              className="px-4 py-2 text-sm font-medium bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors shadow-sm"
            >
              Resolve
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
