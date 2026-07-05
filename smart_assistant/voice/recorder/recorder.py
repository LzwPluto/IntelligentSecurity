# recorder/recorder.py

from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


def _resample(samples, orig_rate, target_rate):
    if orig_rate == target_rate:
        return samples

    if samples.ndim == 2:
        resampled = []
        for ch in range(samples.shape[1]):
            col = samples[:, ch]
            n = len(col)
            target_len = int(n / orig_rate * target_rate)
            resampled.append(
                np.interp(
                    np.linspace(0, n - 1, target_len),
                    np.arange(n),
                    col,
                )
            )
        return np.column_stack(resampled).astype(np.float32)

    n = len(samples)
    target_len = int(n / orig_rate * target_rate)
    return np.interp(
        np.linspace(0, n - 1, target_len),
        np.arange(n),
        samples,
    ).astype(np.float32)


class Recorder:

    def __init__(
        self,
        sample_rate=16000,
        capture_sample_rate=None,
        channels=1,
        duration=5,
        device=1,
    ):

        self.sample_rate = sample_rate
        self.capture_sample_rate = (
            capture_sample_rate if capture_sample_rate else sample_rate
        )
        self.channels = channels
        self.duration = duration
        self.device = device
        self._needs_resample = self.capture_sample_rate != self.sample_rate

        self.record_dir = (
            Path(__file__).parent.parent / "recordings"
        )
        self.record_dir.mkdir(exist_ok=True)

    def record(self):

        wav_path = self.record_dir / "record.wav"

        print("\n========== Recorder ==========")
        print(f"Input Device : {self.device}")
        print(f"Capture Rate : {self.capture_sample_rate} Hz")
        if self._needs_resample:
            print(f"Output Rate  : {self.sample_rate} Hz (resampling)")
        print(f"Channels     : {self.channels}")
        print(f"Duration     : {self.duration} s")
        print("Recording...")
        print("==============================")

        audio = sd.rec(
            int(self.duration * self.capture_sample_rate),
            samplerate=self.capture_sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
        )

        sd.wait()

        if self._needs_resample:
            audio = _resample(audio, self.capture_sample_rate, self.sample_rate)

        sf.write(
            str(wav_path),
            audio,
            self.sample_rate,
            subtype="PCM_16",
        )

        print("Record finished.")
        print(f"Saved to: {wav_path}")
        print("==============================\n")

        return str(wav_path)
