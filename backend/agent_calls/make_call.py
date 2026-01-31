"""
HACKATHON VERSION - ElevenLabs Agent + Twilio
WebSocket bridge implementation (CORRECT VERSION)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
import uvicorn
import asyncio
import websockets
import json
import base64
import os

WEBHOOK_BASE_URL = os.environ["WEBHOOK_BASE_URL"]

# ============================================================================
# CONFIGURATION - PUT YOUR CREDENTIALS HERE
# ============================================================================

###PASTE API KEYS HERE

# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.get("/")
def home():
    return {"status": "ready", "agent": ELEVENLABS_AGENT_ID}


@app.post("/make-call")
def make_call(phone_number: str):
    """Make a call"""
    try:
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{WEBHOOK_BASE_URL}/incoming-call",
            method='POST',
        )
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

    # Connect to ElevenLabs agent
    elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"

    try:
        async with websockets.connect(
                elevenlabs_url,
                additional_headers={"xi-api-key": ELEVENLABS_API_KEY}
        ) as elevenlabs_ws:
            print("✅ ElevenLabs agent connected")
            stream_sid = None
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
                            nonlocal stream_sid
                            stream_sid = message["start"]["streamSid"]
                            stream_ready.set()
                            print("📞 Call started")
                            # Send initial config to ElevenLabs if needed

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
                            audio_b64 = data["audio_event"]["audio_base_64"]

                            # Send to Twilio (Twilio expects mulaw/8000 base64)
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
                            print("🤖:", data["agent_response_event"]["agent_response"])

                        else:
                            # helpful while debugging
                            # print("ELEVEN other:", data)
                            pass

                except websockets.exceptions.ConnectionClosed:
                    print("ElevenLabs disconnected")

            # Run both directions concurrently
            await asyncio.gather(
                twilio_to_elevenlabs(),
                elevenlabs_to_twilio()
            )

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)