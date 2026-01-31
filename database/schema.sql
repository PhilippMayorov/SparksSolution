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
-- ==========================================================

-- Enable UUID extension (usually enabled by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================================
-- USERS TABLE
-- ==========================================================
-- System users (nurses, admins) who use the tablet app

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'NURSE' CHECK (role IN ('NURSE', 'COORDINATOR', 'ADMIN')),
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at 
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();


-- ==========================================================
-- REFERRALS TABLE
-- ==========================================================
-- Referral records with patient and medical information
CREATE TABLE referrals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Patient Information
  patient_name VARCHAR(255) NOT NULL,
  patient_dob DATE NOT NULL,
  health_card_number VARCHAR(50) NOT NULL,
  patient_email VARCHAR(255),  -- For sending calendar invite
  patient_phone VARCHAR(20),   -- For Twilio voice calls
  
  -- Medical Details
  condition TEXT NOT NULL,
  specialist_type VARCHAR(50) NOT NULL CHECK (specialist_type IN (
    'CARDIOLOGY', 'ORTHOPEDICS', 'NEUROLOGY', 'DERMATOLOGY', 
    'OPHTHALMOLOGY', 'ENDOCRINOLOGY', 'PSYCHIATRY', 'OTHER'
  )),
  urgency VARCHAR(20) NOT NULL DEFAULT 'ROUTINE' CHECK (urgency IN ('ROUTINE', 'URGENT', 'CRITICAL')),
  is_high_risk BOOLEAN DEFAULT FALSE,
  
  -- Status Tracking
  status VARCHAR(50) NOT NULL DEFAULT 'PENDING' CHECK (status IN (
    'PENDING', 'SCHEDULED', 'ATTENDED', 'MISSED', 
    'NEEDS_REBOOK', 'ESCALATED', 'COMPLETED', 'CANCELLED'
  )),
  
  -- Important Dates
  referral_date DATE NOT NULL,
  scheduled_date TIMESTAMPTZ,
  completed_date TIMESTAMPTZ,
  
  -- Notes and Tracking
  notes TEXT,
  created_by_id UUID NOT NULL REFERENCES users(id),  -- FK to users table
  updated_by_id UUID REFERENCES users(id),
  
  -- Email & Calendar Tracking
  email_sent BOOLEAN DEFAULT FALSE,
  email_sent_at TIMESTAMPTZ,
  calendar_invite_sent BOOLEAN DEFAULT FALSE,
  calendar_event_id VARCHAR(255),  -- Google Calendar Event ID
  calendar_source_id UUID REFERENCES specialist_calendars(id),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_referrals_status ON referrals(status);
CREATE INDEX idx_referrals_scheduled_date ON referrals(scheduled_date);
CREATE INDEX idx_referrals_created_by ON referrals(created_by_id);
CREATE INDEX idx_referrals_high_risk ON referrals(is_high_risk) WHERE is_high_risk = TRUE;
CREATE INDEX idx_referrals_patient_email ON referrals(patient_email);

-- Auto-update updated_at
CREATE TRIGGER update_referrals_updated_at 
  BEFORE UPDATE ON referrals
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

===========================================================
-- SPECIALIST CALENDARS TABLE
-- Stores external calendar info for each specialist type
==========================================================

CREATE TABLE specialist_calendars (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  specialist_type VARCHAR(50) NOT NULL CHECK (specialist_type IN (
    'CARDIOLOGY', 'ORTHOPEDICS', 'NEUROLOGY', 'DERMATOLOGY',
    'OPHTHALMOLOGY', 'ENDOCRINOLOGY', 'PSYCHIATRY', 'OTHER'
  )),

  -- Store whatever you use as “schedule truth”:
  -- could be Google Calendar ID, clinic calendar ID, etc.
  external_calendar_id VARCHAR(255) NOT NULL,

  timezone TEXT NOT NULL DEFAULT 'America/Toronto',
  is_active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_specialist_cal_unique
  ON specialist_calendars(specialist_type)
  WHERE is_active = TRUE;

CREATE TRIGGER update_specialist_calendars_updated_at
  BEFORE UPDATE ON specialist_calendars
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

==========================================================
-- APPOINTMENT PROPOSALS TABLE
-- Tracks proposed appointment slots for referrals
==========================================================

CREATE TABLE appointment_proposals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  referral_id UUID NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,

  -- The proposed slot
  proposed_start TIMESTAMPTZ NOT NULL,
  proposed_end   TIMESTAMPTZ NOT NULL,

  status VARCHAR(20) NOT NULL CHECK (status IN (
    'PROPOSED',     -- generated by system/agent
    'HELD',         -- temporarily held while on call
    'ACCEPTED',     -- patient chose it
    'REJECTED',     -- patient rejected it
    'EXPIRED',      -- hold timed out
    'CONFIRMED'     -- committed into referrals.scheduled_date
  )) DEFAULT 'PROPOSED',

  -- If you “hold” a slot during the call to prevent double booking
  hold_expires_at TIMESTAMPTZ,

  -- Optional traceability
  created_by VARCHAR(20) NOT NULL DEFAULT 'VOICE_AGENT' CHECK (created_by IN (
    'VOICE_AGENT', 'NURSE', 'SYSTEM'
  )),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_appt_prop_referral ON appointment_proposals(referral_id, created_at DESC);
CREATE INDEX idx_appt_prop_status ON appointment_proposals(status);
CREATE INDEX idx_appt_prop_hold_exp ON appointment_proposals(hold_expires_at);

CREATE TRIGGER update_appointment_proposals_updated_at
  BEFORE UPDATE ON appointment_proposals
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ==========================================================
-- STATUS HISTORY TABLE
-- ==========================================================
-- Tracks status changes for referrals

CREATE TABLE status_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  referral_id UUID NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,
  status VARCHAR(50) NOT NULL,
  changed_by_id UUID NOT NULL REFERENCES users(id),  -- FK to users table
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  note TEXT
);

-- Index for fast referral history lookup
CREATE INDEX idx_status_history_referral ON status_history(referral_id, changed_at DESC);
CREATE INDEX idx_status_history_user ON status_history(changed_by_id);

-- Auto-create status history entry when referral status changes
CREATE OR REPLACE FUNCTION log_status_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO status_history (referral_id, status, updated_by_id, note)
    VALUES (NEW.id, NEW.status, NEW.updated_by_id, 'Status changed to ' || NEW.status);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_status_change
  AFTER UPDATE ON referrals
  FOR EACH ROW
  EXECUTE FUNCTION log_status_change();


-- ==========================================================
-- CALL ATTEMPTS TABLE
-- ==========================================================
-- Tracks ElevenLabs outbound call attempts for missed appointments

CREATE TABLE call_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  referral_id UUID NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,
  call_type VARCHAR(50) NOT NULL CHECK (call_type IN (
    'APPOINTMENT_REMINDER', 'MISSED_APPOINTMENT_FOLLOWUP',
    'HIGH_RISK_CHECKIN', 'MANUAL_OUTREACH'
  )),
  phone_number VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN (
    'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 
    'FAILED', 'NO_ANSWER', 'VOICEMAIL'
  )),
  resolution VARCHAR(30) CHECK (resolution IN (
  'RESCHEDULED',
  'LEFT_VOICEMAIL',
  'NO_ANSWER',
  'CALLBACK_REQUESTED',
  'DECLINED'
)),
selected_proposal_id UUID REFERENCES appointment_proposals(id),
  transcript TEXT,
  duration_seconds INTEGER,
  twilio_call_sid VARCHAR(255),  -- Twilio Call SID for tracking
  recording_url TEXT,
  scheduled_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for call history
CREATE INDEX idx_call_logs_referral ON call_logs(referral_id, created_at DESC);
CREATE INDEX idx_call_logs_status ON call_logs(status);

-- ==========================================================
-- ALERTS TABLE
-- ==========================================================
-- Nurse follow-up alerts for patients requiring attention

CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  referral_id UUID NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),  -- Assigned nurse (null = all nurses)
  alert_type VARCHAR(50) NOT NULL DEFAULT 'GENERAL' CHECK (alert_type IN (
    'HIGH_RISK_ESCALATION', 'MISSED_APPOINTMENT', 'CALL_FAILED',
    'FOLLOW_UP_REQUIRED', 'GENERAL'
  )),
  message TEXT NOT NULL,
  is_read BOOLEAN DEFAULT FALSE,
  is_dismissed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for alerts
CREATE INDEX idx_alerts_referral ON alerts(referral_id);
CREATE INDEX idx_alerts_user ON alerts(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_open ON alerts(is_dismissed, is_read) WHERE is_dismissed = FALSE;

-- ==========================================================
-- EMAIL LOGS TABLE
-- ==========================================================
-- Email tracking for referral-related communications

CREATE TABLE email_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  referral_id UUID NOT NULL REFERENCES referrals(id) ON DELETE CASCADE,
  email_type VARCHAR(50) NOT NULL CHECK (email_type IN (
    'REFERRAL_CREATED', 'APPOINTMENT_REMINDER', 'APPOINTMENT_CONFIRMED',
    'APPOINTMENT_RESCHEDULED', 'FOLLOW_UP'
  )),
  recipient_email VARCHAR(255) NOT NULL,
  subject VARCHAR(500) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN (
    'PENDING', 'SENT', 'FAILED', 'BOUNCED'
  )),
  sendgrid_message_id VARCHAR(255),
  error_message TEXT,
  calendar_invite_attached BOOLEAN DEFAULT FALSE,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for email tracking
CREATE INDEX idx_email_logs_referral ON email_logs(referral_id, created_at DESC);
CREATE INDEX idx_email_logs_status ON email_logs(status);
CREATE INDEX idx_email_logs_pending ON email_logs(status) WHERE status = 'PENDING';

-- ==========================================================
-- TRIGGERS AND FUNCTIONS
-- ==========================================================
-- triggers to automate email sending and escalation

-- Trigger: Auto-queue email when referral is created
CREATE OR REPLACE FUNCTION trigger_referral_email()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.patient_email IS NOT NULL THEN
    INSERT INTO email_logs (
      referral_id,
      email_type,
      recipient_email,
      subject,
      status,
      calendar_invite_attached
    )
    VALUES (
      NEW.id,
      'REFERRAL_CREATED',
      NEW.patient_email,
      'Clearwater Health - Your ' || NEW.specialist_type || ' Referral',
      'PENDING',
      CASE WHEN NEW.scheduled_date IS NOT NULL THEN TRUE ELSE FALSE END
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_send_referral_email
  AFTER INSERT ON referrals
  FOR EACH ROW
  EXECUTE FUNCTION trigger_referral_email();

-- Trigger: Auto-escalate high-risk missed appointments
CREATE OR REPLACE FUNCTION auto_escalate_high_risk()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'MISSED' AND NEW.is_high_risk = TRUE THEN
    -- Update status to ESCALATED
    UPDATE referrals SET status = 'ESCALATED' WHERE id = NEW.id;
    
    -- Create alert for all nurses (user_id = NULL)
    INSERT INTO alerts (referral_id, user_id, alert_type, message)
    VALUES (
      NEW.id,
      NULL,
      'HIGH_RISK_ESCALATION',
      'URGENT: High-risk patient ' || NEW.patient_name || ' missed ' || 
      NEW.specialist_type || ' appointment'
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_escalate
  AFTER UPDATE ON referrals
  FOR EACH ROW
  WHEN (OLD.status IS DISTINCT FROM NEW.status)
  EXECUTE FUNCTION auto_escalate_high_risk();


-- ==========================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================================
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can read all users" ON users
  FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE USING (auth.uid()::text = id::text);

-- Referrals policies (authenticated users = logged-in nurses)
CREATE POLICY "Authenticated users can read all referrals" ON referrals
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create referrals" ON referrals
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can update referrals" ON referrals
  FOR UPDATE USING (auth.role() = 'authenticated');

-- Status history policies
CREATE POLICY "Authenticated users can read status history" ON status_history
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create status history" ON status_history
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Alerts policies
CREATE POLICY "Users can read all alerts or own alerts" ON alerts
  FOR SELECT USING (
    auth.role() = 'authenticated' AND 
    (user_id IS NULL OR auth.uid()::text = user_id::text)
  );

CREATE POLICY "Authenticated users can update alerts" ON alerts
  FOR UPDATE USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create alerts" ON alerts
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Call logs policies
CREATE POLICY "Authenticated users can read call logs" ON call_logs
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create call logs" ON call_logs
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Email logs policies
CREATE POLICY "Authenticated users can read email logs" ON email_logs
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create email logs" ON email_logs
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- ==========================================================
-- Functions for Data Retrieval
-- ==========================================================

-- Function: Get overdue referrals
CREATE OR REPLACE FUNCTION get_overdue_referrals(days_threshold INTEGER DEFAULT 14)
RETURNS TABLE (
  referral_id UUID,
  patient_name VARCHAR,
  patient_email VARCHAR,
  patient_phone VARCHAR,
  status VARCHAR,
  days_overdue INTEGER,
  is_high_risk BOOLEAN,
  created_by_nurse VARCHAR
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    r.id,
    r.patient_name,
    r.patient_email,
    r.patient_phone,
    r.status,
    EXTRACT(DAY FROM NOW() - r.referral_date)::INTEGER as days_overdue,
    r.is_high_risk,
    (u.first_name || ' ' || u.last_name)::VARCHAR as created_by_nurse
  FROM referrals r
  JOIN users u ON r.created_by_id = u.id
  WHERE 
    (r.status = 'PENDING' AND NOW() - r.referral_date > INTERVAL '1 day' * days_threshold)
    OR (r.status = 'SCHEDULED' AND r.scheduled_date < NOW() AND r.status != 'ATTENDED')
    OR (r.status = 'NEEDS_REBOOK' AND NOW() - r.updated_at > INTERVAL '7 days')
  ORDER BY r.is_high_risk DESC, days_overdue DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Get dashboard statistics
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS JSON AS $$
DECLARE
  result JSON;
BEGIN
  SELECT json_build_object(
    'total_active', (
      SELECT COUNT(*) FROM referrals 
      WHERE status NOT IN ('COMPLETED', 'CANCELLED')
    ),
    'scheduled_this_week', (
      SELECT COUNT(*) FROM referrals 
      WHERE scheduled_date >= NOW() 
      AND scheduled_date < NOW() + INTERVAL '7 days'
    ),
    'overdue', (SELECT COUNT(*) FROM get_overdue_referrals(0)),
    'escalated', (SELECT COUNT(*) FROM referrals WHERE status = 'ESCALATED'),
    'high_risk_active', (
      SELECT COUNT(*) FROM referrals 
      WHERE is_high_risk = TRUE 
      AND status NOT IN ('COMPLETED', 'CANCELLED')
    ),
    'emails_pending', (SELECT COUNT(*) FROM email_logs WHERE status = 'PENDING'),
    'emails_failed', (SELECT COUNT(*) FROM email_logs WHERE status = 'FAILED'),
    'unread_alerts', (SELECT COUNT(*) FROM alerts WHERE is_dismissed = FALSE),
    'by_status', (
      SELECT json_object_agg(status, count)
      FROM (
        SELECT status, COUNT(*) as count
        FROM referrals
        WHERE status NOT IN ('COMPLETED', 'CANCELLED')
        GROUP BY status
      ) s
    )
  ) INTO result;
  
  RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function: Get pending emails (for email worker)
CREATE OR REPLACE FUNCTION get_pending_emails(batch_size INTEGER DEFAULT 50)
RETURNS TABLE (
  email_id UUID,
  referral_id UUID,
  email_type VARCHAR,
  recipient_email VARCHAR,
  patient_name VARCHAR,
  patient_phone VARCHAR,
  scheduled_date TIMESTAMPTZ,
  specialist_type VARCHAR,
  condition TEXT,
  notes TEXT,
  created_by_nurse VARCHAR
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    e.id,
    e.referral_id,
    e.email_type,
    e.recipient_email,
    r.patient_name,
    r.patient_phone,
    r.scheduled_date,
    r.specialist_type,
    r.condition,
    r.notes,
    (u.first_name || ' ' || u.last_name)::VARCHAR as created_by_nurse
  FROM email_logs e
  JOIN referrals r ON e.referral_id = r.id
  JOIN users u ON r.created_by_id = u.id
  WHERE e.status = 'PENDING'
  ORDER BY e.created_at ASC
  LIMIT batch_size;
END;
$$ LANGUAGE plpgsql;
-- ==========================================================
-- SAMPLE DATA (for development)
-- ==========================================================
-- Uncomment to insert test data

-- Insert demo nurse users (IMPORTANT: Use bcrypt hashed passwords)
-- Generate hash with: python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('password123'))"

INSERT INTO users (email, password_hash, role, first_name, last_name)
VALUES 
  (
    'jane.doe@clearwater.ca',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqKfN0PZdK',  -- password123
    'NURSE',
    'Jane',
    'Doe'
  ),
  (
    'sarah.johnson@clearwater.ca',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqKfN0PZdK',  -- password123
    'COORDINATOR',
    'Sarah',
    'Johnson'
  );

-- Insert demo referrals
INSERT INTO referrals (
  patient_name, patient_dob, health_card_number, patient_email, patient_phone,
  condition, specialist_type, urgency, is_high_risk, status,
  referral_date, scheduled_date, notes, created_by_id
)
VALUES 
  -- John Smith (from case study - high risk missed appointment)
  (
    'John Smith',
    '1955-03-12',
    '1234-567-890',
    'john.smith@email.com',
    '+12345678901',
    'Atrial fibrillation - requires follow-up after recent episode',
    'CARDIOLOGY',
    'URGENT',
    TRUE,
    'MISSED',
    '2026-01-15',
    '2026-02-01 10:00:00-05',
    'Patient has history of heart issues. Missed appointment on Feb 1.',
    (SELECT id FROM users WHERE email = 'jane.doe@clearwater.ca')
  ),
  -- Mary Johnson
  (
    'Mary Johnson',
    '1980-06-15',
    '9876-543-210',
    'mary.johnson@email.com',
    '+12345678902',
    'Chronic knee pain requiring orthopedic assessment',
    'ORTHOPEDICS',
    'ROUTINE',
    FALSE,
    'PENDING',
    '2026-01-25',
    NULL,
    'Patient requests morning appointments',
    (SELECT id FROM users WHERE email = 'jane.doe@clearwater.ca')
  ),
  -- Robert Wilson
  (
    'Robert Wilson',
    '1942-11-08',
    '5555-123-456',
    'robert.wilson@email.com',
    '+12345678903',
    'Type 2 diabetes management consultation',
    'ENDOCRINOLOGY',
    'ROUTINE',
    TRUE,
    'SCHEDULED',
    '2026-01-20',
    '2026-02-10 14:00:00-05',
    'Senior patient, may need transportation assistance',
    (SELECT id FROM users WHERE email = 'sarah.johnson@clearwater.ca')
  );

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✅ Database setup complete!';
  RAISE NOTICE '📊 Tables created: 6 (users, referrals, status_history, alerts, call_logs, email_logs)';
  RAISE NOTICE '👥 Demo users: 2';
  RAISE NOTICE '📋 Demo referrals: 3';
  RAISE NOTICE '📧 Email trigger: Active';
  RAISE NOTICE '🚨 Auto-escalation trigger: Active';
  RAISE NOTICE '';
  RAISE NOTICE '🔐 Login Credentials:';
  RAISE NOTICE '   Email: jane.doe@clearwater.ca';
  RAISE NOTICE '   Password: password123';
END $$;

-- ==========================================================
-- SANITY CHECK QUERIES
-- ==========================================================
-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Should return: alerts, call_logs, email_logs, referrals, status_history, users

-- Check users
SELECT id, email, role, first_name, last_name, is_active 
FROM users;

-- Should return 2 users

-- Check referrals
SELECT 
  patient_name, 
  specialist_type, 
  status, 
  is_high_risk,
  email_sent,
  created_at
FROM referrals;

-- Should return 3 referrals

-- Check email logs (should have 3 pending emails from trigger)
SELECT 
  email_type,
  recipient_email,
  status,
  calendar_invite_attached
FROM email_logs;

-- Should return 3 pending emails

-- Test dashboard stats function
SELECT get_dashboard_stats();

-- Test overdue referrals function
SELECT * FROM get_overdue_referrals(0);

-- Test pending emails function
SELECT * FROM get_pending_emails(10);

-- ============================================
-- USEFUL VIEWS FOR CLEARWATER REFERRAL TRACKER
-- Run this entire script in Supabase SQL Editor
-- ============================================

-- Drop existing views first (if they exist with SECURITY DEFINER)
DROP VIEW IF EXISTS v_active_referrals CASCADE;
DROP VIEW IF EXISTS v_referral_details CASCADE;
DROP VIEW IF EXISTS v_dashboard_summary CASCADE;
DROP VIEW IF EXISTS v_urgent_actions CASCADE;
DROP VIEW IF EXISTS v_upcoming_appointments CASCADE;
DROP VIEW IF EXISTS v_nurse_activity CASCADE;
DROP VIEW IF EXISTS v_communication_queue CASCADE;
DROP VIEW IF EXISTS v_recent_activity CASCADE;

-- View 1: Active Referrals with Nurse Info
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_active_referrals
WITH (security_invoker=on) AS
SELECT 
  r.id, r.patient_name, r.patient_dob, r.patient_email, r.patient_phone,
  r.health_card_number, r.condition, r.specialist_type, r.urgency,
  r.is_high_risk, r.status, r.referral_date, r.scheduled_date,
  r.completed_date, r.notes, r.email_sent, r.calendar_invite_sent,
  r.created_at, r.updated_at,
  u.id as created_by_id, u.first_name as created_by_first_name,
  u.last_name as created_by_last_name, u.email as created_by_email,
  (u.first_name || ' ' || u.last_name) as created_by_full_name,
  EXTRACT(YEAR FROM AGE(r.patient_dob))::INTEGER as patient_age,
  EXTRACT(DAY FROM NOW() - r.created_at)::INTEGER as days_since_created,
  CASE WHEN r.scheduled_date < NOW() AND r.status = 'SCHEDULED' THEN TRUE ELSE FALSE END as is_appointment_overdue
FROM referrals r
JOIN users u ON r.created_by_id = u.id
WHERE r.status NOT IN ('COMPLETED', 'CANCELLED')
ORDER BY r.is_high_risk DESC, r.urgency DESC, r.created_at DESC;

-- View 2: Referral Details
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_referral_details
WITH (security_invoker=on) AS
SELECT 
  r.id as referral_id, r.patient_name, r.patient_dob, r.patient_email,
  r.patient_phone, r.condition, r.specialist_type, r.urgency,
  r.is_high_risk, r.status, r.referral_date, r.scheduled_date, r.notes,
  (cu.first_name || ' ' || cu.last_name) as created_by,
  cu.email as creator_email,
  (SELECT COUNT(*) FROM status_history sh WHERE sh.referral_id = r.id) as status_change_count,
  (SELECT COUNT(*) FROM alerts a WHERE a.referral_id = r.id AND a.is_dismissed = FALSE) as active_alert_count,
  (SELECT COUNT(*) FROM email_logs el WHERE el.referral_id = r.id) as email_count,
  (SELECT COUNT(*) FROM call_logs cl WHERE cl.referral_id = r.id) as call_count,
  (SELECT changed_at FROM status_history sh WHERE sh.referral_id = r.id ORDER BY changed_at DESC LIMIT 1) as last_status_change_at,
  (SELECT note FROM status_history sh WHERE sh.referral_id = r.id ORDER BY changed_at DESC LIMIT 1) as last_status_note,
  (SELECT status FROM email_logs el WHERE el.referral_id = r.id ORDER BY created_at DESC LIMIT 1) as latest_email_status,
  r.created_at, r.updated_at
FROM referrals r
JOIN users cu ON r.created_by_id = cu.id;

-- View 3: Dashboard Summary
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_dashboard_summary
WITH (security_invoker=on) AS
SELECT 
  (SELECT COUNT(*) FROM referrals WHERE status NOT IN ('COMPLETED', 'CANCELLED')) as total_active,
  (SELECT COUNT(*) FROM referrals WHERE status = 'PENDING') as pending_count,
  (SELECT COUNT(*) FROM referrals WHERE status = 'SCHEDULED') as scheduled_count,
  (SELECT COUNT(*) FROM referrals WHERE status = 'MISSED') as missed_count,
  (SELECT COUNT(*) FROM referrals WHERE status = 'ESCALATED') as escalated_count,
  (SELECT COUNT(*) FROM referrals WHERE status = 'NEEDS_REBOOK') as needs_rebook_count,
  (SELECT COUNT(*) FROM referrals WHERE is_high_risk = TRUE AND status NOT IN ('COMPLETED', 'CANCELLED')) as high_risk_active,
  (SELECT COUNT(*) FROM referrals WHERE scheduled_date >= NOW() AND scheduled_date < NOW() + INTERVAL '7 days') as scheduled_this_week,
  (SELECT COUNT(*) FROM referrals WHERE scheduled_date >= NOW() AND scheduled_date < NOW() + INTERVAL '24 hours') as scheduled_today,
  (SELECT COUNT(*) FROM referrals WHERE status = 'PENDING' AND NOW() - referral_date > INTERVAL '14 days') as overdue_pending,
  (SELECT COUNT(*) FROM referrals WHERE status = 'SCHEDULED' AND scheduled_date < NOW()) as overdue_scheduled,
  (SELECT COUNT(*) FROM alerts WHERE is_dismissed = FALSE) as unread_alerts,
  (SELECT COUNT(*) FROM alerts WHERE is_dismissed = FALSE AND alert_type = 'HIGH_RISK_ESCALATION') as urgent_alerts,
  (SELECT COUNT(*) FROM email_logs WHERE status = 'PENDING') as emails_pending,
  (SELECT COUNT(*) FROM email_logs WHERE status = 'FAILED') as emails_failed,
  (SELECT COUNT(*) FROM call_logs WHERE status = 'SCHEDULED') as calls_scheduled,
  (SELECT COUNT(*) FROM referrals WHERE DATE(created_at) = CURRENT_DATE) as referrals_created_today,
  (SELECT COUNT(*) FROM status_history WHERE DATE(changed_at) = CURRENT_DATE) as status_changes_today;

-- View 4: Urgent Actions
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_urgent_actions
WITH (security_invoker=on) AS
SELECT 'HIGH_RISK_MISSED' as action_type, r.id as referral_id, r.patient_name,
  r.specialist_type, r.status, r.scheduled_date as relevant_date,
  (u.first_name || ' ' || u.last_name) as assigned_nurse, 1 as priority,
  'High-risk patient missed appointment' as message, r.created_at
FROM referrals r JOIN users u ON r.created_by_id = u.id
WHERE r.status = 'MISSED' AND r.is_high_risk = TRUE
UNION ALL
SELECT 'OVERDUE_PENDING', r.id, r.patient_name, r.specialist_type, r.status,
  r.referral_date, (u.first_name || ' ' || u.last_name), 2,
  'Referral pending for ' || EXTRACT(DAY FROM NOW() - r.referral_date)::TEXT || ' days',
  r.created_at
FROM referrals r JOIN users u ON r.created_by_id = u.id
WHERE r.status = 'PENDING' AND NOW() - r.referral_date > INTERVAL '14 days'
UNION ALL
SELECT 'OVERDUE_SCHEDULED', r.id, r.patient_name, r.specialist_type, r.status,
  r.scheduled_date, (u.first_name || ' ' || u.last_name), 2,
  'Scheduled appointment date has passed', r.created_at
FROM referrals r JOIN users u ON r.created_by_id = u.id
WHERE r.status = 'SCHEDULED' AND r.scheduled_date < NOW()
ORDER BY priority ASC, relevant_date ASC;

-- View 5: Upcoming Appointments
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_upcoming_appointments
WITH (security_invoker=on) AS
SELECT 
  r.id as referral_id, r.patient_name, r.patient_email, r.patient_phone,
  r.specialist_type, r.scheduled_date, r.urgency, r.is_high_risk, r.notes,
  (u.first_name || ' ' || u.last_name) as created_by_nurse, u.email as nurse_email,
  EXTRACT(DAY FROM r.scheduled_date - NOW())::INTEGER as days_until_appointment,
  EXTRACT(HOUR FROM r.scheduled_date - NOW())::INTEGER as hours_until_appointment,
  r.email_sent,
  (SELECT COUNT(*) FROM call_logs cl WHERE cl.referral_id = r.id AND cl.call_type = 'APPOINTMENT_REMINDER') as reminder_calls_made,
  r.created_at
FROM referrals r JOIN users u ON r.created_by_id = u.id
WHERE r.status = 'SCHEDULED' AND r.scheduled_date >= NOW() AND r.scheduled_date < NOW() + INTERVAL '7 days'
ORDER BY r.scheduled_date ASC;

-- View 6: Nurse Activity
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_nurse_activity
WITH (security_invoker=on) AS
SELECT 
  u.id as nurse_id, u.first_name, u.last_name, u.email, u.role,
  COUNT(r.id) as total_referrals_created,
  COUNT(r.id) FILTER (WHERE r.status NOT IN ('COMPLETED', 'CANCELLED')) as active_referrals,
  COUNT(r.id) FILTER (WHERE r.status = 'COMPLETED') as completed_referrals,
  COUNT(r.id) FILTER (WHERE r.is_high_risk = TRUE) as high_risk_referrals,
  COUNT(r.id) FILTER (WHERE r.created_at >= NOW() - INTERVAL '7 days') as referrals_this_week,
  COUNT(sh.id) as total_status_changes,
  COUNT(sh.id) FILTER (WHERE sh.changed_at >= NOW() - INTERVAL '7 days') as status_changes_this_week,
  MAX(r.created_at) as last_referral_created_at,
  MAX(sh.changed_at) as last_status_change_at,
  u.last_login
FROM users u
LEFT JOIN referrals r ON u.id = r.created_by_id
LEFT JOIN status_history sh ON u.id = sh.changed_by_id
WHERE u.is_active = TRUE
GROUP BY u.id, u.first_name, u.last_name, u.email, u.role, u.last_login
ORDER BY total_referrals_created DESC;

-- View 7: Communication Queue
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_communication_queue
WITH (security_invoker=on) AS
SELECT 'EMAIL' as communication_type, el.id as queue_item_id, el.referral_id,
  r.patient_name, r.patient_email as contact, el.email_type as action_type,
  el.status, 'Send email' as action_needed, el.created_at as queued_at, 1 as priority
FROM email_logs el JOIN referrals r ON el.referral_id = r.id
WHERE el.status = 'PENDING'
UNION ALL
SELECT 'CALL', cl.id, cl.referral_id, r.patient_name, r.patient_phone,
  cl.call_type, cl.status, 'Make voice call', cl.scheduled_at,
  CASE WHEN cl.call_type = 'HIGH_RISK_CHECKIN' THEN 1
       WHEN cl.call_type = 'MISSED_APPOINTMENT_FOLLOWUP' THEN 2 ELSE 3 END
FROM call_logs cl JOIN referrals r ON cl.referral_id = r.id
WHERE cl.status = 'SCHEDULED' AND cl.scheduled_at <= NOW()
ORDER BY priority ASC, queued_at ASC;

-- View 8: Recent Activity Feed
-- Note: security_invoker=on ensures RLS policies are respected
CREATE VIEW v_recent_activity
WITH (security_invoker=on) AS
SELECT 
  'REFERRAL_CREATED' as activity_type,
  r.id as referral_id,
  r.patient_name,
  (u.first_name || ' ' || u.last_name) as performed_by,
  'Created ' || r.specialist_type || ' referral' as description,
  r.created_at as activity_time
FROM referrals r
JOIN users u ON r.created_by_id = u.id
WHERE r.created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
  'STATUS_CHANGED',
  sh.referral_id,
  r.patient_name,
  (u.first_name || ' ' || u.last_name),
  'Changed status to ' || sh.status,
  sh.changed_at
FROM status_history sh
JOIN referrals r ON sh.referral_id = r.id
JOIN users u ON sh.changed_by_id = u.id
WHERE sh.changed_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
  'EMAIL_SENT',
  el.referral_id,
  r.patient_name,
  'System',
  'Sent ' || el.email_type || ' email',
  el.sent_at
FROM email_logs el
JOIN referrals r ON el.referral_id = r.id
WHERE el.sent_at >= NOW() - INTERVAL '7 days'
ORDER BY activity_time DESC
LIMIT 50;

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✅ All views created successfully!';
  RAISE NOTICE '📊 Views created:';
  RAISE NOTICE '   1. v_active_referrals - Active referrals with nurse info';
  RAISE NOTICE '   2. v_referral_details - Complete referral information';
  RAISE NOTICE '   3. v_dashboard_summary - Real-time stats';
  RAISE NOTICE '   4. v_urgent_actions - Items requiring attention';
  RAISE NOTICE '   5. v_upcoming_appointments - Next 7 days appointments';
  RAISE NOTICE '   6. v_nurse_activity - Nurse performance tracking';
  RAISE NOTICE '   7. v_communication_queue - Pending emails/calls';
  RAISE NOTICE '   8. v_recent_activity - Activity feed';
END $$;