# client_backend

WebSocket-based real-time conversation server for Vocode. This server provides a WebSocket endpoint at `/conversation` that accepts audio input and streams audio responses back to clients.

## Quick Start

### 1. Set up environment variables

Create a `.env` file with your API keys:

```bash
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

### 2. Configure your agent

Edit `main.py` to customize your agent, transcriber, and synthesizer settings.

### 3. Run the server

#### Option A: Using uvicorn directly

```bash
cd apps/client_backend
uvicorn main:app --host 0.0.0.0 --port 3000
```

#### Option B: Using Docker

```bash
# Build the image
docker build -t vocode-client-backend .

# Run the container
docker run --env-file=.env -p 3000:3000 -t vocode-client-backend
```

The server will be available at `http://localhost:3000` with the WebSocket endpoint at `ws://localhost:3000/conversation`.

## WebSocket Protocol

### Connection

Connect to `ws://localhost:3000/conversation` (or your server URL).

### Initial Message

Send an `AudioConfigStartMessage` as the first message:

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

### Server Response

The server will respond with a `ReadyMessage`:

```json
{
  "type": "websocket_ready"
}
```

### Sending Audio

After receiving the ready message, send audio chunks as `AudioMessage`:

```json
{
  "type": "websocket_audio",
  "data": "<base64_encoded_audio_bytes>"
}
```

### Receiving Messages

The server will send:
- **AudioMessage**: Audio chunks for playback (base64 encoded)
- **TranscriptMessage**: Transcript updates (if `subscribe_transcript` is true)

```json
{
  "type": "websocket_transcript",
  "text": "Hello, how are you?",
  "sender": "user",
  "timestamp": 1234567890.123
}
```

### Ending Conversation

Send a `StopMessage` to end the conversation:

```json
{
  "type": "websocket_stop"
}
```

## Example Client

See `websocket_client_example.py` for a basic Python client example:

```bash
python websocket_client_example.py ws://localhost:3000
```

## GCP Deployment

For deploying to Google Cloud Platform, see [DEPLOYMENT_GCP.md](./DEPLOYMENT_GCP.md) for detailed instructions.

Quick steps:
1. Deploy the application to your GCP instance
2. Set up the systemd service using `vocode-websocket.service`
3. Configure firewall rules to allow port 3000
4. Connect using `ws://YOUR_GCP_IP:3000/conversation`

## Using with React SDK

For production use with the Vocode React SDK, you'll need to:
1. Host your server (or use a tunnel like ngrok)
2. Update your React app to connect to your server's WebSocket endpoint
3. Use WSS (WebSocket Secure) for production deployments

## API Configuration

The server uses:
- **Transcriber**: Deepgram (default) - requires `DEEPGRAM_API_KEY`
- **Agent**: ChatGPT (default) - requires `OPENAI_API_KEY`
- **Synthesizer**: ElevenLabs (default) - requires `ELEVENLABS_API_KEY`

You can customize these in `main.py` by modifying the `ConversationRouter` initialization.
