-- ==========================================================
-- Supabase Database Schema for Nurse Appointment System
-- ==========================================================
-- 
-- Run this SQL in the Supabase SQL Editor to create all tables.
-- Make sure to enable the pgcrypto extension for UUID generation.
--
-- Tables:
--   - patients: Patient records
--   - appointments: Scheduled appointments
--   - call_attempts: ElevenLabs outbound call tracking
--   - flags: Nurse follow-up items
--   - users: System users (nurses/admins)
--   - calendar_sync: Google Calendar sync tracking
--
-- ==========================================================

-- Enable UUID extension (usually enabled by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================================
-- USERS TABLE
-- ==========================================================
-- System users (nurses, admins) who use the tablet app

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) DEFAULT 'nurse' CHECK (role IN ('nurse', 'admin', 'doctor')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for email lookups during authentication
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);


-- ==========================================================
-- PATIENTS TABLE
-- ==========================================================
-- Patient records with contact information

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20) NOT NULL,  -- E.164 format recommended
    date_of_birth DATE,
    medical_record_number VARCHAR(50),  -- Optional external ID
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(last_name, first_name);


-- ==========================================================
-- APPOINTMENTS TABLE
-- ==========================================================
-- Scheduled appointments linking patients to time slots

CREATE TYPE appointment_status AS ENUM (
    'scheduled',
    'confirmed', 
    'missed',
    'rescheduled',
    'cancelled',
    'completed'
);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 30 CHECK (duration_minutes > 0),
    appointment_type VARCHAR(100) NOT NULL,
    status appointment_status DEFAULT 'scheduled',
    notes TEXT,
    google_event_id VARCHAR(255),  -- Google Calendar event ID
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for calendar queries
CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_at ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(DATE(scheduled_at));


-- ==========================================================
-- CALL ATTEMPTS TABLE
-- ==========================================================
-- Tracks ElevenLabs outbound call attempts for missed appointments

CREATE TYPE call_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'no_answer'
);

CREATE TYPE call_outcome AS ENUM (
    'rescheduled',
    'declined',
    'voicemail',
    'callback_requested',
    'invalid_number'
);

CREATE TABLE IF NOT EXISTS call_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    elevenlabs_call_id VARCHAR(255),  -- ElevenLabs API call ID
    status call_status DEFAULT 'pending',
    outcome call_outcome,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    transcript TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for webhook lookups by ElevenLabs call ID
CREATE INDEX IF NOT EXISTS idx_call_attempts_elevenlabs_id ON call_attempts(elevenlabs_call_id);
CREATE INDEX IF NOT EXISTS idx_call_attempts_appointment ON call_attempts(appointment_id);
CREATE INDEX IF NOT EXISTS idx_call_attempts_status ON call_attempts(status);


-- ==========================================================
-- FLAGS TABLE
-- ==========================================================
-- Follow-up items for nurses when automated calls fail

CREATE TYPE flag_priority AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
);

CREATE TYPE flag_status AS ENUM (
    'open',
    'in_progress',
    'resolved',
    'dismissed'
);

CREATE TABLE IF NOT EXISTS flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    call_attempt_id UUID REFERENCES call_attempts(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    priority flag_priority DEFAULT 'medium',
    status flag_status DEFAULT 'open',
    created_by UUID REFERENCES users(id),
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_flags_status ON flags(status);
CREATE INDEX IF NOT EXISTS idx_flags_priority ON flags(priority);
CREATE INDEX IF NOT EXISTS idx_flags_patient ON flags(patient_id);
CREATE INDEX IF NOT EXISTS idx_flags_open_priority ON flags(status, priority) WHERE status = 'open';


-- ==========================================================
-- CALENDAR SYNC TABLE
-- ==========================================================
-- Tracks Google Calendar synchronization status

CREATE TABLE IF NOT EXISTS calendar_sync (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID UNIQUE NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    google_event_id VARCHAR(255),
    google_calendar_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'synced', 'failed', 'removed')),
    last_synced_at TIMESTAMP WITH TIME ZONE,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for sync status checks
CREATE INDEX IF NOT EXISTS idx_calendar_sync_appointment ON calendar_sync(appointment_id);


-- ==========================================================
-- TRIGGERS FOR updated_at
-- ==========================================================
-- Automatically update the updated_at timestamp

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_flags_updated_at
    BEFORE UPDATE ON flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_sync_updated_at
    BEFORE UPDATE ON calendar_sync
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==========================================================
-- ROW LEVEL SECURITY (RLS) - Optional
-- ==========================================================
-- Uncomment to enable RLS for production

-- ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE call_attempts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE flags ENABLE ROW LEVEL SECURITY;

-- Example policy: Users can only see their own flags
-- CREATE POLICY "Users can view own flags" ON flags
--     FOR SELECT USING (created_by = auth.uid() OR resolved_by = auth.uid());


-- ==========================================================
-- SAMPLE DATA (for development)
-- ==========================================================
-- Uncomment to insert test data

/*
-- Sample patients
INSERT INTO patients (first_name, last_name, email, phone, date_of_birth) VALUES
    ('John', 'Doe', 'john.doe@example.com', '+15551234567', '1985-03-15'),
    ('Jane', 'Smith', 'jane.smith@example.com', '+15559876543', '1990-07-22'),
    ('Bob', 'Johnson', 'bob.j@example.com', '+15555551234', '1978-11-08');

-- Sample appointments (adjust dates as needed)
INSERT INTO appointments (patient_id, scheduled_at, duration_minutes, appointment_type, status) 
SELECT 
    id,
    NOW() + INTERVAL '1 day',
    30,
    'Follow-up',
    'scheduled'
FROM patients 
WHERE first_name = 'John';

-- Sample missed appointment
INSERT INTO appointments (patient_id, scheduled_at, duration_minutes, appointment_type, status)
SELECT 
    id,
    NOW() - INTERVAL '2 hours',
    30,
    'Check-up',
    'missed'
FROM patients 
WHERE first_name = 'Jane';
*/


-- ==========================================================
-- VIEWS (Optional - for common queries)
-- ==========================================================

-- View for today's appointments
CREATE OR REPLACE VIEW today_appointments AS
SELECT 
    a.*,
    p.first_name,
    p.last_name,
    p.phone,
    p.email
FROM appointments a
JOIN patients p ON a.patient_id = p.id
WHERE DATE(a.scheduled_at) = CURRENT_DATE
ORDER BY a.scheduled_at;

-- View for open flags with patient info
CREATE OR REPLACE VIEW open_flags_with_patient AS
SELECT 
    f.*,
    p.first_name as patient_first_name,
    p.last_name as patient_last_name,
    p.phone as patient_phone
FROM flags f
JOIN patients p ON f.patient_id = p.id
WHERE f.status = 'open'
ORDER BY 
    CASE f.priority 
        WHEN 'urgent' THEN 1 
        WHEN 'high' THEN 2 
        WHEN 'medium' THEN 3 
        ELSE 4 
    END,
    f.created_at DESC;
