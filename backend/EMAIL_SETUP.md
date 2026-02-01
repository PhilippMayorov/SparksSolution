# Email System Setup & Usage Guide

## ✅ Verification Complete

All email system components have been tested and verified working:

- ✓ Email service initialized successfully
- ✓ All 5 email templates render correctly
- ✓ Email router endpoints registered
- ✓ Integration with referrals workflow complete
- ✓ Server startup verified

## 🚀 Quick Start

### 1. Install Dependencies (Already Done)

```bash
pip install sendgrid==6.11.0 jinja2==3.1.3
```

### 2. Set Up SendGrid Account

1. Create a free account at https://sendgrid.com
2. Navigate to **Settings > API Keys**
3. Click **Create API Key**
4. Give it a name (e.g., "Nurse Referral System")
5. Select **Full Access** or **Mail Send** permissions
6. Copy the API key (you won't see it again!)

### 3. Verify Sender Email

1. Go to **Settings > Sender Authentication**
2. Choose **Single Sender Verification** (easiest for development)
3. Enter your email address and clinic details
4. Check your email and click the verification link

### 4. Configure Environment Variables

Add these to your `.env` file:

```bash
# SendGrid Configuration
SENDGRID_API_KEY=SG.your_actual_api_key_here
SENDGRID_FROM_EMAIL=your_verified_email@example.com
SENDGRID_FROM_NAME=Your Clinic Name
SENDGRID_REPLY_TO_EMAIL=support@example.com  # Optional
```

### 5. Start the Server

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload
```

## 📧 Email Types Available

### 1. Referral Created
Sent when a new referral is created
- **Trigger**: POST `/api/referrals/`
- **Template**: `referral_created.html`
- **Contents**: Specialist type, condition, urgency, scheduled date

### 2. Appointment Confirmed
Sent when an appointment is scheduled
- **Trigger**: POST `/api/referrals/{id}/schedule`
- **Template**: `appointment_confirmed.html`
- **Contents**: Appointment time, specialist, what to bring

### 3. Appointment Reminder
For upcoming appointment reminders
- **Trigger**: Manual via POST `/api/emails/send`
- **Template**: `appointment_reminder.html`
- **Contents**: Appointment date/time, location, specialist

### 4. Appointment Rescheduled
Sent when an appointment is rescheduled
- **Trigger**: POST `/api/referrals/{id}/reschedule`
- **Template**: `appointment_rescheduled.html`
- **Contents**: Old time, new time, reason

### 5. Follow-Up
General follow-up communications
- **Trigger**: Manual via POST `/api/emails/send`
- **Template**: `follow_up.html`
- **Contents**: Custom message, referral details

## 🔌 API Endpoints

### List Email Logs
```http
GET /api/emails/?referral_id={uuid}&status=SENT&limit=50
```

### Send Email Manually
```http
POST /api/emails/send
Content-Type: application/json

{
  "referral_id": "uuid-here",
  "email_type": "APPOINTMENT_CONFIRMED",
  "recipient_email": "patient@example.com",
  "subject": "Your Appointment is Confirmed",
  "calendar_invite_attached": false
}
```

### Get Email Log
```http
GET /api/emails/{email_id}
```

### Send Bulk Emails (Queue)
```http
POST /api/emails/send-bulk?email_type=APPOINTMENT_REMINDER
Content-Type: application/json

["uuid1", "uuid2", "uuid3"]
```

## 🔄 Automatic Email Workflow

Emails are sent automatically when:

1. **Creating a referral** (if `patient_email` is provided)
   - Sends `REFERRAL_CREATED` email
   - Logged in `email_logs` table

2. **Scheduling an appointment**
   - Sends `APPOINTMENT_CONFIRMED` email
   - Includes calendar invite status

3. **Rescheduling an appointment**
   - Sends `APPOINTMENT_RESCHEDULED` email
   - Shows old and new times

All emails are:
- Logged in the database (`email_logs` table)
- Non-blocking (failures don't stop the workflow)
- HTML formatted with professional templates
- Tracked with SendGrid message IDs

## 🧪 Testing

### Run Test Suite
```bash
cd backend
python test_email_system.py
```

### Test with cURL
```bash
# Send a test email (requires valid referral_id)
curl -X POST http://localhost:8000/api/emails/send \
  -H "Content-Type: application/json" \
  -d '{
    "referral_id": "your-referral-uuid",
    "email_type": "APPOINTMENT_CONFIRMED",
    "recipient_email": "test@example.com",
    "subject": "Test Email",
    "calendar_invite_attached": false
  }'
```

### List Email Logs
```bash
curl http://localhost:8000/api/emails/
```

## 📝 Email Log Schema

All sent emails are logged with:
- `id`: Unique email log ID
- `referral_id`: Associated referral
- `email_type`: Type of email sent
- `recipient_email`: Recipient address
- `subject`: Email subject
- `status`: PENDING, SENT, FAILED, BOUNCED
- `sendgrid_message_id`: SendGrid tracking ID
- `error_message`: Error details if failed
- `calendar_invite_attached`: Whether calendar invite was included
- `sent_at`: Timestamp when sent
- `created_at`: Timestamp when queued

## 🎨 Customizing Templates

Templates are in `backend/templates/emails/`:

- `referral_created.html`
- `appointment_reminder.html`
- `appointment_confirmed.html`
- `appointment_rescheduled.html`
- `follow_up.html`
- `base.html` (shared base template)

To customize:
1. Edit the HTML files
2. Use Jinja2 syntax for dynamic content: `{{ variable_name }}`
3. Maintain the existing variables used by the service
4. Test with the test suite after changes

## 🔐 Security Notes

1. **Never commit `.env`** - It contains your API key
2. **Use environment variables** - Never hardcode credentials
3. **Verify sender email** - SendGrid requires verification
4. **Monitor usage** - Free tier has daily limits (100 emails/day)
5. **Review logs** - Check `email_logs` table for delivery status

## 📊 Monitoring

### Check Email Status
```python
from services import get_supabase_client

db = get_supabase_client()
emails = await db.get_pending_emails()  # Get pending emails
emails = await db.get_email_logs_by_referral(referral_id)  # Get by referral
```

### Dashboard Stats
The dashboard already tracks:
- `emails_pending`: Count of pending emails
- Email logs per referral via `/api/referrals/{id}/communications`

## 🐛 Troubleshooting

### Email Not Sending
1. Check SendGrid API key is valid
2. Verify sender email is verified in SendGrid
3. Check email logs for error messages: `SELECT * FROM email_logs WHERE status = 'FAILED'`
4. Review server logs for exceptions

### Template Errors
1. Verify all templates exist in `templates/emails/`
2. Check Jinja2 syntax in templates
3. Ensure required variables are passed to templates

### Import Errors
1. Ensure dependencies are installed: `pip install -r requirements.txt`
2. Check virtual environment is activated
3. Verify Python path includes backend directory

## 📚 Documentation

- SendGrid Docs: https://docs.sendgrid.com/
- Jinja2 Docs: https://jinja.palletsprojects.com/
- FastAPI Docs: https://fastapi.tiangolo.com/

## ✨ Features

- ✅ Professional HTML email templates
- ✅ Automatic email sending on workflow events
- ✅ Comprehensive email logging
- ✅ Non-blocking error handling
- ✅ SendGrid integration
- ✅ Template rendering with Jinja2
- ✅ RESTful API endpoints
- ✅ Bulk email support (queuing)
- ✅ Email status tracking
- ✅ Integration with referral workflow

---

**Ready to go!** Just add your SendGrid credentials to `.env` and start sending emails! 🚀
