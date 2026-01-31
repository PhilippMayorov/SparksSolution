/**
 * Calendar Page with all calendar views.
 * 
 * Features:
 * - Day, Week, Month view switching
 * - Add/Edit appointments via modal
 * - Appointment side panel for details
 * - Full backend API integration
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfWeek, endOfWeek, startOfMonth, endOfMonth, addDays } from 'date-fns'
import MonthCalendar from '../components/MonthCalendar'
import DayView from '../components/DayView'
import AppointmentModal from '../components/AppointmentModal'
import AppointmentSidePanel from '../components/AppointmentSidePanel'
import {
  getAppointmentsByDate,
  createAppointment,
  updateAppointment,
  initiateCall,
} from '../api/client'

export default function CalendarPage() {
  const queryClient = useQueryClient()
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [viewMode, setViewMode] = useState('month')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingAppointment, setEditingAppointment] = useState(null)
  const [selectedAppointment, setSelectedAppointment] = useState(null)

  // Fetch appointments for the current view range
  const getDateRange = () => {
    if (viewMode === 'month') {
      const start = startOfMonth(selectedDate)
      const end = endOfMonth(selectedDate)
      return { start, end }
    } else if (viewMode === 'week') {
      const start = startOfWeek(selectedDate)
      const end = endOfWeek(selectedDate)
      return { start, end }
    }
    return { start: selectedDate, end: selectedDate }
  }

  const { start, end } = getDateRange()
  
  // Fetch all appointments for the date range
  const { data: appointments = [], isLoading } = useQuery({
    queryKey: ['appointments', 'range', format(start, 'yyyy-MM-dd'), format(end, 'yyyy-MM-dd')],
    queryFn: async () => {
      const allAppointments = []
      let currentDate = start
      while (currentDate <= end) {
        try {
          const dayAppointments = await getAppointmentsByDate(format(currentDate, 'yyyy-MM-dd'))
          allAppointments.push(...dayAppointments)
        } catch (e) {
          // Ignore errors for individual days
        }
        currentDate = addDays(currentDate, 1)
      }
      return allAppointments
    },
    staleTime: 30000,
  })

  // Create appointment mutation
  const createMutation = useMutation({
    mutationFn: (data) => createAppointment({
      patient_id: data.patient_id,
      scheduled_at: data.scheduled_at,
      appointment_type: data.appointment_type,
      notes: data.notes,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments'])
      setIsModalOpen(false)
    },
  })

  // Update appointment mutation  
  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }) => updateAppointment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments'])
      setIsModalOpen(false)
      setEditingAppointment(null)
    },
  })

  // Initiate call mutation
  const callMutation = useMutation({
    mutationFn: (appointmentId) => {
      const apt = appointments.find(a => a.id === appointmentId)
      return initiateCall(appointmentId, apt?.patient_id || apt?.patient?.id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['appointments'])
      setSelectedAppointment(null)
    },
  })

  const handleAddAppointment = () => {
    setEditingAppointment(null)
    setIsModalOpen(true)
  }

  const handleEditAppointment = (appointment) => {
    setSelectedAppointment(appointment)
  }

  const handleSaveAppointment = (appointmentData) => {
    if (editingAppointment) {
      updateMutation.mutate({ id: editingAppointment.id, ...appointmentData })
    } else {
      createMutation.mutate(appointmentData)
    }
  }

  const handleTriggerAgentCall = (appointmentId) => {
    callMutation.mutate(appointmentId)
  }

  const handleCallManually = (appointmentId) => {
    const apt = appointments.find(a => a.id === appointmentId)
    const phone = apt?.patient?.phone || apt?.phoneNumber
    if (phone) {
      window.open(`tel:${phone}`, '_self')
    } else {
      alert('No phone number available for this patient')
    }
    setSelectedAppointment(null)
  }

  const renderCalendarView = () => {
    switch (viewMode) {
      case 'day':
        return (
          <DayView
            appointments={appointments}
            selectedDate={selectedDate}
            onDateSelect={setSelectedDate}
            onAddAppointment={handleAddAppointment}
            onEditAppointment={handleEditAppointment}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        )
      case 'week':
        // Week view falls back to day view for now
        return (
          <DayView
            appointments={appointments}
            selectedDate={selectedDate}
            onDateSelect={setSelectedDate}
            onAddAppointment={handleAddAppointment}
            onEditAppointment={handleEditAppointment}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        )
      case 'month':
      default:
        return (
          <MonthCalendar
            appointments={appointments}
            selectedDate={selectedDate}
            onDateSelect={(date) => {
              setSelectedDate(date)
              setViewMode('day')
            }}
            onMonthChange={setSelectedDate}
            onAddAppointment={handleAddAppointment}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        )
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Referral Appointments</h1>
        <p className="text-gray-600 mt-2">Manage and track all patient referral appointments</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        renderCalendarView()
      )}

      <AppointmentModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setEditingAppointment(null)
        }}
        onSave={handleSaveAppointment}
        appointment={editingAppointment}
        selectedDate={selectedDate}
        isLoading={createMutation.isPending || updateMutation.isPending}
      />

      {selectedAppointment && (
        <AppointmentSidePanel
          appointment={selectedAppointment}
          onClose={() => setSelectedAppointment(null)}
          onTriggerAgentCall={handleTriggerAgentCall}
          onCallManually={handleCallManually}
        />
      )}
    </div>
  )
}
