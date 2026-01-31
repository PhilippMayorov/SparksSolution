#!/usr/bin/env python3
import requests
import json

# Test appointment creation
url = "http://localhost:8000/api/appointments"
data = {
    "patient_name": "Jane Doe",
    "patient_phone": "555-1234", 
    "patient_email": "jane.doe@email.com",
    "scheduled_at": "2024-01-15T14:30:00Z",
    "appointment_type": "Cardiology",
    "notes": "Routine checkup"
}

headers = {"Content-Type": "application/json"}

print("Testing appointment creation...")
print(f"Sending request to: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200 or response.status_code == 201:
        print("✅ Appointment created successfully!")
    else:
        print("❌ Error creating appointment")
        
except Exception as e:
    print(f"Error: {e}")