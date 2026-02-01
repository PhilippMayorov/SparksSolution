/**
 * Flags page - List of follow-up items requiring nurse attention.
 *
 * Shows flags created when:
 * - Automated calls fail to reschedule
 * - Manual review is required
 *
 * Allows nurses to resolve or dismiss flags.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle,
  Filter,
  RefreshCw,
  Search,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { FlagItem } from '../components/FlagBanner'
import { getFlags, getOpenFlags, resolveFlag, dismissFlag } from '../api/client'

export default function Flags() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('open') // 'open', 'resolved', 'all'
  const [priorityFilter, setPriorityFilter] = useState('all') // 'all', 'urgent', 'high', 'medium', 'low'
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [resolvingId, setResolvingId] = useState(null)

  // Fetch flags based on filter
  const {
    data: flags = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['flags', filter],
    queryFn: () =>
      filter === 'open'
        ? getOpenFlags()
        : getFlags({ status: filter === 'all' ? undefined : filter }),
  })

  // Resolve mutation
  const resolveMutation = useMutation({
    mutationFn: ({ id, notes }) => resolveFlag(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries(['flags'])
      setResolvingId(null)
      setResolutionNotes('')
    },
  })

  // Dismiss mutation
  const dismissMutation = useMutation({
    mutationFn: (id) => dismissFlag(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['flags'])
    },
  })

  // Filter flags by priority
  const filteredFlags =
    priorityFilter === 'all'
      ? flags
      : flags.filter((f) => f.priority === priorityFilter)

  // Group by priority for display
  const urgentFlags = filteredFlags.filter((f) => f.priority === 'urgent')
  const highFlags = filteredFlags.filter((f) => f.priority === 'high')
  const mediumFlags = filteredFlags.filter((f) => f.priority === 'medium')
  const lowFlags = filteredFlags.filter((f) => f.priority === 'low')

  const handleResolve = (id) => {
    if (resolvingId === id) {
      // Submit resolution
      resolveMutation.mutate({ id, notes: resolutionNotes })
    } else {
      // Show resolution input
      setResolvingId(id)
      setResolutionNotes('')
    }
  }

  const handleDismiss = (id) => {
    if (confirm('Are you sure you want to dismiss this flag?')) {
      dismissMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Follow-up Flags</h1>
          <p className="text-gray-500 mt-1">
            {filteredFlags.length} {filter === 'open' ? 'open' : ''} flags
            requiring attention
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all text-gray-700 font-medium shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center">
              <Filter className="w-4 h-4 text-gray-500" />
            </div>
            <span className="text-sm font-semibold text-gray-700">
              Filters:
            </span>
          </div>

          {/* Status filter */}
          <div className="flex bg-gray-100 rounded-xl p-1">
            {['open', 'resolved', 'all'].map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize
                  ${
                    filter === status
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-600 hover:bg-white hover:shadow-sm'
                  }
                `}
              >
                {status}
              </button>
            ))}
          </div>

          {/* Priority filter */}
          <div className="flex gap-2 sm:border-l sm:pl-4 border-gray-200">
            {['all', 'urgent', 'high', 'medium', 'low'].map((priority) => (
              <button
                key={priority}
                onClick={() => setPriorityFilter(priority)}
                className={`
                  px-3 py-2 rounded-xl text-sm font-medium transition-all capitalize border
                  ${
                    priorityFilter === priority
                      ? priority === 'urgent'
                        ? 'bg-red-100 text-red-700 border-red-200'
                        : priority === 'high'
                          ? 'bg-orange-100 text-orange-700 border-orange-200'
                          : priority === 'medium'
                            ? 'bg-amber-100 text-amber-700 border-amber-200'
                            : 'bg-blue-100 text-blue-700 border-blue-200'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }
                `}
              >
                {priority}
              </button>
            ))}
          </div>

          {/* Clear filters */}
          {(filter !== 'open' || priorityFilter !== 'all') && (
            <button
              onClick={() => {
                setFilter('open')
                setPriorityFilter('all')
              }}
              className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl transition-colors"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <RefreshCw className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
            <p className="text-gray-500">Loading flags...</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filteredFlags.length === 0 && (
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-200 shadow-sm">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            All caught up!
          </h2>
          <p className="text-gray-500">
            {filter === 'open'
              ? 'No open flags requiring attention.'
              : 'No flags match your filters.'}
          </p>
        </div>
      )}

      {/* Flags list */}
      {!isLoading && filteredFlags.length > 0 && (
        <div className="space-y-8">
          {/* Urgent section */}
          {urgentFlags.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                </div>
                <h2 className="text-lg font-semibold text-red-700">
                  Urgent ({urgentFlags.length})
                </h2>
              </div>
              <div className="space-y-4">
                {urgentFlags.map((flag) => (
                  <FlagItemWithResolve
                    key={flag.id}
                    flag={flag}
                    onResolve={handleResolve}
                    onDismiss={handleDismiss}
                    isResolving={resolvingId === flag.id}
                    resolutionNotes={resolutionNotes}
                    setResolutionNotes={setResolutionNotes}
                    isPending={resolveMutation.isPending}
                    onCancelResolve={() => setResolvingId(null)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* High priority section */}
          {highFlags.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                </div>
                <h2 className="text-lg font-semibold text-orange-700">
                  High Priority ({highFlags.length})
                </h2>
              </div>
              <div className="space-y-4">
                {highFlags.map((flag) => (
                  <FlagItemWithResolve
                    key={flag.id}
                    flag={flag}
                    onResolve={handleResolve}
                    onDismiss={handleDismiss}
                    isResolving={resolvingId === flag.id}
                    resolutionNotes={resolutionNotes}
                    setResolutionNotes={setResolutionNotes}
                    isPending={resolveMutation.isPending}
                    onCancelResolve={() => setResolvingId(null)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Medium priority section */}
          {mediumFlags.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                </div>
                <h2 className="text-lg font-semibold text-amber-700">
                  Medium Priority ({mediumFlags.length})
                </h2>
              </div>
              <div className="space-y-4">
                {mediumFlags.map((flag) => (
                  <FlagItemWithResolve
                    key={flag.id}
                    flag={flag}
                    onResolve={handleResolve}
                    onDismiss={handleDismiss}
                    isResolving={resolvingId === flag.id}
                    resolutionNotes={resolutionNotes}
                    setResolutionNotes={setResolutionNotes}
                    isPending={resolveMutation.isPending}
                    onCancelResolve={() => setResolvingId(null)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Low priority section */}
          {lowFlags.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-gray-500" />
                </div>
                <h2 className="text-lg font-semibold text-gray-700">
                  Low Priority ({lowFlags.length})
                </h2>
              </div>
              <div className="space-y-4">
                {lowFlags.map((flag) => (
                  <FlagItemWithResolve
                    key={flag.id}
                    flag={flag}
                    onResolve={handleResolve}
                    onDismiss={handleDismiss}
                    isResolving={resolvingId === flag.id}
                    resolutionNotes={resolutionNotes}
                    setResolutionNotes={setResolutionNotes}
                    isPending={resolveMutation.isPending}
                    onCancelResolve={() => setResolvingId(null)}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

// Extended flag item with resolution input
function FlagItemWithResolve({
  flag,
  onResolve,
  onDismiss,
  isResolving,
  resolutionNotes,
  setResolutionNotes,
  isPending,
  onCancelResolve,
}) {
  if (isResolving) {
    return (
      <div className="p-5 bg-gradient-to-r from-green-50 to-white rounded-2xl border border-green-200 shadow-sm">
        <h3 className="font-semibold text-gray-900 mb-3">{flag.title}</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Resolution Notes (optional)
            </label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Describe how this was resolved..."
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all outline-none resize-none"
              rows={3}
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => onResolve(flag.id)}
              disabled={isPending}
              className="px-5 py-2.5 bg-green-500 text-white rounded-xl font-medium hover:bg-green-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isPending ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Saving...
                </span>
              ) : (
                'Confirm Resolution'
              )}
            </button>
            <button
              onClick={onCancelResolve}
              className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    )
  }

  return <FlagItem flag={flag} onResolve={onResolve} onDismiss={onDismiss} />
}
