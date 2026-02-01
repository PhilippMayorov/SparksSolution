"""
HACKATHON VERSION - ElevenLabs Agent + Twilio
WebSocket bridge implementation (CORRECT VERSION)
"""

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from twilio.rest import Client
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

load_dotenv()

WEBHOOK_BASE_URL = os.environ["WEBHOOK_BASE_URL"]

TWILIO_ACCOUNT_SID= os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN= os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER= os.getenv("TWILIO_PHONE_NUMBER")

ELEVENLABS_API_KEY= os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID= os.getenv("ELEVENLABS_AGENT_ID")

# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

CALL_CONTEXT: dict[str, dict] = {}

class CallRequest(BaseModel):
    phone_number: str
    dynamic_variables: Dict[str, Any]

@app.get("/")
def home():
    return {"status": "ready", "agent": ELEVENLABS_AGENT_ID}


@app.post("/make-call")
def make_call(req: CallRequest):
    """Make a call"""
    try:
        call = twilio_client.calls.create(
            to=req.phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{WEBHOOK_BASE_URL}/incoming-call",
            method='POST',
        )

        CALL_CONTEXT[call.sid] = req.dynamic_variables

        return {"success": True, "call_sid": call.sid}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/incoming-call")
@app.get("/incoming-call")
def incoming_call():
    response = VoiceResponse()

    connect = Connect()

    ws_url = WEBHOOK_BASE_URL.replace("https://", "wss://") + "/media-stream"
    connect.stream(url=ws_url, track="inbound_track")

    response.append(connect)
    return Response(content=str(response), media_type="application/xml")



@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket bridge between Twilio and ElevenLabs
    """
    await websocket.accept()
    print("✅ Twilio connected")
    hangup_after_audio = asyncio.Event()
    last_audio_time = 0.0

    # Connect to ElevenLabs agent
    elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"

    try:
        async with websockets.connect(
                elevenlabs_url,
                additional_headers={"xi-api-key": ELEVENLABS_API_KEY}
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
                            nonlocal last_audio_time
                            last_audio_time = time.time()

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
                            # optional: useful debug
                            text = data["agent_response_event"]["agent_response"]
                            print("🤖:", text)
                            m = re.search(r"confirmed for (.+?) with the", text, re.IGNORECASE)

                            if m and call_sid:
                                selected_time_str = m.group(1).strip()

                                # Store it (in-memory)
                                CALL_CONTEXT.setdefault(call_sid, {})
                                CALL_CONTEXT[call_sid]["selected_time"] = selected_time_str

                                print("✅ Stored selected_time:", selected_time_str)

                                # Trigger hangup AFTER audio finishes (see next section)
                                hangup_after_audio.set()

                        else:
                            # helpful while debugging
                            # print("ELEVEN other:", data)
                            pass

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

                # Wait until ElevenLabs stops sending audio for a moment
                while True:
                    await asyncio.sleep(0.25)
                    if time.time() - last_audio_time > 1.0:
                        break

                await asyncio.sleep(11)
                await end_elevenlabs()

                # End the Twilio call
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)