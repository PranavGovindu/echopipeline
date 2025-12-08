"""
Custom Pipecat TTS Service for VibeVoice.

This service connects to a VibeVoice TTS server via WebSocket
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


class VibeVoiceTTSService(TTSService):
    """
    VibeVoice TTS Service for Pipecat.
    
    Connects to a VibeVoice server via WebSocket and streams
    PCM16 audio chunks (24kHz, int16, mono).
    """

    def __init__(
        self,
        *,
        server_url: Optional[str] = None,
        voice: str = "en-Carter_man",
        cfg_scale: float = 1.5,
        inference_steps: int = 5,
        sample_rate: int = 24000,
        **kwargs,
    ):
        """
        Initialize VibeVoice TTS Service.
        
        Args:
            server_url: WebSocket URL of VibeVoice server (e.g., "ws://localhost:8000")
                       If not provided, uses VIBEVOICE_SERVER_URL env var.
            voice: Voice preset name (e.g., "en-Carter_man", "en-Emma_woman")
            cfg_scale: Classifier-free guidance scale (default: 1.5)
            inference_steps: Number of diffusion inference steps (default: 5)
            sample_rate: Audio sample rate in Hz (default: 24000)
        """
        super().__init__(sample_rate=sample_rate, **kwargs)
        
        self._server_url = server_url or os.environ.get("VIBEVOICE_SERVER_URL")
        if not self._server_url:
            raise ValueError(
                "VibeVoice server URL is required. "
                "Provide server_url parameter or set VIBEVOICE_SERVER_URL environment variable."
            )
        
        # Remove trailing slash if present
        self._server_url = self._server_url.rstrip("/")
        
        self._voice = voice
        self._cfg_scale = cfg_scale
        self._inference_steps = inference_steps
        self._sample_rate = sample_rate
        
        # WebSocket connection
        self._websocket: Optional[WebSocketClientProtocol] = None
        
        logger.info(f"VibeVoice TTS Service initialized with server: {self._server_url}")

    def can_generate_metrics(self) -> bool:
        return True

    @property
    def voice(self) -> str:
        return self._voice

    @voice.setter
    def voice(self, value: str):
        self._voice = value
        logger.info(f"VibeVoice voice changed to: {value}")

    async def set_voice(self, voice: str):
        """Set the voice preset."""
        self._voice = voice
        logger.info(f"VibeVoice voice set to: {voice}")

    async def start(self, frame: StartFrame):
        """Called when the pipeline starts."""
        await super().start(frame)
        logger.info("VibeVoice TTS Service started")

    async def stop(self, frame: EndFrame):
        """Called when the pipeline stops."""
        await super().stop(frame)
        await self._close_websocket()
        logger.info("VibeVoice TTS Service stopped")

    async def cancel(self, frame: CancelFrame):
        """Called when generation is cancelled."""
        await super().cancel(frame)
        await self._close_websocket()
        logger.info("VibeVoice TTS generation cancelled")

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
        
        # Build query parameters
        params = {
            "text": text,
            "voice": self._voice,
            "cfg": str(self._cfg_scale),
            "steps": str(self._inference_steps),
        }
        
        query_string = urlencode(params)
        return f"{base_url}/stream?{query_string}"

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """
        Generate speech from text using VibeVoice server.
        
        Args:
            text: Text to convert to speech.
            
        Yields:
            TTSAudioRawFrame: Audio frames containing PCM audio data.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to VibeVoice TTS")
            return

        logger.debug(f"VibeVoice TTS generating speech for: {text[:50]}...")

        # Build WebSocket URL
        ws_url = self._build_websocket_url(text)
        logger.debug(f"Connecting to VibeVoice WebSocket: {ws_url[:100]}...")

        try:
            # Connect to VibeVoice server
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
            ) as websocket:
                self._websocket = websocket
                
                # Signal TTS started
                yield TTSStartedFrame()
                
                # Receive audio chunks
                async for message in websocket:
                    if isinstance(message, bytes):
                        # VibeVoice sends PCM16 (int16) bytes - pass directly
                        # No conversion needed, TTSAudioRawFrame expects PCM16
                        yield TTSAudioRawFrame(
                            audio=message,
                            sample_rate=self._sample_rate,
                            num_channels=1,
                        )
                    elif isinstance(message, str):
                        # Log messages (VibeVoice sends JSON logs)
                        logger.debug(f"VibeVoice log: {message}")
                
                # Signal TTS stopped
                yield TTSStoppedFrame()
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"VibeVoice WebSocket connection closed: {e}")
            yield TTSStoppedFrame()
        except Exception as e:
            logger.error(f"VibeVoice TTS error: {e}")
            yield TTSStoppedFrame()
        finally:
            self._websocket = None

    async def get_available_voices(self) -> list[str]:
        """
        Fetch available voices from VibeVoice server.
        
        Returns:
            List of available voice preset names.
        """
        import aiohttp
        
        # Build HTTP URL for config endpoint
        http_url = self._server_url
        if http_url.startswith("ws://"):
            http_url = "http://" + http_url[5:]
        elif http_url.startswith("wss://"):
            http_url = "https://" + http_url[6:]
        
        config_url = f"{http_url}/config"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("voices", [])
                    else:
                        logger.warning(f"Failed to fetch voices: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return []

