/**
 * Appointment card component for list/detail views.
 *
 * Shows appointment summary with patient info, time, status,
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
} from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

// Status badge styles
const statusStyles = {
  scheduled: 'bg-blue-100 text-blue-800',
  confirmed: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  missed: 'bg-red-100 text-red-800',
  rescheduled: 'bg-yellow-100 text-yellow-800',
  cancelled: 'bg-gray-100 text-gray-800',
}

const statusIcons = {
  scheduled: Clock,
  confirmed: CheckCircle,
  completed: CheckCircle,
  missed: AlertCircle,
  rescheduled: Calendar,
  cancelled: AlertCircle,
}

/**
 * AppointmentCard component
 * @param {Object} props
 * @param {Object} props.appointment - Appointment data
 * @param {boolean} props.compact - Show compact version
 * @param {Function} props.onInitiateCall - Callback for initiating call
 * @param {Function} props.onReschedule - Callback for rescheduling
 */
export default function AppointmentCard({
  appointment,
  compact = false,
  onInitiateCall,
  onReschedule,
}) {
  const {
    id,
    patient,
    scheduled_at,
    duration_minutes = 30,
    appointment_type,
    status,
    notes,
  } = appointment

  const StatusIcon = statusIcons[status] || Clock
  const scheduledDate = new Date(scheduled_at)

  if (compact) {
    // Compact version for lists
    return (
      <Link
        to={`/appointments/${id}`}
        className="block p-4 bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow"
      >
        <div className="flex justify-between items-start">
          <div>
            <p className="font-medium text-gray-900">
              {patient?.first_name} {patient?.last_name}
            </p>
            <p className="text-sm text-gray-500">{appointment_type}</p>
          </div>
          <span
            className={clsx(
              'px-2 py-1 rounded-full text-xs font-medium',
              statusStyles[status],
            )}
          >
            {status}
          </span>
        </div>
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {format(scheduledDate, 'h:mm a')}
          </span>
          <span>{duration_minutes} min</span>
        </div>
      </Link>
    )
  }

  // Full card version
  return (
    <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
      {/* Status header */}
      <div
        className={clsx(
          'px-4 py-2 flex items-center gap-2',
          status === 'missed'
            ? 'bg-red-50'
            : status === 'completed'
              ? 'bg-green-50'
              : 'bg-gray-50',
        )}
      >
        <StatusIcon
          className={clsx(
            'w-5 h-5',
            status === 'missed'
              ? 'text-red-500'
              : status === 'completed'
                ? 'text-green-500'
                : 'text-gray-500',
          )}
        />
        <span
          className={clsx(
            'font-medium capitalize',
            status === 'missed'
              ? 'text-red-700'
              : status === 'completed'
                ? 'text-green-700'
                : 'text-gray-700',
          )}
        >
          {status}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Patient info */}
        <div className="flex items-start gap-3 mb-4">
          <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
            <User className="w-6 h-6 text-gray-500" />
          </div>
          <div>
            <h3 className="font-semibold text-lg text-gray-900">
              {patient?.first_name} {patient?.last_name}
            </h3>
            {patient?.phone && (
              <p className="flex items-center gap-1 text-gray-600">
                <Phone className="w-4 h-4" />
                {patient.phone}
              </p>
            )}
          </div>
        </div>

        {/* Appointment details */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center gap-2 text-gray-600">
            <Calendar className="w-5 h-5" />
            <span>{format(scheduledDate, 'EEEE, MMMM d, yyyy')}</span>
          </div>
          <div className="flex items-center gap-2 text-gray-600">
            <Clock className="w-5 h-5" />
            <span>
              {format(scheduledDate, 'h:mm a')} ({duration_minutes} min)
            </span>
          </div>
          <div className="text-gray-600">
            <span className="font-medium">Type:</span> {appointment_type}
          </div>
          {notes && (
            <div className="text-gray-600">
              <span className="font-medium">Notes:</span> {notes}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-4 border-t">
          <Link
            to={`/appointments/${id}`}
            className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-center hover:bg-gray-200 transition-colors"
          >
            View Details
          </Link>

          {status === 'missed' && onInitiateCall && (
            <button
              onClick={() => onInitiateCall(appointment)}
              className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Call Patient
            </button>
          )}

          {(status === 'scheduled' || status === 'missed') && onReschedule && (
            <button
              onClick={() => onReschedule(appointment)}
              className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
            >
              Reschedule
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
