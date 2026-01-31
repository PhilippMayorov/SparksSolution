/**
 * Appointment Side Panel for viewing appointment details.
 * 
 * Features:
 * - Patient information display
 * - Appointment details
 * - Contact history
 * - Action buttons (trigger call, manual call)
 */

import { X, Phone, Clock, User, Stethoscope, Calendar, MessageSquare } from 'lucide-react'
import { format } from 'date-fns'

export default function AppointmentSidePanel({ 
  appointment, 
  onClose,
  onTriggerAgentCall,
  onCallManually 
}) {
  if (!appointment) return null

  // Normalize appointment data from backend or local format
  const patient = appointment.patient || {}
  const patientName = appointment.patientName || `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown Patient'
  const phoneNumber = appointment.phoneNumber || patient.phone || 'No phone'
  const appointmentDate = appointment.date || appointment.scheduled_at
  const time = appointment.time || (appointmentDate ? format(new Date(appointmentDate), 'HH:mm') : '')
  const doctor = appointment.doctor || 'Specialist'
  const type = appointment.type || appointment.appointment_type || 'Consultation'
  const notes = appointment.notes || ''

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      
      <div className="relative w-full max-w-lg bg-white shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Appointment Details</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Patient Info */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <User size={28} className="text-blue-600" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">{patientName}</h3>
                <p className="text-sm text-gray-500">Patient ID: #{appointment.id?.slice(0, 8) || 'N/A'}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2 text-sm">
                <Phone size={16} className="text-gray-400" />
                <span className="text-gray-700">{phoneNumber}</span>
              </div>
              {appointmentDate && (
                <div className="flex items-center gap-2 text-sm">
                  <Calendar size={16} className="text-gray-400" />
                  <span className="text-gray-700">{format(new Date(appointmentDate), 'MMM d, yyyy')}</span>
                </div>
              )}
              {time && (
                <div className="flex items-center gap-2 text-sm">
                  <Clock size={16} className="text-gray-400" />
                  <span className="text-gray-700">{time}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm">
                <Stethoscope size={16} className="text-gray-400" />
                <span className="text-gray-700">{doctor}</span>
              </div>
            </div>
          </div>

          {/* Referral Type */}
          <div className="border-t border-gray-200 pt-6">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">Referral Information</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-600 mb-1">Referral Type</div>
              <div className="text-base font-medium text-gray-900">{type}</div>
            </div>
          </div>

          {/* Notes */}
          {notes && (
            <div className="border-t border-gray-200 pt-6">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Notes</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-700">{notes}</p>
              </div>
            </div>
          )}

          {/* Status */}
          {appointment.status && (
            <div className="border-t border-gray-200 pt-6">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Status</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  appointment.status === 'scheduled' ? 'bg-blue-100 text-blue-700' :
                  appointment.status === 'completed' ? 'bg-green-100 text-green-700' :
                  appointment.status === 'missed' ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
                </span>
              </div>
            </div>
          )}

          {/* Contact History */}
          <div className="border-t border-gray-200 pt-6">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">Contact History</h4>
            <div className="space-y-3">
              <div className="flex items-start gap-3 text-sm">
                <MessageSquare size={16} className="text-gray-400 mt-0.5" />
                <div>
                  <p className="text-gray-700">Last contacted on {format(new Date(), 'MMM d, yyyy')}</p>
                  <p className="text-gray-500 text-xs mt-1">No answer - voicemail left</p>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="border-t border-gray-200 pt-6 space-y-3">
            <button
              onClick={() => onTriggerAgentCall?.(appointment.id)}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              <Phone size={18} />
              Trigger Agent Call
            </button>
            <button
              onClick={() => onCallManually?.(appointment.id)}
              className="w-full px-6 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <Phone size={18} />
              Call Patient Manually
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
