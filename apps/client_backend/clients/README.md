# WebSocket Clients

This directory contains example client implementations for connecting to the Vocode WebSocket server.

## Available Client

### `websocket_client_with_audio.py` - Full Audio Client

A complete client that captures microphone audio and plays received audio, matching the functionality of `stream-conversation.py`.

**Requirements:**
```bash
pip install websockets sounddevice numpy scipy
```

**Usage:**
```bash
python websocket_client_with_audio.py ws://YOUR_SERVER:3000/conversation
```

**Features:**
- Real-time microphone capture
- Audio playback with resampling (16kHz → 44.1kHz)
- Transcript display
- Full conversation flow

## Server Requirements

Make sure your server is running and accessible. See the main [README.md](../README.md) for server setup instructions.

## Example Server URLs

- Local: `ws://localhost:3000/conversation`
- GCP: `ws://YOUR_GCP_IP:3000/conversation`
- Production (SSL): `wss://yourdomain.com/conversation`

## Notes

- This client is standalone and doesn't require the vocode library
- It can be copied and used independently
- For web/frontend clients, see the main README for WebSocket protocol details

