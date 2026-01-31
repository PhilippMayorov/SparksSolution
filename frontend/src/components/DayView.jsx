/**
 * Day View component for appointments.
 * 
 * Features:
 * - Single day appointment list
 * - Navigation between days
 * - View mode switcher
 * - Appointment details on click
 */

import { format, isSameDay, addDays, subDays } from 'date-fns'
import { ChevronLeft, ChevronRight, Plus, Clock, AlertCircle } from 'lucide-react'
import ViewSwitcher from './ViewSwitcher'
import { StatusBadge, getStatusColor } from './StatusBadge'

export default function DayView({ 
  appointments = [], 
  selectedDate, 
  onDateSelect, 
  onAddAppointment, 
  onEditAppointment,
  viewMode,
  onViewModeChange 
}) {
  const dayAppointments = appointments
    .filter(apt => {
      const aptDate = apt.scheduled_date
      return aptDate && isSameDay(new Date(aptDate), selectedDate)
    })
    .sort((a, b) => {
      const timeA = a.time || format(new Date(a.scheduled_date), 'HH:mm')
      const timeB = b.time || format(new Date(b.scheduled_date), 'HH:mm')
      return timeA.localeCompare(timeB)
    })

  const handlePrevDay = () => {
    onDateSelect(subDays(selectedDate, 1))
  }

  const handleNextDay = () => {
    onDateSelect(addDays(selectedDate, 1))
  }

  const isToday = isSameDay(selectedDate, new Date())

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {format(selectedDate, 'EEEE, MMMM d, yyyy')}
          </h2>
          {isToday && (
            <span className="text-sm text-blue-600 font-medium">Today</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <ViewSwitcher currentView={viewMode} onViewChange={onViewModeChange} />
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevDay}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={handleNextDay}
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

      {dayAppointments.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Clock size={32} className="text-gray-400" />
          </div>
          <p className="text-gray-500">No appointments scheduled for this day</p>
          <button
            onClick={onAddAppointment}
            className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
          >
            Add your first appointment
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {dayAppointments.map(appointment => {
            const time = format(new Date(appointment.scheduled_date), 'HH:mm')
            const patientName = appointment.patient_name
            const type = appointment.condition
            const specialist = appointment.specialist_type
            const phone = appointment.patient_phone || ''
            const notes = appointment.notes || ''
            
            return (
              <button
                key={appointment.id}
                onClick={() => onEditAppointment(appointment)}
                className={`w-full text-left border-2 rounded-lg p-5 transition-all hover:shadow-md ${getStatusColor(appointment.scheduled_date, specialist, appointment.status)}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="text-center min-w-[70px]">
                      <div className="text-xl font-bold text-gray-900">{time}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {appointment.status === 'CRITICAL' && (
                        <AlertCircle size={20} className="text-red-600" />
                      )}
                      <h3 className="text-lg font-semibold text-gray-900">{patientName}</h3>
                    </div>
                  </div>
                  <StatusBadge date={appointment.scheduled_date} type={type} status={appointment.status} />
                </div>
                
                <div className="grid grid-cols-2 gap-3 text-sm text-gray-700 ml-[82px]">
                  <div>
                    <span className="font-medium">Condition:</span> {type}
                  </div>
                  <div>
                    <span className="font-medium">Specialist:</span> {specialist}
                  </div>
                  {phone && (
                    <div>
                      <span className="font-medium">Phone:</span> {phone}
                    </div>
                  )}
                  {notes && (
                    <div className="col-span-2">
                      <span className="font-medium">Notes:</span> {notes}
                    </div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}

      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Total appointments: <strong>{dayAppointments.length}</strong></span>
          {dayAppointments.length > 0 && (
            <span>
              {format(new Date(dayAppointments[0].scheduled_date), 'HH:mm')} - {format(new Date(dayAppointments[dayAppointments.length - 1].scheduled_date), 'HH:mm')}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
