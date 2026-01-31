/**
 * API client for backend communication.
 *
 * Provides typed methods for all backend endpoints.
 * Uses axios with automatic token injection and error handling.
 */

import axios from 'axios'

// Base API client
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // TODO: Handle unauthorized - redirect to login
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ============ APPOINTMENTS ============

/**
 * Fetch appointments for a specific date.
 * @param {string} date - Date in YYYY-MM-DD format
 */
export const getAppointmentsByDate = async (date) => {
  const response = await api.get('/appointments/', { params: { date } })
  return response.data
}

/**
 * Fetch appointments by status.
 * @param {string} status - Status filter (scheduled, missed, etc.)
 */
export const getAppointmentsByStatus = async (status) => {
  const response = await api.get('/appointments/', { params: { status } })
  return response.data
}

/**
 * Fetch a single appointment by ID.
 * @param {string} id - Appointment UUID
 */
export const getAppointment = async (id) => {
  const response = await api.get(`/appointments/${id}`)
  return response.data
}

/**
 * Create a new appointment.
 * @param {Object} appointmentData - Appointment creation data
 */
export const createAppointment = async (appointmentData) => {
  const response = await api.post('/appointments/', appointmentData)
  return response.data
}

/**
 * Update an existing appointment.
 * @param {string} id - Appointment UUID
 * @param {Object} updates - Fields to update
 */
export const updateAppointment = async (id, updates) => {
  const response = await api.patch(`/appointments/${id}`, updates)
  return response.data
}

/**
 * Reschedule an appointment.
 * @param {string} id - Appointment UUID
 * @param {string} newDatetime - New scheduled datetime (ISO format)
 * @param {string} reason - Optional reason for rescheduling
 */
export const rescheduleAppointment = async (id, newDatetime, reason = null) => {
  const response = await api.post(`/appointments/${id}/reschedule`, {
    new_datetime: newDatetime,
    reason,
  })
  return response.data
}

/**
 * Mark an appointment as missed.
 * @param {string} id - Appointment UUID
 */
export const markAppointmentMissed = async (id) => {
  const response = await api.post(`/appointments/${id}/mark-missed`)
  return response.data
}

/**
 * Cancel an appointment.
 * @param {string} id - Appointment UUID
 */
export const cancelAppointment = async (id) => {
  await api.delete(`/appointments/${id}`)
}

// ============ FLAGS ============

/**
 * Fetch all open flags.
 */
export const getOpenFlags = async () => {
  const response = await api.get('/flags/open')
  return response.data
}

/**
 * Fetch flags with optional filters.
 * @param {Object} filters - Filter params (status, priority, patient_id)
 */
export const getFlags = async (filters = {}) => {
  const response = await api.get('/flags/', { params: filters })
  return response.data
}

/**
 * Create a new flag.
 * @param {Object} flagData - Flag creation data
 */
export const createFlag = async (flagData) => {
  const response = await api.post('/flags/', flagData)
  return response.data
}

/**
 * Resolve a flag.
 * @param {string} id - Flag UUID
 * @param {string} resolutionNotes - Optional notes
 */
export const resolveFlag = async (id, resolutionNotes = null) => {
  const response = await api.post(`/flags/${id}/resolve`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}

/**
 * Dismiss a flag.
 * @param {string} id - Flag UUID
 * @param {string} reason - Reason for dismissal
 */
export const dismissFlag = async (id, reason = null) => {
  const response = await api.post(`/flags/${id}/dismiss`, { reason })
  return response.data
}

// ============ CALLS ============

/**
 * Initiate an outbound call for a missed appointment.
 * @param {string} appointmentId - Appointment UUID
 * @param {string} patientId - Patient UUID
 */
export const initiateCall = async (appointmentId, patientId) => {
  const response = await api.post('/calls/initiate', {
    appointment_id: appointmentId,
    patient_id: patientId,
  })
  return response.data
}

/**
 * Get call attempt details.
 * @param {string} id - Call attempt UUID
 */
export const getCallAttempt = async (id) => {
  const response = await api.get(`/calls/${id}`)
  return response.data
}

/**
 * Get pending calls.
 */
export const getPendingCalls = async () => {
  const response = await api.get('/calls/', { params: { status: 'pending' } })
  return response.data
}

// ============ CALENDAR ============

/**
 * Sync an appointment to Google Calendar.
 * @param {string} appointmentId - Appointment UUID
 */
export const syncToCalendar = async (appointmentId) => {
  const response = await api.post(`/calendar/sync/${appointmentId}`)
  return response.data
}

/**
 * Get calendar sync status for an appointment.
 * @param {string} appointmentId - Appointment UUID
 */
export const getCalendarSyncStatus = async (appointmentId) => {
  const response = await api.get(`/calendar/sync-status/${appointmentId}`)
  return response.data
}

// ============ AUTH ============

/**
 * Login user.
 * @param {string} email - User email
 * @param {string} password - User password
 */
export const login = async (email, password) => {
  const formData = new FormData()
  formData.append('username', email)
  formData.append('password', password)

  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

  const { access_token } = response.data
  localStorage.setItem('auth_token', access_token)
  return response.data
}

/**
 * Logout user.
 */
export const logout = async () => {
  await api.post('/auth/logout')
  localStorage.removeItem('auth_token')
}

/**
 * Get current user.
 */
export const getCurrentUser = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export default api
