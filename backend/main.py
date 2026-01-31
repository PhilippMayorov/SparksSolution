"""
FastAPI main application entry point.

This backend handles:
- Patient and referral management via Supabase
- ElevenLabs outbound calling integration
- Google Calendar sync
- Webhook processing from ElevenLabs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, referrals, calls, flags, calendar, webhooks

app = FastAPI(
    title="Nurse Referral Management API",
    description="Backend for nurse tablet app with referral scheduling and automated calling",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(referrals.router, prefix="/api/referrals", tags=["Referrals"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(flags.router, prefix="/api/flags", tags=["Flags"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Nurse Referral API is running"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    from services.supabase_client import get_supabase_client
    
    health_status = {
        "status": "healthy",
        "services": {
            "supabase": "unknown",
            "elevenlabs": "configured",
            "google_calendar": "configured"
        }
    }
    
    try:
        # Check Supabase connectivity
        db = get_supabase_client()
        test_result = db.client.table("users").select("count", count="exact").execute()
        health_status["services"]["supabase"] = "connected"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["supabase"] = f"error: {str(e)}"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
