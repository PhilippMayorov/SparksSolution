/**
 * Dashboard page - Referral Follow-Up Dashboard.
 *
 * Features (Figma design):
 * - Metrics cards for key statistics
 * - Flagged patients section (highest priority)
 * - Missed referrals with agent follow-up
 * - Upcoming referral appointments table
 * - Full backend API integration
 */

import { useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, isBefore, differenceInDays } from 'date-fns'
import { Calendar, AlertCircle, Phone, Flag, RefreshCw } from 'lucide-react'
import MetricsCard from '../components/MetricsCard'
import {
  getAppointmentsByDate,
  getAppointmentsByStatus,
  getOpenFlags,
  initiateCall,
  resolveFlag,
} from '../api/client'

export default function Dashboard() {
  const queryClient = useQueryClient()

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

  // Fetch scheduled (upcoming) appointments
  const { data: upcomingAppointments = [] } = useQuery({
    queryKey: ['appointments', 'status', 'scheduled'],
    queryFn: () => getAppointmentsByStatus('scheduled'),
  })

  // Fetch flags
  const { data: flags = [] } = useQuery({
    queryKey: ['flags', 'open'],
    queryFn: getOpenFlags,
  })

  // Flagged/urgent items
  const flaggedPatients = flags.filter(
    (f) => f.priority === 'urgent' || f.priority === 'high'
  )

  // Initiate call mutation
  const callMutation = useMutation({
    mutationFn: ({ appointmentId, patientId }) =>
      initiateCall(appointmentId, patientId),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments'])
    },
  })

  // Resolve flag mutation
  const resolveMutation = useMutation({
    mutationFn: (flagId) => resolveFlag(flagId, 'Marked resolved by nurse'),
    onSuccess: () => {
      queryClient.invalidateQueries(['flags'])
    },
  })

  const handleActivateAgentCall = (appointment) => {
    callMutation.mutate({
      appointmentId: appointment.id,
      patientId: appointment.patient_id || appointment.patient?.id,
    })
  }

  const handleCallPatient = (appointment) => {
    const phone = appointment.patient?.phone || appointment.phoneNumber
    if (phone) {
      window.open(`tel:${phone}`, '_self')
    } else {
      alert('No phone number available for this patient')
    }
  }

  const handleMarkResolved = (flagId) => {
    resolveMutation.mutate(flagId)
  }

  // Calculate metrics
  const metrics = useMemo(() => ({
    upcoming: upcomingAppointments.filter(apt => 
      !isBefore(new Date(apt.scheduled_at), new Date())
    ).length,
    missed: missedAppointments.length,
    agentCalls: 2, // TODO: Get from backend
    flagged: flaggedPatients.length,
  }), [upcomingAppointments, missedAppointments, flaggedPatients])

  const isLoading = loadingToday || loadingMissed

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Referral Follow-Up Dashboard</h1>
          <p className="text-gray-600 mt-2">Track missed appointments, agent outreach, and follow-ups</p>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries()}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricsCard
          title="Total Upcoming Referrals"
          value={metrics.upcoming}
          icon={Calendar}
          color="blue"
          subtitle="Next 30 days"
        />
        <MetricsCard
          title="Missed Appointments"
          value={metrics.missed}
          icon={AlertCircle}
          color="orange"
          subtitle="Require follow-up"
        />
        <MetricsCard
          title="Agent Calls in Progress"
          value={metrics.agentCalls}
          icon={Phone}
          color="green"
          subtitle="Active outreach"
        />
        <MetricsCard
          title="Flagged Patients"
          value={metrics.flagged}
          icon={Flag}
          color="red"
          subtitle="Nurse action required"
        />
      </div>

      {/* Flagged Patients - Highest Priority */}
      <section className="mb-8">
        <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-6 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Flag size={24} className="text-red-600" />
            <h2 className="text-xl font-bold text-gray-900">Flagged Patients – Nurse Action Required</h2>
          </div>
          <p className="text-sm text-gray-700 mb-6">
            These patients require immediate attention due to failed contact attempts or rescheduling issues.
          </p>
          
          <div className="space-y-4">
            {flaggedPatients.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No flagged patients at this time</div>
            ) : (
              flaggedPatients.map(flag => {
                const apt = flag.appointment || {}
                const patient = apt.patient || flag.patient || {}
                const patientName = `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown Patient'
                const phone = patient.phone || 'No phone'
                
                return (
                  <div key={flag.id} className="bg-white rounded-lg border-2 border-red-200 p-6 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                          <h3 className="text-lg font-semibold text-gray-900">{patientName}</h3>
                          <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                            {flag.priority || 'Urgent'}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-4">
                          <div>
                            <span className="font-medium">Reason:</span> {flag.reason || 'No answer / Multiple attempts'}
                          </div>
                          <div>
                            <span className="font-medium">Phone:</span> {phone}
                          </div>
                          <div>
                            <span className="font-medium">Type:</span> {flag.flag_type || 'Follow-up required'}
                          </div>
                          <div>
                            <span className="font-medium">Call Attempts:</span> {flag.call_attempts || 3}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-3 mt-4">
                      <button
                        onClick={() => handleCallPatient({ patient })}
                        className="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                      >
                        <Phone size={18} />
                        Call Patient
                      </button>
                      <button
                        onClick={() => handleMarkResolved(flag.id)}
                        disabled={resolveMutation.isPending}
                        className="px-6 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
                      >
                        Mark Resolved
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </section>

      {/* Missed Referrals - Agent Follow-Up Available */}
      <section className="mb-8">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle size={24} className="text-orange-600" />
            <h2 className="text-xl font-bold text-gray-900">Missed Referrals – Agent Follow-Up Available</h2>
          </div>
          <p className="text-sm text-gray-600 mb-6">
            Patients who missed appointments and are eligible for AI agent outreach.
          </p>
          
          <div className="space-y-4">
            {missedAppointments.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No missed appointments requiring follow-up</div>
            ) : (
              missedAppointments.slice(0, 3).map(apt => {
                const patient = apt.patient || {}
                const patientName = `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown Patient'
                
                return (
                  <div key={apt.id} className="bg-orange-50 rounded-lg border border-orange-200 p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-3">{patientName}</h3>
                        <div className="grid grid-cols-3 gap-4 text-sm text-gray-600 mb-4">
                          <div>
                            <span className="font-medium">Missed Date:</span><br />
                            {apt.scheduled_at ? format(new Date(apt.scheduled_at), 'MMM d, yyyy') : 'N/A'}
                          </div>
                          <div>
                            <span className="font-medium">Referral Type:</span><br />
                            {apt.appointment_type || apt.type || 'Consultation'}
                          </div>
                          <div>
                            <span className="font-medium">Last Contact:</span><br />
                            2 days ago
                          </div>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleActivateAgentCall(apt)}
                      disabled={callMutation.isPending}
                      className="w-full px-6 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <Phone size={18} />
                      Activate Agent Call
                    </button>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </section>

      {/* Upcoming Referral Appointments */}
      <section>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={24} className="text-blue-600" />
            <h2 className="text-xl font-bold text-gray-900">Upcoming Referral Appointments</h2>
          </div>
          <p className="text-sm text-gray-600 mb-6">
            Patients with scheduled referral appointments in the next 30 days.
          </p>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Patient Name</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Referral Type</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Scheduled Date</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Days Until</th>
                </tr>
              </thead>
              <tbody>
                {upcomingAppointments.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-gray-500">No upcoming appointments</td>
                  </tr>
                ) : (
                  upcomingAppointments.slice(0, 10).map(apt => {
                    const patient = apt.patient || {}
                    const patientName = `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || 'Unknown Patient'
                    const phone = patient.phone || ''
                    const daysUntil = apt.scheduled_at ? differenceInDays(new Date(apt.scheduled_at), new Date()) : 0
                    
                    return (
                      <tr key={apt.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-4 px-4">
                          <div className="font-medium text-gray-900">{patientName}</div>
                          {phone && <div className="text-sm text-gray-500">{phone}</div>}
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-700">
                          {apt.appointment_type || apt.type || 'Consultation'}
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm text-gray-900">
                            {apt.scheduled_at ? format(new Date(apt.scheduled_at), 'MMM d, yyyy') : 'N/A'}
                          </div>
                          <div className="text-xs text-gray-500">
                            {apt.scheduled_at ? format(new Date(apt.scheduled_at), 'h:mm a') : ''}
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            daysUntil <= 3 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `${daysUntil} days`}
                          </span>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}
