/**
 * Dashboard page with calendar view.
 *
 * Main landing page for nurses showing:
 * - Today's referrals overview
 * - Weekly calendar view
 * - Quick access to missed referrals
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfWeek, endOfWeek, addDays } from 'date-fns'
import {
  Calendar,
  AlertCircle,
  Phone,
  RefreshCw,
  CheckCircle2,
  Clock,
  TrendingUp,
  ChevronRight,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import CalendarView from '../components/CalendarView'
import ReferralCard from '../components/ReferralCard'
import {
  getReferralsByDate,
  getReferralsByStatus,
  initiateCall,
} from '../api/client'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [selectedDate, setSelectedDate] = useState(new Date())

  // Fetch referrals for current week
  const weekStart = startOfWeek(selectedDate)
  const weekEnd = endOfWeek(selectedDate)

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

  // Fetch all referrals for calendar (week view)
  const { data: weekReferrals = [] } = useQuery({
    queryKey: ['referrals', 'week', format(weekStart, 'yyyy-MM-dd')],
    queryFn: async () => {
      const days = []
      for (let i = 0; i < 7; i++) {
        const date = format(addDays(weekStart, i), 'yyyy-MM-dd')
        const referrals = await getReferralsByDate(date)
        days.push(...referrals)
      }
      return days
    },
  })

  // Initiate call mutation
  const callMutation = useMutation({
    mutationFn: ({ referralId, phoneNumber }) =>
      initiateCall(referralId, phoneNumber),
    onSuccess: () => {
      queryClient.invalidateQueries(['referrals'])
    },
    onError: (error) => {
      console.error('Failed to initiate call:', error)
    },
  })

  // Stats for today
  const stats = useMemo(
    () => ({
      total: todayReferrals.length,
      completed: todayReferrals.filter((r) => r.status === 'COMPLETED')
        .length,
      missed: missedReferrals.length,
      upcoming: todayReferrals.filter(
        (r) =>
          r.status === 'SCHEDULED' && new Date(r.scheduled_date) > new Date(),
      ).length,
    }),
    [todayReferrals, missedReferrals],
  )

  const handleInitiateCall = (referral) => {
    callMutation.mutate({
      referralId: referral.id,
      phoneNumber: referral.patient_phone,
    })
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">
            {format(new Date(), 'EEEE, MMMM d, yyyy')}
          </p>
        </div>

        <button
          onClick={() => queryClient.invalidateQueries(['referrals'])}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all text-gray-700 font-medium shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Calendar}
          label="Today's Referrals"
          value={stats.total}
          color="blue"
          trend="+2 from yesterday"
        />
        <StatCard
          icon={Clock}
          label="Upcoming"
          value={stats.upcoming}
          color="indigo"
        />
        <StatCard
          icon={AlertCircle}
          label="Missed (needs call)"
          value={stats.missed}
          color="red"
          alert={stats.missed > 0}
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={stats.completed}
          color="green"
        />
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Calendar - takes 2 columns */}
        <div className="lg:col-span-2">
          <CalendarView
            referrals={weekReferrals}
            onSelectDate={setSelectedDate}
          />
        </div>

        {/* Side panel */}
        <div className="space-y-6">
          {/* Missed referrals alert */}
          {missedReferrals.length > 0 && (
            <div className="bg-gradient-to-br from-red-50 to-red-100 border border-red-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-red-500 rounded-xl flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-red-800">
                    Missed Referrals
                  </h2>
                  <p className="text-sm text-red-600">
                    {missedReferrals.length} patients need a call
                  </p>
                </div>
              </div>
              <div className="space-y-3">
                {missedReferrals.slice(0, 3).map((ref) => (
                  <div
                    key={ref.id}
                    className="flex items-center justify-between bg-white p-3 rounded-xl border border-red-100 shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                        <span className="text-red-600 font-semibold text-sm">
                          {ref.patient_name?.[0]}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 text-sm">
                          {ref.patient_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {format(new Date(ref.scheduled_date), 'MMM d, h:mm a')}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleInitiateCall(ref)}
                      disabled={callMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-2 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600 disabled:opacity-50 transition-colors shadow-sm"
                    >
                      <Phone className="w-4 h-4" />
                      Call
                    </button>
                  </div>
                ))}
                {missedReferrals.length > 3 && (
                  <Link
                    to="/flags"
                    className="flex items-center justify-center gap-1 py-2 text-sm text-red-600 font-medium hover:text-red-700 transition-colors"
                  >
                    View all {missedReferrals.length} missed
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Today's schedule */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Today's Schedule</h2>
              <span className="text-sm text-gray-500">
                {todayReferrals.length} referrals
              </span>
            </div>
            <div className="p-4">
              {loadingToday ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : todayReferrals.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Calendar className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-gray-500 text-sm">No referrals today</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto">
                  {todayReferrals
                    .sort(
                      (a, b) =>
                        new Date(a.scheduled_date) - new Date(b.scheduled_date),
                    )
                    .map((ref) => (
                      <ReferralCard key={ref.id} referral={ref} compact />
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Stat card component
function StatCard({
  icon: Icon,
  label,
  value,
  color = 'gray',
  alert = false,
  trend,
}) {
  const colorConfig = {
    blue: {
      bg: 'bg-blue-50',
      iconBg: 'bg-blue-500',
      text: 'text-blue-600',
    },
    indigo: {
      bg: 'bg-indigo-50',
      iconBg: 'bg-indigo-500',
      text: 'text-indigo-600',
    },
    green: {
      bg: 'bg-green-50',
      iconBg: 'bg-green-500',
      text: 'text-green-600',
    },
    red: {
      bg: 'bg-red-50',
      iconBg: 'bg-red-500',
      text: 'text-red-600',
    },
    gray: {
      bg: 'bg-gray-50',
      iconBg: 'bg-gray-500',
      text: 'text-gray-600',
    },
  }

  const config = colorConfig[color]

  return (
    <div
      className={`
        p-5 rounded-2xl border transition-all
        ${
          alert
            ? 'border-red-300 bg-gradient-to-br from-red-50 to-red-100 shadow-md'
            : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className={`p-2.5 rounded-xl ${config.iconBg} shadow-sm`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {alert && (
          <span className="px-2 py-1 bg-red-500 text-white text-xs font-medium rounded-full">
            Action needed
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-1">{label}</p>
        {trend && (
          <p className="flex items-center gap-1 text-xs text-green-600 mt-2">
            <TrendingUp className="w-3 h-3" />
            {trend}
          </p>
        )}
      </div>
    </div>
  )
}
