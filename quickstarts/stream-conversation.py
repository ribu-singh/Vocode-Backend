import asyncio
import queue
import signal

import numpy as np
import sounddevice as sd
from scipy.signal import resample
from pydantic_settings import BaseSettings, SettingsConfigDict

from vocode.helpers import create_streaming_microphone_input_and_speaker_output
from vocode.logging import configure_pretty_logging
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.transcriber import (
    DeepgramTranscriberConfig,
    PunctuationEndpointingConfig,
)
from vocode.streaming.streaming_conversation import StreamingConversation
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramTranscriber
from vocode.streaming.models.audio import AudioEncoding, SamplingRate
from vocode.streaming.synthesizer.eleven_labs_websocket_synthesizer import ElevenLabsWSSynthesizer
from vocode.streaming.output_device.rate_limit_interruptions_output_device import (
    RateLimitInterruptionsOutputDevice,
)
from vocode.streaming.utils.worker import ThreadAsyncWorker


configure_pretty_logging()


class Settings(BaseSettings):
    """
    Settings for the streaming conversation quickstart.
    These parameters can be configured with environment variables.
    """

    openai_api_key: str = "ENTER_YOUR_OPENAI_API_KEY_HERE"
    elevenlabs_api_key: str = "ENTER_YOUR_ELEVENLABS_API_KEY_HERE"
    deepgram_api_key: str = "ENTER_YOUR_DEEPGRAM_API_KEY_HERE"

    azure_speech_region: str = "eastus"

    # This means a .env file can be used to overload these settings
    # ex: "OPENAI_API_KEY=my_key" will set openai_api_key over the default above
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# ---------------------------
# Custom resampling speaker output
# ---------------------------
class _ResamplingPlaybackWorker(ThreadAsyncWorker[bytes]):
    """Worker that handles resampling and playback in a separate thread."""

    def __init__(self, *, device_info: dict, in_rate: int, out_rate: int):
        self.in_rate = in_rate
        self.out_rate = out_rate
        self.device_info = device_info
        super().__init__()
        self.stream = sd.OutputStream(
            channels=1,
            samplerate=self.out_rate,
            dtype=np.int16,
            device=int(self.device_info["index"]),
        )
        self._ended = False
        # Initialize with silence
        self.consume_nonblocking(self.out_rate * b"\x00")
        self.stream.start()

    def _run_loop(self):
        while not self._ended:
            try:
                chunk = self.input_janus_queue.sync_q.get(timeout=1)
                data = np.frombuffer(chunk, dtype=np.int16)
                if len(data) == 0:
                    continue
                # Resample from in_rate to out_rate
                if self.in_rate != self.out_rate:
                    num_samples_out = int(len(data) * self.out_rate / self.in_rate)
                    data = resample(data, num_samples_out).astype(np.int16)
                self.stream.write(data)
            except queue.Empty:
                continue

    async def terminate(self):
        self._ended = True
        await super().terminate()
        self.stream.close()


class ResamplingSpeakerOutput(RateLimitInterruptionsOutputDevice):
    """Output device that resamples audio from one rate to another before playback."""

    def __init__(
        self,
        device_info: dict,
        in_rate: int = 16000,
        out_rate: int = 44100,
        audio_encoding: AudioEncoding = AudioEncoding.LINEAR16,
    ):
        # Report the input rate as our sampling_rate since that's what we receive
        super().__init__(sampling_rate=in_rate, audio_encoding=audio_encoding)
        self.in_rate = in_rate
        self.out_rate = out_rate
        self.playback_worker = _ResamplingPlaybackWorker(
            device_info=device_info, in_rate=in_rate, out_rate=out_rate
        )

    async def play(self, chunk: bytes):
        """Sends an audio chunk to the resampling playback worker."""
        self.playback_worker.consume_nonblocking(chunk)

    def start(self) -> asyncio.Task:
        self.playback_worker.start()
        return super().start()

    async def terminate(self):
        await self.playback_worker.terminate()
        await super().terminate()

    @classmethod
    def from_device_info(
        cls,
        device_info: dict,
        in_rate: int = 16000,
        out_rate: int = 44100,
        **kwargs,
    ):
        return cls(device_info, in_rate=in_rate, out_rate=out_rate, **kwargs)


async def main():
    (
        microphone_input,
        speaker_output,
    ) = create_streaming_microphone_input_and_speaker_output(
        use_default_devices=False,
    )

    # Create resampling output device that converts 16kHz to 44.1kHz
    # This fixes the chipmunk/high-pitched sound issue
    # Query the output device info (same device that was selected)
    output_device_info = sd.query_devices(kind="output")
    resampling_output = ResamplingSpeakerOutput.from_device_info(
        device_info=output_device_info,
        in_rate=16000,  # Synthesizer output rate
        out_rate=44100,  # Your speaker output rate
    )

    conversation = StreamingConversation(
        output_device=resampling_output,
        transcriber=DeepgramTranscriber(
            DeepgramTranscriberConfig.from_input_device(
                microphone_input,
                endpointing_config=PunctuationEndpointingConfig(),
                api_key=settings.deepgram_api_key,
            ),
        ),
        agent=ChatGPTAgent(
            ChatGPTAgentConfig(
                openai_api_key=settings.openai_api_key,
                initial_message=None,  # Set to None instead of empty string to immediately enable voice input
                prompt_preamble="""The AI is having a pleasant conversation about life""",
            )
        ),
        synthesizer=ElevenLabsWSSynthesizer(
            ElevenLabsSynthesizerConfig(
                sampling_rate=SamplingRate.RATE_16000,  # Use 16kHz for free tier compatibility
                audio_encoding=AudioEncoding.LINEAR16,
                api_key=settings.elevenlabs_api_key,
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice (Rachel)
                experimental_websocket=True,  # Enable WebSocket streaming API
            )
        ),
    )
    await conversation.start()
    print("Conversation started, press Ctrl+C to end")
    signal.signal(signal.SIGINT, lambda _0, _1: asyncio.create_task(conversation.terminate()))
    while conversation.is_active():
        chunk = await microphone_input.get_audio()
        conversation.receive_audio(chunk)


if __name__ == "__main__":
    asyncio.run(main())
