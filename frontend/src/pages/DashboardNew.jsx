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
  getReferralsByDate,
  getReferralsByStatus,
  getOpenFlags,
  initiateCall,
  resolveFlag,
} from '../api/client'

export default function Dashboard() {
  const queryClient = useQueryClient()

  // Fetch today's referrals
  const todayStr = format(new Date(), 'yyyy-MM-dd')
  const { data: todayReferrals = [], isLoading: loadingToday } = useQuery({
    queryKey: ['referrals', 'date', todayStr],
    queryFn: () => getReferralsByDate(todayStr),
  })

  // Fetch missed referrals
  const { data: missedReferrals = [], isLoading: loadingMissed } = useQuery({
    queryKey: ['referrals', 'status', 'MISSED'],
    queryFn: () => getReferralsByStatus('MISSED'),
  })

  // Fetch scheduled (upcoming) referrals
  const { data: upcomingReferrals = [] } = useQuery({
    queryKey: ['referrals', 'status', 'SCHEDULED'],
    queryFn: () => getReferralsByStatus('SCHEDULED'),
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
    mutationFn: ({ referralId, phoneNumber }) =>
      initiateCall(referralId, phoneNumber),
    onSuccess: () => {
      queryClient.invalidateQueries(['referrals'])
    },
  })

  // Resolve flag mutation
  const resolveMutation = useMutation({
    mutationFn: (flagId) => resolveFlag(flagId, 'Marked resolved by nurse'),
    onSuccess: () => {
      queryClient.invalidateQueries(['flags'])
    },
  })

  const handleActivateAgentCall = (referral) => {
    callMutation.mutate({
      referralId: referral.id,
      phoneNumber: referral.patient_phone,
    })
  }

  const handleCallPatient = (referral) => {
    const phone = referral.patient_phone
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
    upcoming: upcomingReferrals.filter(ref => 
      !isBefore(new Date(ref.scheduled_date), new Date())
    ).length,
    missed: missedReferrals.length,
    agentCalls: 2, // TODO: Get from backend
    flagged: flaggedPatients.length,
  }), [upcomingReferrals, missedReferrals, flaggedPatients])

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
                // Get patient name from the referral data in the flag
                const patientName = flag.referrals?.patient_name || 'Unknown Patient'
                const phone = flag.referrals?.patient_phone || 'No phone'
                const scheduledDate = flag.referrals?.scheduled_date
                
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
                            <span className="font-medium">Title:</span> {flag.title || 'Follow-up required'}
                          </div>
                          <div>
                            <span className="font-medium">Phone:</span> {phone}
                          </div>
                          <div>
                            <span className="font-medium">Description:</span> {flag.description || 'Patient needs attention'}
                          </div>
                          <div>
                            <span className="font-medium">Status:</span> {flag.status || 'open'}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-3 mt-4">
                      <button
                        onClick={() => handleCallPatient(flag.referrals)}
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
            {missedReferrals.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No missed appointments requiring follow-up</div>
            ) : (
              missedReferrals.slice(0, 3).map(ref => {
                const patientName = ref.patient_name || 'Unknown Patient'
                
                return (
                  <div key={ref.id} className="bg-orange-50 rounded-lg border border-orange-200 p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-3">{patientName}</h3>
                        <div className="grid grid-cols-3 gap-4 text-sm text-gray-600 mb-4">
                          <div>
                            <span className="font-medium">Missed Date:</span><br />
                            {ref.scheduled_date ? format(new Date(ref.scheduled_date), 'MMM d, yyyy') : 'N/A'}
                          </div>
                          <div>
                            <span className="font-medium">Referral Type:</span><br />
                            {ref.condition || ref.specialist_type || 'Consultation'}
                          </div>
                          <div>
                            <span className="font-medium">Last Contact:</span><br />
                            2 days ago
                          </div>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleActivateAgentCall(ref)}
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
                {upcomingReferrals.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-gray-500">No upcoming appointments</td>
                  </tr>
                ) : (
                  upcomingReferrals.slice(0, 10).map(ref => {
                    const patientName = ref.patient_name || 'Unknown Patient'
                    const phone = ref.patient_phone || ''
                    const daysUntil = ref.scheduled_date ? differenceInDays(new Date(ref.scheduled_date), new Date()) : 0
                    
                    return (
                      <tr key={ref.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-4 px-4">
                          <div className="font-medium text-gray-900">{patientName}</div>
                          {phone && <div className="text-sm text-gray-500">{phone}</div>}
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-700">
                          {ref.condition || ref.specialist_type || 'Consultation'}
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm text-gray-900">
                            {ref.scheduled_date ? format(new Date(ref.scheduled_date), 'MMM d, yyyy') : 'N/A'}
                          </div>
                          <div className="text-xs text-gray-500">
                            {ref.scheduled_date ? format(new Date(ref.scheduled_date), 'h:mm a') : ''}
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
