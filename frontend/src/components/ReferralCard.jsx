/**
 * Referral card component for list/detail views.
 *
 * Shows referral summary with patient info, time, status,
 * and action buttons based on status.
 */

import { format } from 'date-fns'
import {
  Clock,
  User,
  Phone,
  Calendar,
  AlertCircle,
  CheckCircle,
  ChevronRight,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

// Status badge styles
const statusStyles = {
  PENDING: 'bg-gray-100 text-gray-700 border-gray-200',
  SCHEDULED: 'bg-blue-100 text-blue-700 border-blue-200',
  ATTENDED: 'bg-green-100 text-green-700 border-green-200',
  MISSED: 'bg-red-100 text-red-700 border-red-200',
  NEEDS_REBOOK: 'bg-amber-100 text-amber-700 border-amber-200',
  ESCALATED: 'bg-purple-100 text-purple-700 border-purple-200',
  COMPLETED: 'bg-green-100 text-green-700 border-green-200',
  CANCELLED: 'bg-gray-100 text-gray-600 border-gray-200',
}

const statusIcons = {
  PENDING: Clock,
  SCHEDULED: Clock,
  ATTENDED: CheckCircle,
  COMPLETED: CheckCircle,
  MISSED: AlertCircle,
  NEEDS_REBOOK: Calendar,
  ESCALATED: AlertCircle,
  CANCELLED: AlertCircle,
}

// Specialist type colors
const typeColors = {
  CARDIOLOGY: 'border-l-red-500',
  ORTHOPEDICS: 'border-l-blue-500',
  NEUROLOGY: 'border-l-purple-500',
  DERMATOLOGY: 'border-l-pink-500',
  OPHTHALMOLOGY: 'border-l-indigo-500',
  ENDOCRINOLOGY: 'border-l-green-500',
  PSYCHIATRY: 'border-l-teal-500',
  OTHER: 'border-l-gray-400',
}

/**
 * ReferralCard component
 * @param {Object} props
 * @param {Object} props.referral - Referral data
 * @param {boolean} props.compact - Show compact version
 * @param {Function} props.onInitiateCall - Callback for initiating call
 * @param {Function} props.onReschedule - Callback for rescheduling
 */
export default function ReferralCard({
  referral,
  compact = false,
  onInitiateCall,
  onReschedule,
}) {
  const {
    id,
    patient_name,
    patient_phone,
    scheduled_date,
    specialist_type,
    status,
    notes,
  } = referral

  const StatusIcon = statusIcons[status] || Clock
  const scheduledDate = scheduled_date ? new Date(scheduled_date) : null
  const typeColor = typeColors[specialist_type] || 'border-l-gray-400'

  // Get initials from patient name
  const getInitials = (name) => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    if (parts.length === 1) return parts[0][0]
    return parts[0][0] + parts[parts.length - 1][0]
  }

  if (compact) {
    // Compact version for lists
    return (
      <Link
        to={`/referrals/${id}`}
        className={clsx(
          'block p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all group border-l-4',
          typeColor,
        )}
      >
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600 font-semibold text-sm">
                {getInitials(patient_name)}
              </span>
            </div>
            <div>
              <p className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                {patient_name}
              </p>
              <p className="text-sm text-gray-500 capitalize">
                {specialist_type}
              </p>
            </div>
          </div>
          <span
            className={clsx(
              'px-2.5 py-1 rounded-full text-xs font-medium border capitalize',
              statusStyles[status],
            )}
          >
            {status}
          </span>
        </div>
        {scheduledDate && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-gray-400" />
                {format(scheduledDate, 'h:mm a')}
              </span>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
          </div>
        )}
      </Link>
    )
  }

  // Full card version
  return (
    <div
      className={clsx(
        'bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-all border-l-4',
        typeColor,
      )}
    >
      {/* Status header */}
      <div
        className={clsx(
          'px-5 py-3 flex items-center gap-2 border-b',
          status === 'MISSED'
            ? 'bg-red-50 border-red-100'
            : status === 'COMPLETED' || status === 'ATTENDED'
              ? 'bg-green-50 border-green-100'
              : 'bg-gray-50 border-gray-100',
        )}
      >
        <StatusIcon
          className={clsx(
            'w-5 h-5',
            status === 'MISSED'
              ? 'text-red-500'
              : status === 'COMPLETED' || status === 'ATTENDED'
                ? 'text-green-500'
                : 'text-gray-500',
          )}
        />
        <span
          className={clsx(
            'font-medium capitalize',
            status === 'MISSED'
              ? 'text-red-700'
              : status === 'COMPLETED' || status === 'ATTENDED'
                ? 'text-green-700'
                : 'text-gray-700',
          )}
        >
          {status}
        </span>
      </div>

      {/* Content */}
      <div className="p-5">
        {/* Patient info */}
        <div className="flex items-start gap-4 mb-5">
          <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-blue-600 font-bold text-lg">
              {getInitials(patient_name)}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              {patient_name}
            </h3>
            {patient_phone && (
              <p className="flex items-center gap-2 text-gray-600 mt-1">
                <Phone className="w-4 h-4 text-gray-400" />
                {patient_phone}
              </p>
            )}
          </div>
        </div>

        {/* Referral details */}
        <div className="space-y-3 mb-5 p-4 bg-gray-50 rounded-xl">
          {scheduledDate && (
            <>
              <div className="flex items-center gap-3 text-gray-700">
                <Calendar className="w-5 h-5 text-gray-400" />
                <span>{format(scheduledDate, 'EEEE, MMMM d, yyyy')}</span>
              </div>
              <div className="flex items-center gap-3 text-gray-700">
                <Clock className="w-5 h-5 text-gray-400" />
                <span>{format(scheduledDate, 'h:mm a')}</span>
              </div>
            </>
          )}
          <div className="text-gray-700">
            <span className="font-medium text-gray-500">Specialist:</span>{' '}
            <span className="capitalize">{specialist_type}</span>
          </div>
          {notes && (
            <div className="text-gray-700">
              <span className="font-medium text-gray-500">Notes:</span> {notes}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t border-gray-100">
          <Link
            to={`/referrals/${id}`}
            className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl text-center font-medium hover:bg-gray-200 transition-colors"
          >
            View Details
          </Link>

          {status === 'MISSED' && onInitiateCall && (
            <button
              onClick={() => onInitiateCall(referral)}
              className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors shadow-sm"
            >
              Call Patient
            </button>
          )}

          {(status === 'SCHEDULED' || status === 'MISSED') && onReschedule && (
            <button
              onClick={() => onReschedule(referral)}
              className="flex-1 px-4 py-2.5 bg-amber-500 text-white rounded-xl font-medium hover:bg-amber-600 transition-colors shadow-sm"
            >
              Reschedule
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
