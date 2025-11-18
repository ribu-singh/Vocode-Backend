# How Client and GCP Server Work Together

This document explains how `websocket_client_with_audio.py` connects to and communicates with the Vocode WebSocket server running on a GCP instance.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Local Machine                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  websocket_client_with_audio.py                       │  │
│  │  - Captures microphone audio                          │  │
│  │  - Plays received audio through speakers              │  │
│  │  - Handles WebSocket communication                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ WebSocket (ws://GCP_IP:3000/conversation)
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    GCP Server Instance                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (main.py)                            │  │
│  │  - Listens on port 3000                              │  │
│  │  - Handles WebSocket connections                     │  │
│  └───────────────────────────┬──────────────────────────┘  │
│                              │                              │
│  ┌───────────────────────────▼──────────────────────────┐  │
│  │  ConversationRouter                                   │  │
│  │  - Manages conversation lifecycle                    │  │
│  │  - Routes audio to transcriber                       │  │
│  │  - Routes text to agent                              │  │
│  │  - Routes agent response to synthesizer              │  │
│  └───┬───────────────┬───────────────┬──────────────────┘  │
│      │               │               │                      │
│  ┌───▼───┐    ┌──────▼──────┐  ┌────▼─────┐              │
│  │Deepgram│    │ChatGPT Agent│  │ElevenLabs│              │
│  │(STT)  │    │             │  │(TTS)     │              │
│  └───────┘    └─────────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Connection Flow

### Step 1: Server Setup (GCP Instance)

1. **Server runs on GCP**:
   ```bash
   # On GCP instance, service runs via systemd
   sudo systemctl start vocode-websocket.service
   ```
   - Server listens on `0.0.0.0:3000`
   - WebSocket endpoint: `/conversation`
   - Full URL: `ws://YOUR_GCP_IP:3000/conversation`

2. **Firewall configured**:
   - Port 3000 is open for incoming connections
   - Firewall rule allows TCP traffic on port 3000

### Step 2: Client Connection (Your Local Machine)

1. **Client starts**:
   ```bash
   python websocket_client_with_audio.py ws://YOUR_GCP_IP:3000/conversation
   ```

2. **WebSocket connection established**:
   - Client opens WebSocket connection to GCP server
   - Server accepts connection (`await websocket.accept()`)

### Step 3: Initial Handshake

**Client sends configuration**:
```json
{
  "type": "websocket_audio_config_start",
  "input_audio_config": {
    "sampling_rate": 16000,
    "audio_encoding": "linear16",
    "chunk_size": 4096
  },
  "output_audio_config": {
    "sampling_rate": 16000,
    "audio_encoding": "linear16"
  },
  "conversation_id": null,
  "subscribe_transcript": true
}
```

**Server processes**:
1. Receives `AudioConfigStartMessage`
2. Creates `WebsocketOutputDevice` for sending audio back
3. Initializes `StreamingConversation` with:
   - **Transcriber**: Deepgram (converts speech → text)
   - **Agent**: ChatGPT (processes text, generates responses)
   - **Synthesizer**: ElevenLabs (converts text → speech)
4. Starts the conversation
5. Sends `ReadyMessage` back to client

**Client receives**:
```json
{
  "type": "websocket_ready"
}
```

### Step 4: Audio Streaming Loop

Once ready, both sides enter a continuous streaming loop:

#### Client → Server (Audio Input)

1. **Microphone capture**:
   - `sounddevice` captures audio at 16kHz, 16-bit, mono
   - Audio callback puts chunks into `audio_input_queue`

2. **Send to server**:
   - Client reads from queue every ~50ms
   - Encodes audio bytes as base64
   - Sends as `AudioMessage`:
     ```json
     {
       "type": "websocket_audio",
       "data": "<base64_encoded_audio_bytes>"
     }
     ```

#### Server Processing Pipeline

1. **Receive audio**:
   - Server receives `AudioMessage`
   - Decodes base64 audio bytes
   - Calls `conversation.receive_audio(audio_bytes)`

2. **Transcription** (Deepgram):
   - Audio chunks sent to Deepgram WebSocket API
   - Deepgram returns transcribed text
   - Server sends transcript to client (if subscribed):
     ```json
     {
       "type": "websocket_transcript",
       "text": "Hello, how are you?",
       "sender": "user",
       "timestamp": 1234567890.123
     }
     ```

3. **Agent processing** (ChatGPT):
   - Transcribed text sent to ChatGPT
   - Agent generates response text
   - Response text sent to synthesizer

4. **Synthesis** (ElevenLabs):
   - Text sent to ElevenLabs WebSocket API
   - ElevenLabs streams audio chunks back
   - Server encodes audio as base64 and sends to client:
     ```json
     {
       "type": "websocket_audio",
       "data": "<base64_encoded_audio_bytes>"
     }
     ```

#### Server → Client (Audio Output)

1. **Receive audio**:
   - Client receives `AudioMessage` from server
   - Decodes base64 audio bytes
   - Puts into `audio_output_queue`

2. **Playback**:
   - Audio output callback reads from queue
   - Resamples from 16kHz → 44.1kHz (to avoid chipmunk sound)
   - Plays through speakers via `sounddevice`

### Step 5: Conversation End

**Client sends stop**:
```json
{
  "type": "websocket_stop"
}
```

**Server processes**:
- Stops conversation loop
- Closes output device
- Terminates conversation
- Closes WebSocket connection

## Key Components

### Client Side (`websocket_client_with_audio.py`)

- **Audio Input**: `sounddevice.InputStream` captures microphone
- **Audio Output**: `sounddevice.OutputStream` plays speakers
- **WebSocket Client**: `websockets` library handles connection
- **Queue Management**: Thread-safe queues buffer audio chunks
- **Resampling**: Converts 16kHz server audio to 44.1kHz for playback

### Server Side (`main.py` + `ConversationRouter`)

- **FastAPI**: Web framework hosting WebSocket endpoint
- **ConversationRouter**: Manages WebSocket connections and conversation lifecycle
- **StreamingConversation**: Orchestrates transcriber, agent, and synthesizer
- **WebsocketOutputDevice**: Sends audio back to client via WebSocket

## Data Flow Example

```
User speaks: "Hello, how are you?"
    │
    ▼
[Microphone] → [16kHz audio chunks] → [Client Queue]
    │
    ▼
[WebSocket] → [GCP Server] → [Deepgram] → "Hello, how are you?"
    │
    ▼
[ChatGPT] → "I'm doing well, thank you for asking!"
    │
    ▼
[ElevenLabs] → [16kHz audio chunks] → [WebSocket] → [Client]
    │
    ▼
[Resample to 44.1kHz] → [Speakers] → User hears response
```

## Network Considerations

### Latency
- **Network latency**: Depends on your location relative to GCP instance
- **Processing latency**: 
  - Deepgram transcription: ~200-500ms
  - ChatGPT response: ~500-2000ms (depends on response length)
  - ElevenLabs synthesis: ~100-300ms
- **Total round-trip**: Typically 1-3 seconds from speech to response

### Bandwidth
- **Audio bitrate**: ~256 kbps (16kHz, 16-bit, mono)
- **Base64 overhead**: ~33% increase
- **Total**: ~340 kbps per direction
- **Bidirectional**: ~680 kbps total

### Firewall Requirements
- **Outbound**: Client needs to connect to GCP IP on port 3000
- **Inbound**: GCP firewall must allow TCP:3000 from your IP (or 0.0.0.0/0)

## Troubleshooting Connection Issues

### Connection Refused
- **Check server is running**: `sudo systemctl status vocode-websocket.service`
- **Check firewall**: Verify port 3000 is open on GCP
- **Check IP**: Ensure you're using the correct external IP

### Audio Issues
- **No audio input**: Check microphone permissions and device selection
- **No audio output**: Check speaker device and volume
- **Choppy audio**: Increase queue sizes or check network latency

### Timeout Errors
- **Network timeout**: Check firewall rules and network connectivity
- **API timeout**: Verify API keys are valid and have quota

## Example Usage

```bash
# 1. Get your GCP instance IP
gcloud compute instances describe YOUR_INSTANCE --zone=YOUR_ZONE \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# 2. Run client (replace with your GCP IP)
python apps/client_backend/clients/websocket_client_with_audio.py \
  ws://34.13.49.144:3000/conversation

# 3. Speak into microphone and hear responses!
```

## Security Notes

- **Current setup**: Uses unencrypted WebSocket (ws://)
- **Production**: Should use WSS (wss://) with SSL/TLS
- **Authentication**: No authentication currently - add if needed
- **CORS**: Configured to allow all origins - restrict in production

