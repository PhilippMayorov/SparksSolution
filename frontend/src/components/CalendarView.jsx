/**
 * Calendar view component using react-big-calendar.
 *
 * Displays referrals in week/day/month views.
 * Color-coded by referral status:
 * - Blue: Scheduled
 * - Green: Completed/Attended
 * - Red: Missed
 * - Purple: Escalated
 */

import { useMemo, useState, useCallback } from 'react'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import { enUS } from 'date-fns/locale'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
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

// Status to color mapping (uppercase to match schema)
const statusColors = {
  PENDING: { bg: '#9ca3af', text: 'Pending' },
  SCHEDULED: { bg: '#3b82f6', text: 'Scheduled' },
  ATTENDED: { bg: '#22c55e', text: 'Attended' },
  COMPLETED: { bg: '#22c55e', text: 'Completed' },
  MISSED: { bg: '#ef4444', text: 'Missed' },
  NEEDS_REBOOK: { bg: '#f59e0b', text: 'Needs Rebook' },
  ESCALATED: { bg: '#a855f7', text: 'Escalated' },
  CANCELLED: { bg: '#9ca3af', text: 'Cancelled' },
}

/**
 * CalendarView component
 * @param {Object} props
 * @param {Array} props.referrals - Array of referral objects
 * @param {Function} props.onSelectDate - Callback when date is selected
 * @param {Function} props.onSelectReferral - Callback when referral is clicked
 */
export default function CalendarView({
  referrals = [],
  onSelectDate,
  onSelectReferral,
}) {
  const navigate = useNavigate()
  const [view, setView] = useState('week')
  const [date, setDate] = useState(new Date())

  // Transform referrals to calendar events
  const events = useMemo(() => {
    return referrals
      .filter((ref) => ref.scheduled_date) // Only show scheduled referrals
      .map((ref) => {
        const startDate = new Date(ref.scheduled_date)
        // Default 60 min duration for referrals
        const endDate = new Date(startDate.getTime() + 60 * 60000)

        return {
          id: ref.id,
          title: `${ref.specialist_type} - ${ref.patient_name || 'Patient'}`,
          start: startDate,
          end: endDate,
          status: ref.status,
          type: ref.specialist_type,
          resource: ref,
        }
      })
  }, [referrals])

  // Custom event styling
  const eventStyleGetter = useCallback((event) => {
    const backgroundColor =
      statusColors[event.status]?.bg || statusColors.SCHEDULED.bg
    return {
      style: {
        backgroundColor,
        borderRadius: '8px',
        opacity: event.status === 'CANCELLED' ? 0.5 : 1,
        color: 'white',
        border: 'none',
        display: 'block',
        fontSize: '12px',
        fontWeight: '500',
        padding: '2px 8px',
      },
    }
  }, [])

  // Handle event click
  const handleSelectEvent = useCallback(
    (event) => {
      if (onSelectReferral) {
        onSelectReferral(event.resource)
      } else {
        navigate(`/referrals/${event.id}`)
      }
    },
    [navigate, onSelectReferral],
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

  // Custom toolbar component
  const CustomToolbar = ({ label, onNavigate, onView, view: currentView }) => (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center bg-gray-100 rounded-xl p-1">
          <button
            onClick={() => onNavigate('PREV')}
            className="p-2 rounded-lg hover:bg-white hover:shadow-sm transition-all"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <button
            onClick={() => onNavigate('TODAY')}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-white hover:shadow-sm rounded-lg transition-all"
          >
            Today
          </button>
          <button
            onClick={() => onNavigate('NEXT')}
            className="p-2 rounded-lg hover:bg-white hover:shadow-sm transition-all"
          >
            <ChevronRight className="w-5 h-5 text-gray-600" />
          </button>
        </div>
        <h2 className="text-lg font-semibold text-gray-900">{label}</h2>
      </div>

      <div className="flex items-center gap-2">
        {/* View switcher */}
        <div className="flex bg-gray-100 rounded-xl p-1">
          {['day', 'week', 'month'].map((v) => (
            <button
              key={v}
              onClick={() => onView(v)}
              className={`
                px-4 py-2 text-sm font-medium rounded-lg transition-all capitalize
                ${
                  currentView === v
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-600 hover:bg-white hover:shadow-sm'
                }
              `}
            >
              {v}
            </button>
          ))}
        </div>

        {/* Add referral button */}
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Add Referral</span>
        </button>
      </div>
    </div>
  )

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 pb-4 border-b border-gray-100">
        {Object.entries(statusColors).map(([status, { bg, text }]) => (
          <div key={status} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: bg }}
            />
            <span className="text-sm text-gray-600">{text}</span>
          </div>
        ))}
      </div>

      <div className="h-[600px]">
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
          min={new Date(0, 0, 0, 7, 0, 0)}
          max={new Date(0, 0, 0, 19, 0, 0)}
          step={15}
          timeslots={4}
          components={{
            toolbar: CustomToolbar,
          }}
        />
      </div>
    </div>
  )
}
