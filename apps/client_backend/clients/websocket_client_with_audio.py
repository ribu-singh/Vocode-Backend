"""
Working WebSocket client for Vocode's websocket conversation endpoint.

This client actually captures microphone audio and plays received audio.

Requirements:
    pip install websockets sounddevice numpy scipy

Usage:
    python websocket_client_with_audio.py ws://YOUR_GCP_IP:3000/conversation (current GCP IP: 34.13.49.144)
"""

import asyncio
import base64
import json
import sys
import websockets
import sounddevice as sd
import numpy as np
import queue as thread_queue
from scipy.signal import resample
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


# Audio configuration
# Server sends audio at 16kHz (ElevenLabs free tier compatibility)
SERVER_SAMPLING_RATE = 16000
# Your speakers typically run at 44.1kHz
OUTPUT_SAMPLING_RATE = 44100
CHUNK_SIZE = 4096  # bytes
CHUNK_DURATION = CHUNK_SIZE / (SERVER_SAMPLING_RATE * 2)  # seconds (16-bit = 2 bytes per sample)

# Buffer configuration for smooth playback
INPUT_QUEUE_SIZE = 50  # Increased for better buffering
OUTPUT_QUEUE_SIZE = 50  # Increased for better buffering
BLOCKSIZE_MULTIPLIER = 2  # Larger blocksize for smoother audio


async def websocket_client_with_audio(server_url: str):
    """
    Connect to the Vocode websocket server with real microphone input and speaker output.
    
    Args:
        server_url: The WebSocket URL of the server (e.g., ws://YOUR_IP:3000/conversation)
    """
    print(f"Connecting to {server_url}...")
    
    # Audio queues (thread-safe for sounddevice callbacks)
    # Increased queue sizes to prevent choppy audio
    audio_input_queue = thread_queue.Queue(maxsize=INPUT_QUEUE_SIZE)
    audio_output_queue = thread_queue.Queue(maxsize=OUTPUT_QUEUE_SIZE)
    
    # Flag to control audio streaming
    streaming_active = asyncio.Event()
    
    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected! Sending initial configuration...")
            
            # Send the initial AudioConfigStartMessage
            start_message = {
                "type": WebSocketMessageType.AUDIO_CONFIG_START,
                "input_audio_config": {
                    "sampling_rate": SERVER_SAMPLING_RATE,
                    "audio_encoding": "linear16",
                    "chunk_size": CHUNK_SIZE,
                },
                "output_audio_config": {
                    "sampling_rate": SERVER_SAMPLING_RATE,  # Server sends at 16kHz
                    "audio_encoding": "linear16",
                },
                "conversation_id": None,
                "subscribe_transcript": True,
            }
            
            await websocket.send(json.dumps(start_message))
            print("✓ Configuration sent. Waiting for ready message...")
            
            # Wait for ready message
            ready_response = await websocket.recv()
            ready_data = json.loads(ready_response)
            print(f"✓ Received: {ready_data}")
            
            if ready_data.get("type") != WebSocketMessageType.READY:
                print(f"✗ Unexpected response: {ready_data}")
                return
            
            print("\n✓ Server is ready! Starting audio streaming...")
            print("Speak into your microphone. Press Ctrl+C to stop.\n")
            
            streaming_active.set()
            
            # Start audio input callback
            def audio_callback(indata, frames, time, status):
                """Callback for microphone input (runs in separate thread)."""
                if status:
                    print(f"Audio input status: {status}")
                if streaming_active.is_set():
                    # Convert numpy array to bytes
                    audio_bytes = indata.tobytes()
                    # Put in queue (non-blocking, drop oldest if full to prevent lag)
                    try:
                        audio_input_queue.put_nowait(audio_bytes)
                    except thread_queue.Full:
                        # Drop oldest item to prevent lag buildup
                        try:
                            audio_input_queue.get_nowait()
                            audio_input_queue.put_nowait(audio_bytes)
                        except thread_queue.Empty:
                            pass
            
            # Start audio output callback with resampling
            def output_callback(outdata, frames, time, status):
                """Callback for speaker output with resampling (runs in separate thread)."""
                if status:
                    print(f"Audio output status: {status}")
                
                # Try to get multiple chunks to fill the output buffer smoothly
                audio_chunks = []
                total_samples = 0
                
                # Collect enough audio data to fill the output buffer
                while total_samples < frames and not audio_output_queue.empty():
                    try:
                        audio_bytes = audio_output_queue.get_nowait()
                        audio_array_16k = np.frombuffer(audio_bytes, dtype=np.int16)
                        audio_chunks.append(audio_array_16k)
                        total_samples += len(audio_array_16k)
                    except thread_queue.Empty:
                        break
                
                if audio_chunks:
                    # Concatenate all chunks
                    combined_audio_16k = np.concatenate(audio_chunks)
                    
                    # Resample from 16kHz to 44.1kHz to avoid chipmunk sound
                    if SERVER_SAMPLING_RATE != OUTPUT_SAMPLING_RATE:
                        num_samples_out = int(len(combined_audio_16k) * OUTPUT_SAMPLING_RATE / SERVER_SAMPLING_RATE)
                        audio_array = resample(combined_audio_16k, num_samples_out).astype(np.int16)
                    else:
                        audio_array = combined_audio_16k
                    
                    # Fill output buffer
                    samples_to_write = min(len(audio_array), frames)
                    outdata[:samples_to_write] = audio_array[:samples_to_write].reshape(-1, 1)
                    
                    # Fill remaining with silence if needed
                    if samples_to_write < frames:
                        outdata[samples_to_write:] = 0
                else:
                    # No audio available - fill with silence
                    outdata[:] = 0
            
            # Start audio streams
            # Input: Capture at 16kHz (matches server)
            # Use larger blocksize for smoother capture
            input_blocksize = int(SERVER_SAMPLING_RATE * CHUNK_DURATION * BLOCKSIZE_MULTIPLIER)
            input_stream = sd.InputStream(
                samplerate=SERVER_SAMPLING_RATE,
                channels=1,
                dtype=np.int16,
                blocksize=input_blocksize,
                callback=audio_callback,
                latency='low'  # Low latency for real-time conversation
            )
            
            # Output: Play at 44.1kHz (typical speaker rate) with resampling
            # Use larger blocksize for smoother playback
            output_blocksize = int(OUTPUT_SAMPLING_RATE * CHUNK_DURATION * BLOCKSIZE_MULTIPLIER)
            output_stream = sd.OutputStream(
                samplerate=OUTPUT_SAMPLING_RATE,
                channels=1,
                dtype=np.int16,
                blocksize=output_blocksize,
                callback=output_callback,
                latency='low'  # Low latency for real-time conversation
            )
            
            input_stream.start()
            output_stream.start()
            print("✓ Microphone and speaker started")
            
            async def send_audio():
                """Send audio chunks to server."""
                while streaming_active.is_set():
                    try:
                        # Get audio chunk from queue (with timeout)
                        audio_bytes = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: audio_input_queue.get(timeout=0.05)
                        )
                        
                        # Send to server
                        audio_message = {
                            "type": WebSocketMessageType.AUDIO,
                            "data": base64.b64encode(audio_bytes).decode("utf-8"),
                        }
                        await websocket.send(json.dumps(audio_message))
                    except Exception:
                        # Timeout or other error - continue without blocking
                        await asyncio.sleep(0.001)
                        continue
            
            async def receive_messages():
                """Receive messages from server."""
                try:
                    while streaming_active.is_set():
                        message = await websocket.recv()
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == WebSocketMessageType.AUDIO:
                            # Decode audio and put in output queue
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            try:
                                audio_output_queue.put_nowait(audio_bytes)
                            except thread_queue.Full:
                                # Drop oldest audio to prevent lag buildup
                                try:
                                    audio_output_queue.get_nowait()
                                    audio_output_queue.put_nowait(audio_bytes)
                                except thread_queue.Empty:
                                    pass
                                
                        elif msg_type == WebSocketMessageType.TRANSCRIPT:
                            sender = data.get("sender", "unknown")
                            text = data.get("text", "")
                            print(f"💬 [{sender}]: {text}")
                            
                        elif msg_type == WebSocketMessageType.READY:
                            print("✓ Server ready")
                            
                except websockets.exceptions.ConnectionClosed:
                    print("\n✗ Connection closed by server")
                except Exception as e:
                    print(f"\n✗ Error receiving: {e}")
            
            # Run send and receive concurrently
            try:
                await asyncio.gather(
                    send_audio(),
                    receive_messages()
                )
            except KeyboardInterrupt:
                print("\n\n⏹ Stopping...")
            finally:
                streaming_active.clear()
                input_stream.stop()
                output_stream.stop()
                input_stream.close()
                output_stream.close()
                
                # Send stop message
                stop_message = {"type": WebSocketMessageType.STOP}
                await websocket.send(json.dumps(stop_message))
                print("✓ Sent stop message. Connection closed.")
                
    except websockets.exceptions.InvalidURI:
        print(f"✗ Error: Invalid WebSocket URL: {server_url}")
        print("  Example: ws://YOUR_IP:3000/conversation")
    except websockets.exceptions.ConnectionClosed:
        print("✗ Connection closed by server")
    except ConnectionRefusedError:
        print(f"✗ Error: Connection refused. Is the server running at {server_url}?")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Vocode WebSocket Client with Audio")
    print("=" * 60)
    
    # Check if sounddevice is available
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"✓ Found {len(devices)} audio devices")
        print(f"  Default input: {sd.query_devices(kind='input')['name']}")
        print(f"  Default output: {sd.query_devices(kind='output')['name']}")
    except Exception as e:
        print(f"✗ Error: Could not access audio devices: {e}")
        print("  Make sure sounddevice and PortAudio are installed")
        sys.exit(1)
    
    # Allow custom server URL via command line argument
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        print("Usage: python websocket_client_with_audio.py <websocket_url>")
        print("Example: python websocket_client_with_audio.py ws://YOUR_GCP_IP:3000/conversation")
        sys.exit(1)
    
    print(f"Server URL: {server_url}")
    print("=" * 60)
    
    try:
        asyncio.run(websocket_client_with_audio(server_url))
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

