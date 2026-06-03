"""Microphone capture for push-to-talk dictation.

Records mono float32 at a fixed sample rate into an in-memory buffer while the
push-to-talk key is held, then hands the concatenated waveform to the STT stage.
No temp files: the raw samples feed straight into the log-mel front end.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd


class Recorder:
    """Streams the default input device into a list of frames between start/stop."""

    def __init__(self, sample_rate: int, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time, status) -> None:  # noqa: ANN001
        # status carries xruns/overflows; surface them without aborting capture.
        if status:
            print(f"[audio] {status}")
        self._frames.append(indata.copy())

    def start(self) -> None:
        if self._stream is not None:
            return
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop capture and return the recorded waveform as 1-D float32."""
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._frames, axis=0).reshape(-1).astype(np.float32)
