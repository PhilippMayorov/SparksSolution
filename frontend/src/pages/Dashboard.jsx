/**
 * Dashboard page with calendar view.
 *
 * Main landing page for nurses showing:
 * - Today's appointments overview
 * - Weekly calendar view
 * - Quick access to missed appointments
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfWeek, endOfWeek, addDays } from 'date-fns'
import { Calendar, AlertCircle, Phone, RefreshCw } from 'lucide-react'
import CalendarView from '../components/CalendarView'
import AppointmentCard from '../components/AppointmentCard'
import {
  getAppointmentsByDate,
  getAppointmentsByStatus,
  initiateCall,
} from '../api/client'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [selectedDate, setSelectedDate] = useState(new Date())

  // Fetch appointments for current week
  const weekStart = startOfWeek(selectedDate)
  const weekEnd = endOfWeek(selectedDate)

  // Fetch today's appointments
  const todayStr = format(new Date(), 'yyyy-MM-dd')
  const { data: todayAppointments = [], isLoading: loadingToday } = useQuery({
    queryKey: ['appointments', 'date', todayStr],
    queryFn: () => getAppointmentsByDate(todayStr),
  })

  // Fetch missed appointments
  const { data: missedAppointments = [], isLoading: loadingMissed } = useQuery({
    queryKey: ['appointments', 'status', 'missed'],
    queryFn: () => getAppointmentsByStatus('missed'),
  })

  // Fetch all appointments for calendar (week view)
  // TODO: Implement date range query
  const { data: weekAppointments = [] } = useQuery({
    queryKey: ['appointments', 'week', format(weekStart, 'yyyy-MM-dd')],
    queryFn: async () => {
      // Fetch each day of the week
      const days = []
      for (let i = 0; i < 7; i++) {
        const date = format(addDays(weekStart, i), 'yyyy-MM-dd')
        const appointments = await getAppointmentsByDate(date)
        days.push(...appointments)
      }
      return days
    },
  })

  // Initiate call mutation
  const callMutation = useMutation({
    mutationFn: ({ appointmentId, patientId }) =>
      initiateCall(appointmentId, patientId),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments'])
      // TODO: Show success notification
    },
    onError: (error) => {
      // TODO: Show error notification
      console.error('Failed to initiate call:', error)
    },
  })

  // Stats for today
  const stats = useMemo(
    () => ({
      total: todayAppointments.length,
      completed: todayAppointments.filter((a) => a.status === 'completed')
        .length,
      missed: missedAppointments.length,
      upcoming: todayAppointments.filter(
        (a) =>
          a.status === 'scheduled' && new Date(a.scheduled_at) > new Date(),
      ).length,
    }),
    [todayAppointments, missedAppointments],
  )

  const handleInitiateCall = (appointment) => {
    callMutation.mutate({
      appointmentId: appointment.id,
      patientId: appointment.patient_id || appointment.patient?.id,
    })
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">
            {format(new Date(), 'EEEE, MMMM d, yyyy')}
          </p>
        </div>

        <button
          onClick={() => queryClient.invalidateQueries(['appointments'])}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Calendar}
          label="Today's Appointments"
          value={stats.total}
          color="blue"
        />
        <StatCard
          icon={Calendar}
          label="Upcoming"
          value={stats.upcoming}
          color="green"
        />
        <StatCard
          icon={AlertCircle}
          label="Missed (needs call)"
          value={stats.missed}
          color="red"
          alert={stats.missed > 0}
        />
        <StatCard
          icon={Calendar}
          label="Completed"
          value={stats.completed}
          color="gray"
        />
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Calendar - takes 2 columns */}
        <div className="lg:col-span-2">
          <CalendarView
            appointments={weekAppointments}
            onSelectDate={setSelectedDate}
          />
        </div>

        {/* Side panel */}
        <div className="space-y-6">
          {/* Missed appointments alert */}
          {missedAppointments.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-red-500" />
                <h2 className="font-semibold text-red-800">
                  Missed Appointments ({missedAppointments.length})
                </h2>
              </div>
              <div className="space-y-2">
                {missedAppointments.slice(0, 3).map((apt) => (
                  <div
                    key={apt.id}
                    className="flex items-center justify-between bg-white p-2 rounded border"
                  >
                    <div>
                      <p className="font-medium text-sm">
                        {apt.patient?.first_name} {apt.patient?.last_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {format(new Date(apt.scheduled_at), 'MMM d, h:mm a')}
                      </p>
                    </div>
                    <button
                      onClick={() => handleInitiateCall(apt)}
                      disabled={callMutation.isPending}
                      className="flex items-center gap-1 px-2 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50"
                    >
                      <Phone className="w-3 h-3" />
                      Call
                    </button>
                  </div>
                ))}
                {missedAppointments.length > 3 && (
                  <p className="text-sm text-red-600 text-center">
                    +{missedAppointments.length - 3} more
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Today's schedule */}
          <div>
            <h2 className="font-semibold text-gray-900 mb-3">
              Today's Schedule
            </h2>
            {loadingToday ? (
              <p className="text-gray-500">Loading...</p>
            ) : todayAppointments.length === 0 ? (
              <p className="text-gray-500">No appointments today</p>
            ) : (
              <div className="space-y-3">
                {todayAppointments
                  .sort(
                    (a, b) =>
                      new Date(a.scheduled_at) - new Date(b.scheduled_at),
                  )
                  .map((apt) => (
                    <AppointmentCard key={apt.id} appointment={apt} compact />
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Stat card component
function StatCard({ icon: Icon, label, value, color = 'gray', alert = false }) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    gray: 'bg-gray-50 text-gray-600',
  }

  return (
    <div
      className={`
      p-4 rounded-lg border
      ${alert ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'}
    `}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  )
}
