/**
 * Appointment Modal for creating/editing appointments.
 * 
 * Features:
 * - Form for appointment details
 * - Patient info, date, time, type
 * - Edit mode with pre-filled data
 * - Backend API integration
 */

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { format } from 'date-fns'

export default function AppointmentModal({ 
  isOpen, 
  onClose, 
  onSave, 
  appointment, 
  selectedDate,
  isLoading 
}) {
  const [patientName, setPatientName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [doctor, setDoctor] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [type, setType] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (appointment) {
      const patient = appointment.patient || {}
      setPatientName(appointment.patientName || `${patient.first_name || ''} ${patient.last_name || ''}`.trim())
      setPhoneNumber(appointment.phoneNumber || patient.phone || '')
      setDoctor(appointment.doctor || '')
      setDate(appointment.date ? format(new Date(appointment.date), 'yyyy-MM-dd') : 
              appointment.scheduled_at ? format(new Date(appointment.scheduled_at), 'yyyy-MM-dd') : '')
      setTime(appointment.time || (appointment.scheduled_at ? format(new Date(appointment.scheduled_at), 'HH:mm') : ''))
      setType(appointment.type || appointment.appointment_type || 'Consultation')
      setNotes(appointment.notes || '')
    } else {
      setPatientName('')
      setPhoneNumber('')
      setDoctor('Dr. Smith')
      setDate(selectedDate ? format(selectedDate, 'yyyy-MM-dd') : format(new Date(), 'yyyy-MM-dd'))
      setTime('09:00')
      setType('Consultation')
      setNotes('')
    }
  }, [appointment, selectedDate, isOpen])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      patientName,
      phoneNumber,
      doctor,
      date: new Date(date),
      time,
      type,
      notes,
      // For backend API
      scheduled_at: `${date}T${time}:00`,
      appointment_type: type.toLowerCase(),
    })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {appointment ? 'Edit Appointment' : 'New Appointment'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Patient Name
            </label>
            <input
              type="text"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter patient name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="(555) 123-4567"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Doctor / Specialist
            </label>
            <select
              value={doctor}
              onChange={(e) => setDoctor(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Dr. Smith">Dr. Smith</option>
              <option value="Dr. Johnson">Dr. Johnson</option>
              <option value="Dr. Williams">Dr. Williams</option>
              <option value="Dr. Brown">Dr. Brown</option>
              <option value="Dr. Davis">Dr. Davis</option>
              <option value="Dr. Martinez">Dr. Martinez</option>
              <option value="Dr. Chen">Dr. Chen</option>
              <option value="Dr. Torres">Dr. Torres</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time
            </label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Appointment Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Consultation">Consultation</option>
              <option value="Follow-up">Follow-up</option>
              <option value="Check-up">Check-up</option>
              <option value="Vaccination">Vaccination</option>
              <option value="Treatment">Treatment</option>
              <option value="Cardiology">Cardiology</option>
              <option value="Orthopedics">Orthopedics</option>
              <option value="Mental Health">Mental Health</option>
              <option value="Dermatology">Dermatology</option>
              <option value="Emergency">Emergency</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Additional notes..."
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : (appointment ? 'Save Changes' : 'Add Appointment')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
