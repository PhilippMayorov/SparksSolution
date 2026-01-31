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
import { AlertTriangle, CheckCircle, Filter, RefreshCw } from 'lucide-react'
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Follow-up Flags</h1>
          <p className="text-gray-500">
            {filteredFlags.length} {filter === 'open' ? 'open' : ''} flags
            requiring attention
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 p-4 bg-white rounded-lg border">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Filters:</span>
        </div>

        {/* Status filter */}
        <div className="flex gap-1">
          {['open', 'resolved', 'all'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`
                px-3 py-1 rounded-lg text-sm font-medium transition-colors
                ${
                  filter === status
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }
              `}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* Priority filter */}
        <div className="flex gap-1 border-l pl-4">
          {['all', 'urgent', 'high', 'medium', 'low'].map((priority) => (
            <button
              key={priority}
              onClick={() => setPriorityFilter(priority)}
              className={`
                px-3 py-1 rounded-lg text-sm font-medium transition-colors
                ${
                  priorityFilter === priority
                    ? priority === 'urgent'
                      ? 'bg-red-100 text-red-700'
                      : priority === 'high'
                        ? 'bg-orange-100 text-orange-700'
                        : priority === 'medium'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }
              `}
            >
              {priority.charAt(0).toUpperCase() + priority.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filteredFlags.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900">
            All caught up!
          </h2>
          <p className="text-gray-500 mt-2">
            {filter === 'open'
              ? 'No open flags requiring attention.'
              : 'No flags match your filters.'}
          </p>
        </div>
      )}

      {/* Flags list */}
      {!isLoading && filteredFlags.length > 0 && (
        <div className="space-y-6">
          {/* Urgent section */}
          {urgentFlags.length > 0 && (
            <section>
              <h2 className="flex items-center gap-2 text-lg font-semibold text-red-700 mb-3">
                <AlertTriangle className="w-5 h-5" />
                Urgent ({urgentFlags.length})
              </h2>
              <div className="space-y-3">
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
              <h2 className="flex items-center gap-2 text-lg font-semibold text-orange-700 mb-3">
                <AlertTriangle className="w-5 h-5" />
                High Priority ({highFlags.length})
              </h2>
              <div className="space-y-3">
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
              <h2 className="text-lg font-semibold text-yellow-700 mb-3">
                Medium Priority ({mediumFlags.length})
              </h2>
              <div className="space-y-3">
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
              <h2 className="text-lg font-semibold text-gray-700 mb-3">
                Low Priority ({lowFlags.length})
              </h2>
              <div className="space-y-3">
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
      <div className="p-4 bg-green-50 rounded-lg border border-green-200">
        <h3 className="font-semibold text-gray-900 mb-2">{flag.title}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resolution Notes (optional)
            </label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Describe how this was resolved..."
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              rows={2}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onResolve(flag.id)}
              disabled={isPending}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
            >
              {isPending ? 'Saving...' : 'Confirm Resolution'}
            </button>
            <button
              onClick={onCancelResolve}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
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
