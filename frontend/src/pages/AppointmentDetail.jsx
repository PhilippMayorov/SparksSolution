/**
 * Appointment detail page.
 *
 * Shows full appointment details with:
 * - Patient information
 * - Appointment status and history
 * - Call attempts history
 * - Actions: reschedule, cancel, initiate call
 * - Calendar sync status
 */

import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  ArrowLeft,
  Calendar,
  Clock,
  User,
  Phone,
  Mail,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  X,
} from 'lucide-react'
import {
  getAppointment,
  rescheduleAppointment,
  cancelAppointment,
  initiateCall,
  syncToCalendar,
  getCalendarSyncStatus,
} from '../api/client'
import { useState } from 'react'

export default function AppointmentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showReschedule, setShowReschedule] = useState(false)
  const [newDateTime, setNewDateTime] = useState('')
  const [rescheduleReason, setRescheduleReason] = useState('')

  // Fetch appointment
  const {
    data: appointment,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['appointments', id],
    queryFn: () => getAppointment(id),
    enabled: !!id,
  })

  // Fetch calendar sync status
  const { data: syncStatus } = useQuery({
    queryKey: ['calendar-sync', id],
    queryFn: () => getCalendarSyncStatus(id),
    enabled: !!id,
  })

  // Reschedule mutation
  const rescheduleMutation = useMutation({
    mutationFn: ({ newDatetime, reason }) =>
      rescheduleAppointment(id, newDatetime, reason),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments', id])
      setShowReschedule(false)
      // TODO: Show success toast
    },
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => cancelAppointment(id),
    onSuccess: () => {
      navigate('/')
    },
  })

  // Call mutation
  const callMutation = useMutation({
    mutationFn: () =>
      initiateCall(id, appointment.patient_id || appointment.patient?.id),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments', id])
      // TODO: Show success toast
    },
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => syncToCalendar(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['calendar-sync', id])
      queryClient.invalidateQueries(['appointments', id])
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !appointment) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900">
          Appointment not found
        </h2>
        <Link
          to="/"
          className="text-primary-500 hover:underline mt-2 inline-block"
        >
          Return to dashboard
        </Link>
      </div>
    )
  }

  const {
    patient,
    scheduled_at,
    duration_minutes,
    appointment_type,
    status,
    notes,
  } = appointment
  const scheduledDate = new Date(scheduled_at)

  const statusColors = {
    scheduled: 'bg-blue-100 text-blue-800',
    confirmed: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    missed: 'bg-red-100 text-red-800',
    rescheduled: 'bg-yellow-100 text-yellow-800',
    cancelled: 'bg-gray-100 text-gray-800',
  }

  const handleReschedule = () => {
    if (!newDateTime) return
    rescheduleMutation.mutate({
      newDatetime: new Date(newDateTime).toISOString(),
      reason: rescheduleReason || null,
    })
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back button */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      {/* Main card */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        {/* Status header */}
        <div
          className={`
          px-6 py-4 flex items-center justify-between
          ${
            status === 'missed'
              ? 'bg-red-50'
              : status === 'completed'
                ? 'bg-green-50'
                : 'bg-gray-50'
          }
        `}
        >
          <div className="flex items-center gap-3">
            {status === 'completed' ? (
              <CheckCircle className="w-6 h-6 text-green-500" />
            ) : status === 'missed' ? (
              <AlertCircle className="w-6 h-6 text-red-500" />
            ) : (
              <Clock className="w-6 h-6 text-gray-500" />
            )}
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[status]}`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
          </div>

          {/* Calendar sync status */}
          <div className="flex items-center gap-2">
            {syncStatus?.synced ? (
              <span className="flex items-center gap-1 text-sm text-green-600">
                <CheckCircle className="w-4 h-4" />
                Synced to Calendar
              </span>
            ) : (
              <button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="flex items-center gap-1 text-sm text-primary-500 hover:text-primary-600"
              >
                <RefreshCw
                  className={`w-4 h-4 ${syncMutation.isPending ? 'animate-spin' : ''}`}
                />
                Sync to Calendar
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Patient info */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Patient Information
              </h2>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                    <User className="w-8 h-8 text-gray-500" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold text-gray-900">
                      {patient?.first_name} {patient?.last_name}
                    </p>
                    <p className="text-gray-500">Patient</p>
                  </div>
                </div>

                {patient?.phone && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Phone className="w-5 h-5" />
                    <a
                      href={`tel:${patient.phone}`}
                      className="hover:text-primary-500"
                    >
                      {patient.phone}
                    </a>
                  </div>
                )}

                {patient?.email && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Mail className="w-5 h-5" />
                    <a
                      href={`mailto:${patient.email}`}
                      className="hover:text-primary-500"
                    >
                      {patient.email}
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Appointment details */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Appointment Details
              </h2>
              <div className="space-y-3">
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
                    <span className="font-medium">Notes:</span>
                    <p className="mt-1 text-sm bg-gray-50 p-3 rounded">
                      {notes}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Reschedule form */}
          {showReschedule && (
            <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <h3 className="font-semibold text-gray-900 mb-3">
                Reschedule Appointment
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Date & Time
                  </label>
                  <input
                    type="datetime-local"
                    value={newDateTime}
                    onChange={(e) => setNewDateTime(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Reason (optional)
                  </label>
                  <input
                    type="text"
                    value={rescheduleReason}
                    onChange={(e) => setRescheduleReason(e.target.value)}
                    placeholder="e.g., Patient requested new time"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleReschedule}
                    disabled={!newDateTime || rescheduleMutation.isPending}
                    className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
                  >
                    {rescheduleMutation.isPending
                      ? 'Saving...'
                      : 'Confirm Reschedule'}
                  </button>
                  <button
                    onClick={() => setShowReschedule(false)}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="mt-8 pt-6 border-t flex flex-wrap gap-3">
            {status === 'missed' && (
              <button
                onClick={() => callMutation.mutate()}
                disabled={callMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50"
              >
                <Phone className="w-4 h-4" />
                {callMutation.isPending ? 'Initiating...' : 'Call Patient'}
              </button>
            )}

            {(status === 'scheduled' || status === 'missed') &&
              !showReschedule && (
                <button
                  onClick={() => setShowReschedule(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                >
                  <Calendar className="w-4 h-4" />
                  Reschedule
                </button>
              )}

            {status !== 'cancelled' && status !== 'completed' && (
              <button
                onClick={() => {
                  if (
                    confirm('Are you sure you want to cancel this appointment?')
                  ) {
                    cancelMutation.mutate()
                  }
                }}
                disabled={cancelMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                Cancel Appointment
              </button>
            )}
          </div>
        </div>
      </div>

      {/* TODO: Call history section */}
      {/* TODO: Activity timeline */}
    </div>
  )
}
