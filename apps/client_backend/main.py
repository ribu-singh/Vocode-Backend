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
from vocode.streaming.models.audio import SamplingRate, AudioEncoding
from vocode.streaming.synthesizer.eleven_labs_websocket_synthesizer import ElevenLabsWSSynthesizer

load_dotenv()

app = FastAPI(docs_url=None)

# Configure CORS for WebSocket connections from web clients
# Allow all origins in production - restrict this based on your needs
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_pretty_logging()

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
            sampling_rate=SamplingRate.RATE_16000,  # Use 16kHz for free tier compatibility
            audio_encoding=AudioEncoding.LINEAR16,
            experimental_websocket=True,  # Enable WebSocket streaming API
        )
    ),
)

app.include_router(conversation_router.get_router())
