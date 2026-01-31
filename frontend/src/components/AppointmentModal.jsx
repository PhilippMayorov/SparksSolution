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
  const [patientDob, setPatientDob] = useState('')
  const [healthCardNumber, setHealthCardNumber] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [patientEmail, setPatientEmail] = useState('')
  const [specialistType, setSpecialistType] = useState('')
  const [date, setDate] = useState('')
  const [condition, setCondition] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (appointment) {
      setPatientName(appointment.patient_name || '')
      setPatientDob(appointment.patient_dob || '')
      setHealthCardNumber(appointment.health_card_number || '')
      setPhoneNumber(appointment.patient_phone || '')
      setPatientEmail(appointment.patient_email || '')
      setSpecialistType(appointment.specialist_type || '')
      setDate(appointment.scheduled_date ? format(new Date(appointment.scheduled_date), 'yyyy-MM-dd') : '')
      setCondition(appointment.condition || '')
      setNotes(appointment.notes || '')
    } else {
      setPatientName('')
      setPatientDob('')
      setHealthCardNumber('')
      setPhoneNumber('')
      setPatientEmail('')
      setSpecialistType('CARDIOLOGY')
      setDate(selectedDate ? format(selectedDate, 'yyyy-MM-dd') : format(new Date(), 'yyyy-MM-dd'))
      setCondition('')
      setNotes('')
    }
  }, [appointment, selectedDate, isOpen])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      patient_name: patientName,
      patient_dob: patientDob,
      health_card_number: healthCardNumber,
      patient_phone: phoneNumber,
      patient_email: patientEmail,
      specialist_type: specialistType,
      scheduled_date: date,
      condition: condition,
      notes: notes,
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
              Date of Birth
            </label>
            <input
              type="date"
              value={patientDob}
              onChange={(e) => setPatientDob(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Health Card Number
            </label>
            <input
              type="text"
              value={healthCardNumber}
              onChange={(e) => setHealthCardNumber(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter health card number"
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
              Email Address
            </label>
            <input
              type="email"
              value={patientEmail}
              onChange={(e) => setPatientEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="patient@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Specialist Type
            </label>
            <select
              value={specialistType}
              onChange={(e) => setSpecialistType(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="CARDIOLOGY">Cardiology</option>
              <option value="ORTHOPEDICS">Orthopedics</option>
              <option value="NEUROLOGY">Neurology</option>
              <option value="DERMATOLOGY">Dermatology</option>
              <option value="OPHTHALMOLOGY">Ophthalmology</option>
              <option value="ENDOCRINOLOGY">Endocrinology</option>
              <option value="PSYCHIATRY">Psychiatry</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scheduled Date
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
              Condition
            </label>
            <textarea
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              required
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Describe the medical condition..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
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
              {isLoading ? 'Saving...' : (appointment ? 'Save Changes' : 'Add Referral')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
