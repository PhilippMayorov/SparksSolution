/**
 * Shared TypeScript types for frontend and backend.
 *
 * These types mirror the Pydantic models in the backend
 * and can be used for type-safe API calls in the frontend.
 */

// ============ ENUMS ============

export type AppointmentStatus =
  | 'scheduled'
  | 'confirmed'
  | 'missed'
  | 'rescheduled'
  | 'cancelled'
  | 'completed'

export type CallStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'no_answer'

export type CallOutcome =
  | 'rescheduled'
  | 'declined'
  | 'voicemail'
  | 'callback_requested'
  | 'invalid_number'

export type FlagPriority = 'low' | 'medium' | 'high' | 'urgent'

export type FlagStatus = 'open' | 'in_progress' | 'resolved' | 'dismissed'

// ============ PATIENT TYPES ============

export interface Patient {
  id: string
  first_name: string
  last_name: string
  email?: string
  phone: string
  date_of_birth?: string
  created_at: string
  updated_at: string
}

export interface PatientCreate {
  first_name: string
  last_name: string
  email?: string
  phone: string
  date_of_birth?: string
}

// ============ APPOINTMENT TYPES ============

export interface Appointment {
  id: string
  patient_id: string
  scheduled_at: string
  duration_minutes: number
  appointment_type: string
  status: AppointmentStatus
  notes?: string
  google_event_id?: string
  created_at: string
  updated_at: string
  patient?: Patient
}

export interface AppointmentCreate {
  patient_id: string
  scheduled_at: string
  duration_minutes?: number
  appointment_type: string
  notes?: string
}

export interface AppointmentUpdate {
  scheduled_at?: string
  duration_minutes?: number
  appointment_type?: string
  notes?: string
  status?: AppointmentStatus
}

export interface AppointmentReschedule {
  new_datetime: string
  reason?: string
}

// ============ CALL ATTEMPT TYPES ============

export interface CallAttempt {
  id: string
  appointment_id: string
  patient_id: string
  status: CallStatus
  outcome?: CallOutcome
  elevenlabs_call_id?: string
  started_at?: string
  ended_at?: string
  transcript?: string
  created_at: string
}

export interface CallAttemptCreate {
  appointment_id: string
  patient_id: string
}

// ============ FLAG TYPES ============

export interface Flag {
  id: string
  patient_id: string
  appointment_id?: string
  title: string
  description?: string
  priority: FlagPriority
  status: FlagStatus
  created_by?: string
  resolved_by?: string
  resolved_at?: string
  resolution_notes?: string
  created_at: string
  updated_at: string
  patient?: Patient
  appointment?: Appointment
}

export interface FlagCreate {
  patient_id: string
  appointment_id?: string
  title: string
  description?: string
  priority?: FlagPriority
}

export interface FlagUpdate {
  title?: string
  description?: string
  priority?: FlagPriority
  status?: FlagStatus
  resolution_notes?: string
}

// ============ AUTH TYPES ============

export interface User {
  id: string
  email: string
  full_name: string
  role: 'nurse' | 'admin' | 'doctor'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

// ============ CALENDAR TYPES ============

export interface CalendarSyncStatus {
  appointment_id: string
  synced: boolean
  google_event_id?: string
  last_synced_at?: string
  error?: string
}

// ============ WEBHOOK TYPES ============

export interface ElevenLabsWebhookPayload {
  call_id: string
  status: string
  outcome?: string
  new_appointment_time?: string
  transcript?: string
  duration_seconds?: number
  metadata?: {
    appointment_id: string
    call_attempt_id: string
  }
}

// ============ DASHBOARD TYPES ============

export interface DashboardStats {
  total_appointments_today: number
  missed_appointments: number
  pending_calls: number
  open_flags: number
  upcoming_appointments: Appointment[]
}

// ============ API RESPONSE TYPES ============

export interface ApiError {
  detail: string
  status_code?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}
