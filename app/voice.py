"""Voice support for PidginPharma.

Provides speech-to-text (STT) and text-to-speech (TTS) capabilities
for community health workers who cannot type.

Uses platform-native speech services:
  - Windows: SAPI (built-in, no install needed)
  - Linux: espeak (may need: sudo apt install espeak)
  - macOS: NSSpeechSynthesizer (built-in)

For STT, uses the browser Web Speech API (via the web UI) or
the pyttsx3 library as a fallback for CLI.

This module is OPTIONAL — the system works fully without it.
"""

import os
import platform
import shutil
import subprocess
import sys
import threading

# Try to import pyttsx3 (cross-platform TTS)
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class VoiceEngine:
    """Handles voice input/output for PidginPharma."""

    def __init__(self):
        self._tts_engine = None
        self._available = False
        self._init_tts()

    def _init_tts(self):
        """Initialize the text-to-speech engine."""
        if HAS_PYTTSX3:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", 150)  # Slow for clarity
                self._available = True
                return
            except Exception:
                pass

        # Fallback: platform-specific commands
        system = platform.system()
        if system == "Windows":
            # PowerShell SAPI
            self._tts_cmd = [
                "powershell", "-Command",
                "Add-Type -AssemblyName System.Speech; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$synth.Speak('{}')"
            ]
            self._available = True
        elif system == "Linux":
            if shutil.which("espeak"):
                self._tts_cmd = ["espeak", "-s", "140"]
                self._available = True
        elif system == "Darwin":
            if shutil.which("say"):
                self._tts_cmd = ["say", "-r", "150"]
                self._available = True

    @property
    def is_available(self) -> bool:
        """True if TTS is available on this system."""
        return self._available

    def speak(self, text: str, block: bool = True) -> None:
        """Speak text aloud using TTS.

        Args:
            text: The text to speak.
            block: If True, wait for speech to finish before returning.
        """
        if not self._available:
            return

        # Clean text for TTS (remove emojis and special chars)
        clean = self._clean_for_tts(text)

        if self._tts_engine:
            if block:
                self._tts_engine.say(clean)
                self._tts_engine.runAndWait()
            else:
                t = threading.Thread(target=self._speak_async, args=(clean,))
                t.daemon = True
                t.start()
        elif hasattr(self, "_tts_cmd"):
            try:
                cmd = self._tts_cmd + [clean]
                subprocess.run(cmd, capture_output=True, timeout=30)
            except Exception:
                pass

    def _speak_async(self, text: str):
        """Speak in a background thread."""
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception:
            pass

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Remove emojis and special characters for TTS."""
        import re
        # Remove emojis
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
        text = re.sub(r'[\U00002702-\U000027B0]', '', text)
        text = re.sub(r'[\U0000FE00-\U0000FE0F]', '', text)
        text = re.sub(r'[\U0001FA00-\U0001FA6F]', '', text)
        text = re.sub(r'[\U0001FA70-\U0001FAFF]', '', text)
        # Remove other special chars but keep basic punctuation
        text = re.sub(r'[^\w\s.,;:!?\'"-/()àáâãäåèéêëìíîïòóôõöùúûüñç]', '', text)
        return text.strip()


# Global instance
_engine = None


def get_voice_engine() -> VoiceEngine:
    """Get the singleton voice engine."""
    global _engine
    if _engine is None:
        _engine = VoiceEngine()
    return _engine


def speak(text: str, block: bool = True) -> None:
    """Convenience function to speak text aloud."""
    get_voice_engine().speak(text, block=block)


def is_voice_available() -> bool:
    """Check if voice output is available."""
    return get_voice_engine().is_available
