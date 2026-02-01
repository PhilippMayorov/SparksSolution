"""
HACKATHON VERSION - ElevenLabs Agent + Twilio
WebSocket bridge implementation (CORRECT VERSION)
"""

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Connect
import uvicorn
import asyncio
import websockets
import json
import os
from pydantic import BaseModel
from typing import Any, Dict
import re
import time
from dotenv import load_dotenv
from supabase import create_client, Client as SupaBaseClient

load_dotenv()
# ============================================================================
# CONFIGURATION - PUT YOUR CREDENTIALS HERE
# ============================================================================

# ============================================================================
# APP SETUP
# ============================================================================


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],   # includes OPTIONS
    allow_headers=["*"],

)
twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

CALL_CONTEXT: dict[str, dict] = {}

class CallRequest(BaseModel):
    phone_number: str
    dynamic_variables: Dict[str, Any]

@app.get("/")
def home():
    return {"status": "ready", "agent": os.getenv("ELEVENLABS_AGENT_ID")}

def create_flagged_entry(name):
    """
    Look up a patient by name in the referrals table, then create
    a complete entry in the flagged table using that information.

    Args:
        name: The patient name to look up and flag

    Returns:
        dict: Response data with created record or error message
    """
    try:
        # First, get the patient's referral information
        referral_response = supabase.table("referrals").select("*").eq(
            "patient_name", name
        ).execute()

        if not referral_response.data or len(referral_response.data) == 0:
            print(f"No referral found for patient: {name}")
            return {"success": False, "message": "No referral found for patient"}

        referral = referral_response.data[0]

        # Create a flags entry using the referral's id
        flags_data = {
            "referral_id": referral.get("id"),
            "created_by_id": referral.get("created_by_id"),
            "title": f"Flagged: {name}",
            "description": f"Patient {name} has been flagged for follow-up from nurse.",
            "priority": "medium",
            "status": "open",
        }

        response = supabase.table("flags").insert(flags_data).execute()

        if response.data and len(response.data) > 0:
            print(f"Successfully created flagged entry for {name}")
            return {"success": True, "data": response.data}
        else:
            print(f"Failed to create flagged entry for {name}")
            return {"success": False, "message": "No record created"}

    except Exception as e:
        print(f"Error creating flagged entry: {e}")
        return {"success": False, "error": str(e)}


def get_scheduled_dates(specialist_type):
    """
    Get all scheduled dates for a patient by name.

    Args:
        patient_name: The name of the patient to search for

    Returns:
        dict: Response data with list of scheduled dates or error message
    """
    try:
        # Query all referrals matching patient_name and select scheduled_date
        response = supabase.table("referrals").select(
            "id, scheduled_date, status"
        ).eq("specialist_type", specialist_type.upper()).execute()

        if response.data and len(response.data) > 0:
            # Extract just the scheduled_date values (filter out None values)
            scheduled_dates = [
                record["scheduled_date"]
                for record in response.data
                if record["scheduled_date"] is not None
            ]

            print(f"Found {len(response.data)} record(s) for {specialist_type}")
            print(f"Scheduled dates: {specialist_type}")

            return scheduled_dates

        else:
            print(f"No records found for specialist type: {specialist_type}")
            return False

    except Exception as e:
        print(f"Error retrieving scheduled dates: {e}")
        return {"success": False, "error": str(e)}


@app.post("/make-call")
def make_call(req: CallRequest):
    """Make a call"""
    try:
        call = twilio_client.calls.create(
            to=req.phone_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            url=f"{os.getenv('WEBHOOK_BASE_URL')}/incoming-call",
            method='POST',
        )

        times = get_scheduled_dates(req.dynamic_variables['specialist_type'])

        req.dynamic_variables['unavailable_times'] = json.dumps(times)

        CALL_CONTEXT[call.sid] = req.dynamic_variables

        return {"success": True, "call_sid": call.sid}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/incoming-call")
@app.get("/incoming-call")
def incoming_call():
    response = VoiceResponse()

    connect = Connect()

    ws_url = os.getenv("WEBHOOK_BASE_URL").replace("https://", "wss://") + "/media-stream"
    connect.stream(url=ws_url, track="inbound_track")

    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


def update_scheduled_date(patient_name, new_scheduled_date):
    """
    Update the scheduled date for a patient by name.

    Args:
        patient_name: The name of the patient to update
        new_scheduled_date: The new scheduled date in format 'YYYY-MM-DD'

    Returns:
        dict: Response data with updated record(s) or error message
    """
    try:
        # Update the referral_date for matching patient_name
        response = supabase.table("referrals").update({
            "scheduled_date": new_scheduled_date
        }).eq("patient_name", patient_name).execute()

        if response.data and len(response.data) > 0:
            print(f"Successfully updated scheduled date for {patient_name} to {new_scheduled_date}")
            print(f"Updated {len(response.data)} record(s)")
            return {"success": True, "data": response.data}
        else:
            print(f"No records found for patient name: {patient_name}")
            return {"success": False, "message": "No matching records found"}

    except Exception as e:
        print(f"Error updating scheduled date: {e}")
        return {"success": False, "error": str(e)}


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket bridge between Twilio and ElevenLabs
    """
    await websocket.accept()
    print("✅ Twilio connected")
    hangup_after_audio = asyncio.Event()
    suppress_agent_audio = False
    last_audio_time = 0.0

    # Connect to ElevenLabs agent
    elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={os.getenv('ELEVENLABS_AGENT_ID')}"

    try:
        async with websockets.connect(
                elevenlabs_url,
                additional_headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY")}
        ) as elevenlabs_ws:
            print("✅ ElevenLabs agent connected")
            stream_sid = None
            call_sid = None
            stream_ready = asyncio.Event()

            # Create tasks for bidirectional communication
            async def twilio_to_elevenlabs():
                """Forward audio from Twilio to ElevenLabs"""
                try:
                    while True:
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        if message["event"] == "media":
                            if message["media"].get("track") not in (None, "inbound"):
                                continue
                            await elevenlabs_ws.send(json.dumps({"user_audio_chunk": message["media"]["payload"]}))
                        elif message['event'] == 'start':
                            nonlocal stream_sid, call_sid
                            stream_sid = message["start"]["streamSid"]
                            call_sid = message["start"].get("callSid")
                            stream_ready.set()
                            print("📞 Call started", "callSid=", call_sid)

                            dyn = CALL_CONTEXT.get(call_sid, {})
                            await elevenlabs_ws.send(json.dumps({
                                "type": "conversation_initiation_client_data",
                                "dynamic_variables": {k: str(v) for k, v in dyn.items()}
                            }))

                        elif message['event'] == 'stop':
                            print("📞 Call ended")
                            break

                except WebSocketDisconnect:
                    print("Twilio disconnected")

            async def elevenlabs_to_twilio():
                nonlocal last_audio_time, suppress_agent_audio
                await stream_ready.wait()

                try:
                    while True:
                        msg = await elevenlabs_ws.recv()
                        if isinstance(msg, bytes):
                            # ElevenLabs events are typically JSON text; if you ever get bytes, log it.
                            print("ELEVEN (bytes) len:", len(msg))
                            continue

                        data = json.loads(msg)
                        t = data.get("type")

                        if t == "conversation_initiation_metadata":
                            meta = data.get("conversation_initiation_metadata_event", {})
                            print("📊 Conversation ID:", meta.get("conversation_id"))
                            print("🎛️ Formats:", meta.get("user_input_audio_format"), "->",
                                  meta.get("agent_output_audio_format"))

                        elif t == "audio":
                            last_audio_time = time.time()

                            if suppress_agent_audio:
                                # Don't forward any more agent audio to Twilio
                                continue

                            audio_b64 = data["audio_event"]["audio_base_64"]
                            await websocket.send_text(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_b64}
                            }))

                        elif t == "ping":
                            # MUST respond with pong
                            event_id = data["ping_event"]["event_id"]
                            await elevenlabs_ws.send(json.dumps({
                                "type": "pong",
                                "event_id": event_id
                            }))

                        elif t == "interruption":
                            await websocket.send_text(json.dumps({
                                "event": "clear",
                                "streamSid": stream_sid
                            }))

                        elif t == "agent_response":
                            text = data["agent_response_event"]["agent_response"]
                            print("🤖 raw:", text)

                            # Check if the response contains "Rescheduled"
                            if "Rescheduled" in text:
                                print("🚫 'Rescheduled' detected - will suppress audio in 7 seconds")

                                payload = {}

                                # Extract data using regex
                                rescheduled_match = re.search(r'"Rescheduled"\s*:\s*(true|false)', text, re.IGNORECASE)
                                if rescheduled_match:
                                    payload["Rescheduled"] = rescheduled_match.group(1).lower() == "true"

                                # Extract name - look for patterns like "name":"Parth Joshi"
                                name_match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
                                if name_match:
                                    payload["name"] = name_match.group(1)

                                # Extract scheduled_date - look for patterns like "scheduled_date":"2026-02-07 11:00:00+00:00"
                                date_match = re.search(r'"scheduled_date"\s*:\s*"([^"]+)"', text)
                                if date_match:
                                    payload["scheduled_date"] = date_match.group(1)

                                # Save to CALL_CONTEXT
                                CALL_CONTEXT.setdefault(call_sid, {})
                                CALL_CONTEXT[call_sid]["agent_result"] = payload


                                if not payload.get("Rescheduled"):
                                    create_flagged_entry(payload["name"])
                                # Update database if we have the necessary data
                                elif payload.get("name") and payload.get("scheduled_date"):
                                    update_scheduled_date(payload["name"], payload["scheduled_date"])
                                    print("✅ Saved data:", payload)
                                else:
                                    print("⚠️ Incomplete data extracted:", payload)

                                # Schedule suppression after 7 seconds
                                async def delayed_suppress():
                                    await asyncio.sleep(5.5)
                                    suppress_agent_audio = True

                                    # Clear buffer
                                    if stream_sid:
                                        await websocket.send_text(json.dumps({
                                            "event": "clear",
                                            "streamSid": stream_sid
                                        }))

                                    print("🚫 Audio suppressed after 7 seconds")
                                    # Trigger instant hangup
                                    hangup_after_audio.set()

                                asyncio.create_task(delayed_suppress())

                except websockets.exceptions.ConnectionClosed:
                    print("ElevenLabs disconnected")

            async def end_elevenlabs():
                try:
                    # Ask ElevenLabs to terminate the conversation
                    await elevenlabs_ws.send(json.dumps({"command_type": "end_call"}))
                except Exception as e:
                    print("⚠️ Could not send end_call to ElevenLabs:", e)

                try:
                    await elevenlabs_ws.close()
                except Exception as e:
                    print("⚠️ Could not close ElevenLabs WS:", e)

            async def hangup_watcher():
                await stream_ready.wait()
                await hangup_after_audio.wait()

                # Hangup instantly (no delay)
                await end_elevenlabs()

                # End the Twilio call immediately
                if call_sid:
                    try:
                        twilio_client.calls(call_sid).update(status="completed")
                        print("📴 Hung up callSid:", call_sid)
                    except Exception as e:
                        print("❌ Hangup failed:", e)

            # Run both directions concurrently
            await asyncio.gather(
                twilio_to_elevenlabs(),
                elevenlabs_to_twilio(),
                hangup_watcher()
            )

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await websocket.close()