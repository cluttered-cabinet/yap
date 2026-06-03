"""Speech-to-text via parakeet-mlx, in-memory (no temp files).

Mirrors what ``BaseParakeet.transcribe`` does after loading a file: convert the
waveform to a log-mel spectrogram with the model's own preprocessor config, then
run ``generate``. We skip the disk round-trip because the audio is already in
RAM from the recorder.
"""

from __future__ import annotations

import mlx.core as mx
import numpy as np
from parakeet_mlx import from_pretrained
from parakeet_mlx.audio import get_logmel

DEFAULT_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"


class Transcriber:
    def __init__(self, model_id: str = DEFAULT_MODEL) -> None:
        self.model = from_pretrained(model_id)

    @property
    def sample_rate(self) -> int:
        return self.model.preprocessor_config.sample_rate

    def transcribe(self, samples: np.ndarray) -> str:
        if samples.size == 0:
            return ""
        audio = mx.array(samples.astype(np.float32))
        mel = get_logmel(audio, self.model.preprocessor_config)
        results = self.model.generate(mel)
        if not results:
            return ""
        return results[0].text.strip()
