#!/usr/bin/env python3
"""
Test direct database connection for appointment creation.
"""
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.supabase_client import get_supabase_client
import asyncio

async def test_create_appointment():
    """Test creating an appointment directly."""
    db = get_supabase_client()
    
    test_data = {
        "patient_name": "Test Patient",
        "patient_phone": "555-1234",
        "patient_email": "test@example.com",
        "scheduled_at": "2024-01-15T14:30:00Z",
        "appointment_type": "Cardiology",
        "notes": "Test appointment"
    }
    
    print("Creating appointment with data:", test_data)
    
    try:
        result = await db.create_appointment(test_data)
        print("✅ Success!")
        print("Created appointment:", result)
        return result
    except Exception as e:
        print("❌ Error:", e)
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_create_appointment())
    if result:
        print("\n🎉 Appointment created successfully!")
        print(f"ID: {result.get('id')}")
        print(f"Patient: {result.get('patient_name')}")
        print(f"Scheduled: {result.get('scheduled_at')}")
    else:
        print("\n❌ Failed to create appointment")