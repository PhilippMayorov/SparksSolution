/**
 * Month Calendar component.
 * 
 * Features:
 * - Full month view with navigation
 * - View mode switcher (day/week/month)
 * - Add appointment button
 * - Appointment indicators on days
 */

import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, addMonths, subMonths, startOfWeek, endOfWeek } from 'date-fns'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import ViewSwitcher from './ViewSwitcher'

export default function MonthCalendar({ 
  appointments = [], 
  selectedDate, 
  onDateSelect, 
  onMonthChange, 
  onAddAppointment,
  viewMode,
  onViewModeChange 
}) {
  const monthStart = startOfMonth(selectedDate)
  const monthEnd = endOfMonth(selectedDate)
  const calendarStart = startOfWeek(monthStart)
  const calendarEnd = endOfWeek(monthEnd)
  
  const days = eachDayOfInterval({ start: calendarStart, end: calendarEnd })
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  const getAppointmentsForDay = (date) => {
    return appointments.filter(apt => {
      const aptDate = apt.scheduled_at || apt.date
      return aptDate && isSameDay(new Date(aptDate), date)
    })
  }

  const getAppointmentColor = (type) => {
    const colors = {
      'consultation': 'bg-blue-100 text-blue-800 border-blue-200',
      'follow-up': 'bg-green-100 text-green-800 border-green-200',
      'check-up': 'bg-purple-100 text-purple-800 border-purple-200',
      'vaccination': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'treatment': 'bg-pink-100 text-pink-800 border-pink-200',
      'emergency': 'bg-red-100 text-red-800 border-red-200',
    }
    return colors[type?.toLowerCase()] || 'bg-gray-100 text-gray-800 border-gray-200'
  }

  const handlePrevMonth = () => {
    onMonthChange(subMonths(selectedDate, 1))
  }

  const handleNextMonth = () => {
    onMonthChange(addMonths(selectedDate, 1))
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          {format(selectedDate, 'MMMM yyyy')}
        </h2>
        <div className="flex items-center gap-4">
          <ViewSwitcher currentView={viewMode} onViewChange={onViewModeChange} />
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevMonth}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={handleNextMonth}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronRight size={20} />
            </button>
            <button
              onClick={onAddAppointment}
              className="ml-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus size={18} />
              Add Appointment
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-2">
        {weekDays.map(day => (
          <div key={day} className="text-center text-sm font-semibold text-gray-600 py-2">
            {day}
          </div>
        ))}
        
        {days.map(day => {
          const dayAppointments = getAppointmentsForDay(day)
          const isCurrentMonth = isSameMonth(day, selectedDate)
          const isSelected = isSameDay(day, selectedDate)
          const isToday = isSameDay(day, new Date())

          return (
            <button
              key={day.toISOString()}
              onClick={() => onDateSelect(day)}
              className={`
                min-h-[100px] p-2 border rounded-lg text-left transition-all
                ${isCurrentMonth ? 'bg-white' : 'bg-gray-50'}
                ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-200'}
                ${!isCurrentMonth ? 'text-gray-400' : 'text-gray-900'}
                hover:border-blue-300
              `}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-sm font-medium ${isToday ? 'bg-blue-600 text-white w-6 h-6 flex items-center justify-center rounded-full' : ''}`}>
                  {format(day, 'd')}
                </span>
              </div>
              
              <div className="space-y-1">
                {dayAppointments.slice(0, 2).map(apt => (
                  <div
                    key={apt.id}
                    className={`text-xs px-2 py-1 rounded truncate border ${getAppointmentColor(apt.type || apt.appointment_type)}`}
                  >
                    {apt.time || format(new Date(apt.scheduled_at), 'HH:mm')} - {apt.patientName || apt.patient?.first_name || 'Patient'}
                  </div>
                ))}
                {dayAppointments.length > 2 && (
                  <div className="text-xs text-gray-500 px-2">
                    +{dayAppointments.length - 2} more
                  </div>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
