# Nurse Appointment Management System

A hackathon project for managing patient appointments with automated outbound calling for rescheduling missed appointments.

## 🎯 Overview

This system provides a tablet-based web app for nurses to:

- View and manage patient appointments via calendar
- Automatically call patients who miss appointments (via ElevenLabs AI)
- Receive follow-up flags when automated rescheduling fails
- Sync appointments with Google Calendar

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  React Frontend │────▶│  FastAPI Backend│────▶│    Supabase     │
│  (Tablet App)   │     │                 │     │   (PostgreSQL)  │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
           ┌────────────┐ ┌────────────┐ ┌────────────┐
           │ ElevenLabs │ │  Google    │ │  Webhooks  │
           │ Outbound   │ │  Calendar  │ │  (Inbound) │
           │ Calling    │ │  API       │ │            │
           └────────────┘ └────────────┘ └────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- ElevenLabs account (with Conversational AI access)
- Google Cloud project (for Calendar API)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../.env.example .env
# Edit .env with your credentials

# Run the server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### Database Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com)
2. Go to SQL Editor in your project dashboard
3. Copy and run the contents of `database/schema.sql`
4. Copy your API keys to `.env`

## 📁 Project Structure

```
/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── models/
│   │   └── schemas.py      # Pydantic models
│   ├── routers/
│   │   ├── appointments.py # Appointment CRUD
│   │   ├── auth.py         # Authentication
│   │   ├── calendar.py     # Google Calendar sync
│   │   ├── calls.py        # ElevenLabs call management
│   │   ├── flags.py        # Follow-up flags
│   │   └── webhooks.py     # Webhook handlers
│   └── services/
│       ├── supabase_client.py
│       ├── elevenlabs_service.py
│       └── google_calendar_service.py
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # Reusable components
│   │   │   ├── CalendarView.jsx
│   │   │   ├── AppointmentCard.jsx
│   │   │   └── FlagBanner.jsx
│   │   └── pages/         # Page components
│   │       ├── Dashboard.jsx
│   │       ├── AppointmentDetail.jsx
│   │       ├── Flags.jsx
│   │       └── Login.jsx
│   └── package.json
│
├── database/
│   └── schema.sql         # Supabase database schema
│
├── shared/
│   └── types.ts           # Shared TypeScript types
│
└── .env.example           # Environment variables template
```

## 🔄 Workflow

### Missed Appointment → Automated Call Flow

```
1. Appointment time passes without check-in
          │
          ▼
2. Backend marks appointment as "missed"
          │
          ▼
3. Nurse can trigger call OR automated job triggers
          │
          ▼
4. Backend calls ElevenLabs API to initiate outbound call
          │
          ▼
5. ElevenLabs AI agent calls patient
   - Explains missed appointment
   - Offers rescheduling options
   - Collects new preferred time
          │
          ▼
6. Call ends → ElevenLabs sends webhook to /api/webhooks/elevenlabs
          │
          ├─── SUCCESS (Rescheduled) ───┐
          │                             ▼
          │                    Update appointment
          │                    Sync to Google Calendar
          │                    Send new invite
          │
          └─── FAILURE (Declined/No Answer) ───┐
                                               ▼
                                      Create follow-up flag
                                      Nurse sees on dashboard
```

### Webhook Processing

```python
# When ElevenLabs calls our webhook:
POST /api/webhooks/elevenlabs
{
    "call_id": "elabs-123",
    "status": "completed",
    "outcome": "rescheduled",
    "new_appointment_time": "2026-02-05T14:00:00Z",
    "metadata": {
        "appointment_id": "apt-uuid",
        "call_attempt_id": "call-uuid"
    }
}

# Backend then:
# 1. Validates webhook signature
# 2. Finds call attempt record
# 3. If rescheduled: update appointment + sync calendar
# 4. If failed: create nurse follow-up flag
```

## 🔑 Environment Variables

See `.env.example` for all required variables:

| Variable                    | Description                             |
| --------------------------- | --------------------------------------- |
| `SUPABASE_URL`              | Your Supabase project URL               |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side) |
| `ELEVENLABS_API_KEY`        | ElevenLabs API key                      |
| `ELEVENLABS_AGENT_ID`       | Your conversational agent ID            |
| `GOOGLE_CLIENT_ID`          | Google OAuth client ID                  |
| `GOOGLE_CLIENT_SECRET`      | Google OAuth client secret              |
| `BACKEND_BASE_URL`          | Public URL for webhooks                 |
| `WEBHOOK_SECRET`            | Secret for verifying webhooks           |

## 🛠️ Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Local Webhook Testing

Use [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 8000
# Update BACKEND_BASE_URL in .env with ngrok URL
```

## 📝 API Endpoints

### Appointments

- `GET /api/appointments/` - List appointments
- `POST /api/appointments/` - Create appointment
- `GET /api/appointments/{id}` - Get appointment
- `PATCH /api/appointments/{id}` - Update appointment
- `POST /api/appointments/{id}/reschedule` - Reschedule
- `POST /api/appointments/{id}/mark-missed` - Mark as missed

### Calls

- `POST /api/calls/initiate` - Initiate outbound call
- `GET /api/calls/{id}` - Get call status

### Flags

- `GET /api/flags/open` - Get open flags
- `POST /api/flags/{id}/resolve` - Resolve flag
- `POST /api/flags/{id}/dismiss` - Dismiss flag

### Calendar

- `POST /api/calendar/sync/{appointment_id}` - Sync to Google Calendar

### Webhooks

- `POST /api/webhooks/elevenlabs` - ElevenLabs callback

## 🚧 TODOs

- [ ] Implement actual authentication (currently stubbed)
- [ ] Add background job for auto-detecting missed appointments
- [ ] Implement retry logic for failed calls
- [ ] Add real-time updates via WebSocket
- [ ] Implement proper ElevenLabs webhook signature verification
- [ ] Add comprehensive test coverage
- [ ] Set up CI/CD pipeline

## 📄 License

MIT License - Built for SparksHacks Hackathon 2026
