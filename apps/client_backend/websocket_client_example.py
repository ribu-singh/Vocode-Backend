"""
Example WebSocket client for connecting to Vocode's websocket conversation endpoint on GCP.

This example demonstrates how to connect to a deployed GCP server and send/receive audio.

Requirements:
    pip install websockets

Usage:
    python websocket_client_example.py ws://YOUR_GCP_IP:3000/conversation
    python websocket_client_example.py wss://yourdomain.com/conversation  # If using SSL
"""

import asyncio
import base64
import json
import sys
import websockets
from typing import Optional

# WebSocket message types matching the server protocol
class WebSocketMessageType:
    BASE = "websocket_base"
    START = "websocket_start"
    AUDIO = "websocket_audio"
    TRANSCRIPT = "websocket_transcript"
    READY = "websocket_ready"
    STOP = "websocket_stop"
    AUDIO_CONFIG_START = "websocket_audio_config_start"


async def websocket_client_example(server_url: str):
    """
    Connect to the Vocode websocket server and demonstrate the conversation flow.
    
    Args:
        server_url: The WebSocket URL of the server (e.g., ws://YOUR_IP:3000/conversation)
    """
    print(f"Connecting to {server_url}...")
    
    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected! Sending initial configuration...")
            
            # Send the initial AudioConfigStartMessage
            start_message = {
                "type": WebSocketMessageType.AUDIO_CONFIG_START,
                "input_audio_config": {
                    "sampling_rate": 16000,
                    "audio_encoding": "linear16",
                    "chunk_size": 4096,
                },
                "output_audio_config": {
                    "sampling_rate": 16000,
                    "audio_encoding": "linear16",
                },
                "conversation_id": None,
                "subscribe_transcript": True,  # Subscribe to transcript events
            }
            
            await websocket.send(json.dumps(start_message))
            print("✓ Configuration sent. Waiting for ready message...")
            
            # Wait for ready message
            ready_response = await websocket.recv()
            ready_data = json.loads(ready_response)
            print(f"✓ Received: {ready_data}")
            
            if ready_data.get("type") == WebSocketMessageType.READY:
                print("\n✓ Server is ready! You can now send audio messages.")
                print("\n" + "="*60)
                print("WebSocket Protocol Guide:")
                print("="*60)
                print("\n1. Send AudioMessage to send audio chunks:")
                print('   {"type": "websocket_audio", "data": "<base64_encoded_audio>"}')
                print("\n2. Receive messages:")
                print("   - AudioMessage: Audio chunks for playback")
                print("   - TranscriptMessage: Transcript updates")
                print("\n3. End conversation:")
                print('   {"type": "websocket_stop"}')
                print("="*60)
                
                # Example: Listen for messages for a few seconds
                print("\nListening for messages (press Ctrl+C to stop)...")
                try:
                    async def receive_messages():
                        while True:
                            message = await websocket.recv()
                            data = json.loads(message)
                            msg_type = data.get("type")
                            
                            if msg_type == WebSocketMessageType.AUDIO:
                                audio_len = len(base64.b64decode(data.get("data", "")))
                                print(f"📢 Received audio chunk: {audio_len} bytes")
                            elif msg_type == WebSocketMessageType.TRANSCRIPT:
                                sender = data.get("sender", "unknown")
                                text = data.get("text", "")
                                print(f"💬 Transcript [{sender}]: {text}")
                            elif msg_type == WebSocketMessageType.READY:
                                print("✓ Server ready")
                            else:
                                print(f"📨 Received: {data}")
                    
                    # Listen for 10 seconds, then send stop
                    await asyncio.wait_for(receive_messages(), timeout=10.0)
                except asyncio.TimeoutError:
                    print("\n⏱ Timeout reached. Sending stop message...")
                
                # Send stop message
                stop_message = {"type": WebSocketMessageType.STOP}
                await websocket.send(json.dumps(stop_message))
                print("✓ Sent stop message. Closing connection...")
            else:
                print(f"✗ Unexpected response: {ready_data}")
                
    except websockets.exceptions.InvalidURI:
        print(f"✗ Error: Invalid WebSocket URL: {server_url}")
        print("  Example: ws://YOUR_IP:3000/conversation")
    except websockets.exceptions.ConnectionClosed:
        print("✗ Connection closed by server")
    except ConnectionRefusedError:
        print(f"✗ Error: Connection refused. Is the server running at {server_url}?")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")


async def send_audio_chunk(websocket, audio_bytes: bytes):
    """
    Helper function to send an audio chunk to the server.
    
    Args:
        websocket: The websocket connection
        audio_bytes: Raw audio bytes (should match the configured encoding)
    """
    audio_message = {
        "type": WebSocketMessageType.AUDIO,
        "data": base64.b64encode(audio_bytes).decode("utf-8"),
    }
    await websocket.send(json.dumps(audio_message))


async def receive_messages(websocket):
    """
    Helper function to continuously receive messages from the server.
    
    Args:
        websocket: The websocket connection
    """
    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == WebSocketMessageType.AUDIO:
                # Received audio response - decode and handle
                audio_data = base64.b64decode(data.get("data", ""))
                print(f"Received audio chunk: {len(audio_data)} bytes")
                # In a real implementation, you would play this audio
                
            elif message_type == WebSocketMessageType.TRANSCRIPT:
                # Received transcript update
                sender = data.get("sender", "unknown")
                text = data.get("text", "")
                print(f"Transcript [{sender}]: {text}")
                
            elif message_type == WebSocketMessageType.READY:
                print("Server ready!")
                
            else:
                print(f"Received message: {data}")
                
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")


if __name__ == "__main__":
    print("Vocode WebSocket Client Example")
    print("=" * 60)
    
    # Allow custom server URL via command line argument
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        # Default to localhost, but prompt for GCP server
        print("Usage: python websocket_client_example.py <websocket_url>")
        print("Example: python websocket_client_example.py ws://YOUR_GCP_IP:3000/conversation")
        print("\nUsing default localhost (press Ctrl+C to cancel)...")
        server_url = "ws://localhost:3000/conversation"
    
    print(f"Server URL: {server_url}")
    print("=" * 60)
    
    try:
        asyncio.run(websocket_client_example(server_url))
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")

