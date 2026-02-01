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
      // Handle unauthorized - redirect to login
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ============ REFERRALS ============

/**
 * Fetch referrals for a specific date.
 * @param {string} date - Date in YYYY-MM-DD format
 */
export const getReferralsByDate = async (date) => {
  const response = await api.get('/referrals/', { params: { date } })
  return response.data
}

/**
 * Fetch referrals by status.
 * @param {string} status - Status filter (PENDING, SCHEDULED, MISSED, etc.)
 */
export const getReferralsByStatus = async (status) => {
  const response = await api.get('/referrals/', { params: { status } })
  return response.data
}

/**
 * Fetch a single referral by ID.
 * @param {string} id - Referral UUID
 */
export const getReferral = async (id) => {
  const response = await api.get(`/referrals/${id}`)
  return response.data
}

/**
 * Create a new referral.
 * @param {Object} referralData - Referral creation data
 */
export const createReferral = async (referralData) => {
  const response = await api.post('/referrals/', referralData)
  return response.data
}

/**
 * Update an existing referral.
 * @param {string} id - Referral UUID
 * @param {Object} updates - Fields to update
 */
export const updateReferral = async (id, updates) => {
  const response = await api.patch(`/referrals/${id}`, updates)
  return response.data
}

/**
 * Schedule a pending referral.
 * @param {string} id - Referral UUID
 * @param {string} scheduledDate - Scheduled datetime (ISO format)
 * @param {string} notes - Optional notes
 */
export const scheduleReferral = async (id, scheduledDate, notes = null) => {
  const response = await api.post(`/referrals/${id}/schedule`, {
    scheduled_date: scheduledDate,
    notes,
  })
  return response.data
}

/**
 * Reschedule a referral.
 * @param {string} id - Referral UUID
 * @param {string} newDatetime - New scheduled datetime (ISO format)
 * @param {string} reason - Optional reason for rescheduling
 */
export const rescheduleReferral = async (id, newDatetime, reason = null) => {
  const response = await api.post(`/referrals/${id}/reschedule`, {
    new_datetime: newDatetime,
    reason,
  })
  return response.data
}

/**
 * Mark a referral as missed.
 * @param {string} id - Referral UUID
 */
export const markReferralMissed = async (id) => {
  const response = await api.post(`/referrals/${id}/mark-missed`)
  return response.data
}

/**
 * Mark a referral as attended.
 * @param {string} id - Referral UUID
 */
export const markReferralAttended = async (id) => {
  const response = await api.post(`/referrals/${id}/mark-attended`)
  return response.data
}

/**
 * Cancel a referral.
 * @param {string} id - Referral UUID
 */
export const cancelReferral = async (id) => {
  await api.delete(`/referrals/${id}`)
}

/**
 * Get status history for a referral.
 * @param {string} id - Referral UUID
 */
export const getReferralHistory = async (id) => {
  const response = await api.get(`/referrals/${id}/history`)
  return response.data
}

/**
 * Get communications (calls + emails) for a referral.
 * @param {string} id - Referral UUID
 */
export const getReferralCommunications = async (id) => {
  const response = await api.get(`/referrals/${id}/communications`)
  return response.data
}

/**
 * Get dashboard statistics.
 */
export const getDashboardStats = async () => {
  const response = await api.get('/referrals/dashboard/stats')
  return response.data
}

/**
 * Get overdue referrals.
 * @param {number} daysThreshold - Days threshold for overdue (default 14)
 */
export const getOverdueReferrals = async (daysThreshold = 14) => {
  const response = await api.get('/referrals/overdue/list', {
    params: { days_threshold: daysThreshold },
  })
  return response.data
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
 * @param {Object} filters - Filter params (status, priority, referral_id)
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
 * Initiate an outbound call for a missed referral.
 * @param {string} referralId - Referral UUID
 * @param {string} phoneNumber - Phone number to call
 * @param {string} callType - Type of call (default: MISSED_APPOINTMENT_FOLLOWUP)
 */
const TWILIO_VERIFIED_NUMBER = "+19054628586"; // trial-verified number

export const initiateCall = async (
  referralId,
  _phoneNumber, // intentionally unused on trial
  callType = "MISSED_APPOINTMENT_FOLLOWUP"
) => {
  // Log when function is called
  console.log("🔵 initiateCall() called");
  console.log("📊 Parameters:", {
    referralId,
    _phoneNumber,
    callType,
    timestamp: new Date().toISOString()
  });

  try {
    console.log("📡 Making fetch request to make-call endpoint...");

    const response = await fetch(
      "https://vehicles-forgot-terrain-magnificent.trycloudflare.com/make-call",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: TWILIO_VERIFIED_NUMBER, // 👈 forced
          dynamic_variables: {
            patient_name: "Parth Joshi",
            patient_age: "19",
            specialist_type: "Cardiologist",
            cancelled_appointment_time: "Jan 20, 2026",
            selected_time: "",
            referral_id: referralId,
            call_type: callType,
          },
        }),
      }
    );

    console.log("📥 Response received:", {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok
    });

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    console.log("📦 Response data:", data);

    if (!response.ok) {
      console.error("❌ Request failed:", {
        status: response.status,
        data
      });
      throw new Error(
        typeof data === "string" ? data : JSON.stringify(data)
      );
    }

    console.log("✅ initiateCall() completed successfully");
    return data;

  } catch (error) {
    console.error("💥 initiateCall() error:", error);
    throw error;
  }
};

/**
 * Get call log details.
 * @param {string} id - Call log UUID
 */
export const getCallLog = async (id) => {
  const response = await api.get(`/calls/${id}`)
  return response.data
}

/**
 * Get pending calls.
 */
export const getPendingCalls = async () => {
  const response = await api.get('/calls/', { params: { status: 'SCHEDULED' } })
  return response.data
}

/**
 * Get calls for a specific referral.
 * @param {string} referralId - Referral UUID
 */
export const getCallsByReferral = async (referralId) => {
  const response = await api.get('/calls/', { params: { referral_id: referralId } })
  return response.data
}

// ============ CALENDAR ============

/**
 * Sync a referral to Google Calendar.
 * @param {string} referralId - Referral UUID
 */
export const syncToCalendar = async (referralId) => {
  const response = await api.post(`/calendar/sync/${referralId}`)
  return response.data
}

/**
 * Get calendar sync status for a referral.
 * @param {string} referralId - Referral UUID
 */
export const getCalendarSyncStatus = async (referralId) => {
  const response = await api.get(`/calendar/sync-status/${referralId}`)
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
