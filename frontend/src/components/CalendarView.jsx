/**
 * Calendar view component using react-big-calendar.
 *
 * Displays appointments in week/day/month views.
 * Color-coded by appointment status:
 * - Blue: Scheduled
 * - Green: Completed
 * - Red: Missed
 * - Yellow: Rescheduled
 */

import { useMemo, useState, useCallback } from 'react'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { useNavigate } from 'react-router-dom'
import 'react-big-calendar/lib/css/react-big-calendar.css'

// Setup date-fns localizer
const locales = { 'en-US': enUS }
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
})

// Status to color mapping
const statusColors = {
  scheduled: '#3b82f6', // Blue
  confirmed: '#3b82f6',
  completed: '#22c55e', // Green
  missed: '#ef4444', // Red
  rescheduled: '#f59e0b', // Yellow
  cancelled: '#9ca3af', // Gray
}

/**
 * CalendarView component
 * @param {Object} props
 * @param {Array} props.appointments - Array of appointment objects
 * @param {Function} props.onSelectDate - Callback when date is selected
 * @param {Function} props.onSelectAppointment - Callback when appointment is clicked
 */
export default function CalendarView({
  appointments = [],
  onSelectDate,
  onSelectAppointment,
}) {
  const navigate = useNavigate()
  const [view, setView] = useState('week')
  const [date, setDate] = useState(new Date())

  // Transform appointments to calendar events
  const events = useMemo(() => {
    return appointments.map((apt) => ({
      id: apt.id,
      title: `${apt.appointment_type} - ${apt.patient?.first_name || 'Patient'} ${apt.patient?.last_name || ''}`,
      start: new Date(apt.scheduled_at),
      end: new Date(
        new Date(apt.scheduled_at).getTime() +
          (apt.duration_minutes || 30) * 60000,
      ),
      status: apt.status,
      resource: apt, // Store full appointment data
    }))
  }, [appointments])

  // Custom event styling
  const eventStyleGetter = useCallback((event) => {
    const backgroundColor = statusColors[event.status] || statusColors.scheduled
    return {
      style: {
        backgroundColor,
        borderRadius: '4px',
        opacity: event.status === 'cancelled' ? 0.5 : 1,
        color: 'white',
        border: 'none',
        display: 'block',
      },
    }
  }, [])

  // Handle event click
  const handleSelectEvent = useCallback(
    (event) => {
      if (onSelectAppointment) {
        onSelectAppointment(event.resource)
      } else {
        navigate(`/appointments/${event.id}`)
      }
    },
    [navigate, onSelectAppointment],
  )

  // Handle slot selection (clicking on empty time)
  const handleSelectSlot = useCallback(
    ({ start }) => {
      if (onSelectDate) {
        onSelectDate(start)
      }
    },
    [onSelectDate],
  )

  return (
    <div className="h-[700px] bg-white rounded-lg shadow-sm p-4">
      {/* Legend */}
      <div className="flex gap-4 mb-4 text-sm">
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: statusColors.scheduled }}
          />
          <span>Scheduled</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: statusColors.completed }}
          />
          <span>Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: statusColors.missed }}
          />
          <span>Missed</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: statusColors.rescheduled }}
          />
          <span>Rescheduled</span>
        </div>
      </div>

      <Calendar
        localizer={localizer}
        events={events}
        startAccessor="start"
        endAccessor="end"
        view={view}
        onView={setView}
        date={date}
        onNavigate={setDate}
        onSelectEvent={handleSelectEvent}
        onSelectSlot={handleSelectSlot}
        selectable
        eventPropGetter={eventStyleGetter}
        views={['month', 'week', 'day']}
        defaultView="week"
        min={new Date(0, 0, 0, 7, 0, 0)} // 7 AM
        max={new Date(0, 0, 0, 19, 0, 0)} // 7 PM
        step={15}
        timeslots={4}
      />
    </div>
  )
}
