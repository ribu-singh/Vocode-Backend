import logging
import os
import typing

from call_transcript_utils import add_transcript
from dotenv import load_dotenv
from fastapi import FastAPI

from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.events import Event, EventType
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.telephony import TwilioConfig
from vocode.streaming.models.transcript import TranscriptCompleteEvent
from vocode.streaming.telephony.config_manager.redis_config_manager import RedisConfigManager
from vocode.streaming.telephony.server.base import TelephonyServer, TwilioInboundCallConfig
from vocode.streaming.utils import events_manager

load_dotenv()

app = FastAPI(docs_url=None)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class EventsManager(events_manager.EventsManager):
    def __init__(self):
        super().__init__(subscriptions=[EventType.TRANSCRIPT_COMPLETE])

    async def handle_event(self, event: Event):
        if event.type == EventType.TRANSCRIPT_COMPLETE:
            transcript_complete_event = typing.cast(TranscriptCompleteEvent, event)
            add_transcript(
                transcript_complete_event.conversation_id,
                transcript_complete_event.transcript.to_string(),
            )


config_manager = RedisConfigManager()

BASE_URL = os.environ["TELEPHONY_SERVER_BASE_URL"]

twilio_config = TwilioConfig(
    account_sid=os.environ["TWILIO_ACCOUNT_SID"],
    auth_token=os.environ["TWILIO_AUTH_TOKEN"],
)

inbound_prompt = os.getenv(
    "INBOUND_AGENT_PROMPT",
    "The assistant helps callers and keeps responses concise and friendly.",
)
inbound_initial_message = os.getenv(
    "INBOUND_AGENT_GREETING",
    "Hi there! How can I help you today?",
)

telephony_server = TelephonyServer(
    base_url=BASE_URL,
    config_manager=config_manager,
    inbound_call_configs=[
        TwilioInboundCallConfig(
            url="/inbound_call",
            agent_config=ChatGPTAgentConfig(
                prompt_preamble=inbound_prompt,
                initial_message=BaseMessage(text=inbound_initial_message),
            ),
            twilio_config=twilio_config,
        )
    ],
    events_manager=EventsManager(),
    logger=logger,
)

app.include_router(telephony_server.get_router())
