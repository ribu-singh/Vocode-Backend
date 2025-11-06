"""
Vocode WebSocket Server

FastAPI server that provides a WebSocket endpoint for real-time voice conversations.
Handles audio streaming, transcription, AI agent processing, and speech synthesis.

Configuration:
- Transcriber: Deepgram (default)
- Agent: ChatGPT
- Synthesizer: ElevenLabs

Environment Variables:
- OPENAI_API_KEY: Required for ChatGPT agent
- DEEPGRAM_API_KEY: Required for speech-to-text
- ELEVENLABS_API_KEY: Required for text-to-speech
- ALLOWED_ORIGINS: CORS origins (default: "*")
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vocode.logging import configure_pretty_logging
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.client_backend.conversation import ConversationRouter
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.synthesizer.eleven_labs_websocket_synthesizer import (
    ElevenLabsWSSynthesizer,
)

load_dotenv()

app = FastAPI(docs_url=None)

# Configure CORS for WebSocket connections from web clients
# In production, restrict ALLOWED_ORIGINS to specific domains
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_pretty_logging()

# Configure conversation router with agent, transcriber, and synthesizer
conversation_router = ConversationRouter(
    agent_thunk=lambda: ChatGPTAgent(
        ChatGPTAgentConfig(
            initial_message=BaseMessage(text="Hello!"),
            prompt_preamble="Have a pleasant conversation about life",
        )
    ),
    synthesizer_thunk=lambda output_audio_config: ElevenLabsWSSynthesizer(
        ElevenLabsSynthesizerConfig.from_output_audio_config(
            output_audio_config,
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice (Rachel)
            experimental_websocket=True,  # Enable WebSocket streaming API
        )
    ),
    # transcriber_thunk uses default: DeepgramTranscriber
)

app.include_router(conversation_router.get_router())
