"""
Custom Pipecat TTS Service for Echo TTS.

This service connects to an Echo TTS server via WebSocket
and streams audio back to the Pipecat pipeline.
"""

import asyncio
import os
from typing import AsyncGenerator, Optional
from urllib.parse import urlencode

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    raise ImportError("websockets is required. Install with: pip install websockets")

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    StartFrame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from pipecat.transcriptions.language import Language

from loguru import logger


class EchoTTSService(TTSService):
    """
    Echo TTS Service for Pipecat.
    
    Connects to an Echo TTS server via WebSocket and streams
    PCM16 audio chunks (44.1kHz, int16, mono).
    """

    def __init__(
        self,
        *,
        server_url: Optional[str] = None,
        voice: str = "expresso_02_ex03-ex01_calm_005",
        cfg_scale_text: float = 2.5,
        cfg_scale_speaker: float = 5.0,
        seed: int = 0,
        sample_rate: int = 44100,
        **kwargs,
    ):
        """
        Initialize Echo TTS Service.
        
        Args:
            server_url: WebSocket URL of Echo TTS server (e.g., "ws://localhost:8000")
                       If not provided, uses ECHO_SERVER_URL env var.
            voice: Voice name from audio_prompts/ directory
            cfg_scale_text: Text classifier-free guidance scale (default: 2.5)
            cfg_scale_speaker: Speaker classifier-free guidance scale (default: 5.0)
            seed: Random seed for reproducibility (default: 0)
            sample_rate: Audio sample rate in Hz (default: 44100)
        """
        super().__init__(sample_rate=sample_rate, **kwargs)
        
        self._server_url = server_url or os.environ.get("ECHO_SERVER_URL")
        if not self._server_url:
            raise ValueError(
                "Echo TTS server URL is required. "
                "Provide server_url parameter or set ECHO_SERVER_URL environment variable."
            )
        
        # Remove trailing slash if present
        self._server_url = self._server_url.rstrip("/")
        
        self._voice = voice
        self._cfg_scale_text = cfg_scale_text
        self._cfg_scale_speaker = cfg_scale_speaker
        self._seed = seed
        self._sample_rate = sample_rate
        
        # WebSocket connection
        self._websocket: Optional[WebSocketClientProtocol] = None
        
        logger.info(f"Echo TTS Service initialized with server: {self._server_url}")

    def can_generate_metrics(self) -> bool:
        return True

    @property
    def voice(self) -> str:
        return self._voice

    @voice.setter
    def voice(self, value: str):
        self._voice = value
        logger.info(f"Echo TTS voice changed to: {value}")

    async def set_voice(self, voice: str):
        """Set the voice preset."""
        self._voice = voice
        logger.info(f"Echo TTS voice set to: {voice}")

    async def start(self, frame: StartFrame):
        """Called when the pipeline starts."""
        await super().start(frame)
        logger.info("Echo TTS Service started")

    async def stop(self, frame: EndFrame):
        """Called when the pipeline stops."""
        await super().stop(frame)
        await self._close_websocket()
        logger.info("Echo TTS Service stopped")

    async def cancel(self, frame: CancelFrame):
        """Called when generation is cancelled."""
        await super().cancel(frame)
        await self._close_websocket()
        logger.info("Echo TTS generation cancelled")

    async def _close_websocket(self):
        """Close the WebSocket connection if open."""
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._websocket = None

    def _build_websocket_url(self, text: str) -> str:
        """Build the WebSocket URL with query parameters."""
        # Use ws:// or wss:// based on server URL
        base_url = self._server_url
        if base_url.startswith("http://"):
            base_url = "ws://" + base_url[7:]
        elif base_url.startswith("https://"):
            base_url = "wss://" + base_url[8:]
        elif not base_url.startswith(("ws://", "wss://")):
            base_url = "ws://" + base_url
        
        # Build query parameters for Echo TTS
        params = {
            "text": text,
            "voice": self._voice,
            "cfg_scale_text": str(self._cfg_scale_text),
            "cfg_scale_speaker": str(self._cfg_scale_speaker),
            "seed": str(self._seed),
        }
        
        query_string = urlencode(params)
        return f"{base_url}/stream?{query_string}"

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """
        Generate speech from text using Echo TTS server.
        
        Args:
            text: Text to convert to speech.
            
        Yields:
            TTSAudioRawFrame: Audio frames containing PCM audio data.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to Echo TTS")
            return

        logger.debug(f"Echo TTS generating speech for: {text[:50]}...")

        # Build WebSocket URL
        ws_url = self._build_websocket_url(text)
        logger.debug(f"Connecting to Echo TTS WebSocket: {ws_url[:100]}...")

        try:
            # Connect to Echo TTS server
            # max_size=None removes the message size limit (Echo can send large audio chunks)
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
                max_size=None,  # Remove 1MB limit for large audio chunks
            ) as websocket:
                self._websocket = websocket
                
                # Signal TTS started
                yield TTSStartedFrame()
                
                # Receive audio chunks
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Echo TTS sends PCM16 (int16) bytes at 44.1kHz
                        yield TTSAudioRawFrame(
                            audio=message,
                            sample_rate=self._sample_rate,
                            num_channels=1,
                        )
                    elif isinstance(message, str):
                        # Log messages (Echo TTS sends JSON logs)
                        logger.debug(f"Echo TTS log: {message}")
                
                # Signal TTS stopped
                yield TTSStoppedFrame()
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Echo TTS WebSocket connection closed: {e}")
            yield TTSStoppedFrame()
        except Exception as e:
            logger.error(f"Echo TTS error: {e}")
            yield TTSStoppedFrame()
        finally:
            self._websocket = None

    async def get_available_voices(self) -> list[str]:
        """
        Fetch available voices from Echo TTS server.
        
        Returns:
            List of available voice names.
        """
        import aiohttp
        
        # Build HTTP URL for voices endpoint
        http_url = self._server_url
        if http_url.startswith("ws://"):
            http_url = "http://" + http_url[5:]
        elif http_url.startswith("wss://"):
            http_url = "https://" + http_url[6:]
        
        voices_url = f"{http_url}/v1/voices"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(voices_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Echo TTS returns {"object": "list", "data": [{"id": "voice_name", ...}]}
                        return [v.get("id", v.get("name", "")) for v in data.get("data", [])]
                    else:
                        logger.warning(f"Failed to fetch voices: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return []


