"""
SpartaFlash - Industrial Sound & Audio Alert Service.
Developer: Rohidfkra777 (https://github.com/rohidfkra777)

Provides crisp, non-blocking hardware-synthesized acoustic cues for operator feedback:
- Success Chime (Pass)
- Error Alert (Fail)
- Warning Double-Beep (Attention)
"""

import sys
import time
import threading
from typing import Optional

try:
    import winsound
except ImportError:
    winsound = None

from src.config.settings import settings_manager
from src.utils.logger import get_logger
logger = get_logger()


class SoundService:
    """
    Non-blocking sound generator for manufacturing station audio alerts.
    Dispatches beeps asynchronously to ensure zero UI frame stutters.
    """

    def is_enabled(self) -> bool:
        """Check if audio alerts are enabled in settings."""
        return bool(settings_manager.get("play_sound_on_completion", True))

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audio alerts."""
        settings_manager.set("play_sound_on_completion", bool(enabled))

    def _play_async(self, target_fn, *args) -> None:
        """Run an audio sequence in a daemon thread."""
        thread = threading.Thread(target=target_fn, args=args, daemon=True)
        thread.start()

    def play_success(self, force: bool = False) -> None:
        """
        Play energetic ascending 3-tone chime for PASS / Success.
        Frequencies: G5 (784Hz) -> B5 (988Hz) -> E6 (1318Hz).
        """
        if not force and not self.is_enabled():
            return

        def _worker():
            try:
                if winsound:
                    winsound.Beep(784, 100)
                    time.sleep(0.02)
                    winsound.Beep(988, 100)
                    time.sleep(0.02)
                    winsound.Beep(1318, 180)
                else:
                    self._system_fallback(winsound.MB_ICONASTERISK if winsound else None)
            except Exception as e:
                logger.debug(f"[SoundService] Success beep fallback: {e}")
                self._system_fallback()

        self._play_async(_worker)

    def play_failure(self, force: bool = False) -> None:
        """
        Play descending alert buzz for FAIL / Error.
        Frequencies: A4 (440Hz) -> D4 (293Hz).
        """
        if not force and not self.is_enabled():
            return

        def _worker():
            try:
                if winsound:
                    winsound.Beep(440, 140)
                    time.sleep(0.04)
                    winsound.Beep(293, 240)
                else:
                    self._system_fallback(winsound.MB_ICONHAND if winsound else None)
            except Exception as e:
                logger.debug(f"[SoundService] Failure beep fallback: {e}")
                self._system_fallback()

        self._play_async(_worker)

    def play_warning(self, force: bool = False) -> None:
        """
        Play double-beep for CANCEL / Warning.
        Frequency: 700Hz double tap.
        """
        if not force and not self.is_enabled():
            return

        def _worker():
            try:
                if winsound:
                    winsound.Beep(700, 90)
                    time.sleep(0.06)
                    winsound.Beep(700, 90)
                else:
                    self._system_fallback(winsound.MB_ICONEXCLAMATION if winsound else None)
            except Exception as e:
                logger.debug(f"[SoundService] Warning beep fallback: {e}")
                self._system_fallback()

        self._play_async(_worker)

    def _system_fallback(self, msg_type=None) -> None:
        """Fallback to Windows system message sound or Qt app beep."""
        try:
            if winsound and msg_type is not None:
                winsound.MessageBeep(msg_type)
            elif winsound:
                winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass


sound_service = SoundService()
