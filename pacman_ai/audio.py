"""Small procedural sound effects with no external asset dependency."""

from __future__ import annotations

from array import array
from math import pi, sin

import pygame


class SoundBank:
    """Generate short tones at startup and fail silently without an audio device."""

    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44_100, size=-16, channels=1, buffer=512)
            self.sounds = {
                "collect": self._tone(740, 0.055, 0.16),
                "power": self._tone(440, 0.18, 0.22, rise=True),
                "algorithm_selected": self._tone(570, 0.07, 0.12),
                "collision": self._tone(145, 0.28, 0.22),
                "ghost_eaten": self._tone(920, 0.13, 0.18, rise=True),
                "win": self._tone(660, 0.4, 0.18, rise=True),
                "compare": self._tone(510, 0.1, 0.12, rise=True),
            }
            self.enabled = True
        except pygame.error:
            self.enabled = False

    @staticmethod
    def _tone(
        frequency: float,
        duration: float,
        volume: float,
        rise: bool = False,
    ) -> pygame.mixer.Sound:
        sample_rate = 44_100
        count = max(1, int(sample_rate * duration))
        samples = array("h")
        for index in range(count):
            progress = index / count
            envelope = min(1.0, progress * 12) * max(0.0, 1.0 - progress)
            local_frequency = frequency * (1.0 + 0.45 * progress if rise else 1.0)
            value = sin(2 * pi * local_frequency * index / sample_rate)
            samples.append(int(32_767 * volume * envelope * value))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, event: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(event)
        if sound is not None:
            sound.play()

