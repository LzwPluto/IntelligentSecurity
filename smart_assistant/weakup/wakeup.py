# weakup/wakeup.py

from pathlib import Path
import threading
import sys

import numpy as np
import sherpa_onnx
import sounddevice as sd


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


class Wakeup:

    def __init__(
        self,
        model_dir=None,
        device=1,
        sample_rate=16000,
        capture_sample_rate=None,
        block_size=4096,
        num_threads=1,
        provider="cpu",
        echo_canceler=None,
    ):

        if model_dir is None:
            model_dir = Path(__file__).parent

        self.model_dir = Path(model_dir)

        self.device = device
        self.sample_rate = sample_rate
        self.capture_sample_rate = (
            capture_sample_rate if capture_sample_rate else sample_rate
        )
        self.block_size = block_size
        self.echo_canceler = echo_canceler
        self._needs_resample = self.capture_sample_rate != self.sample_rate

        if self._needs_resample:
            self._capture_block_size = int(
                block_size
                * self.capture_sample_rate
                / self.sample_rate
            )
        else:
            self._capture_block_size = block_size

        print("\n========== Wakeup ==========")
        print(f"Capture rate : {self.capture_sample_rate} Hz")
        if self._needs_resample:
            print(f"Model rate   : {self.sample_rate} Hz (resampling)")
        print("Loading keyword spotter...")

        self.spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(self.model_dir / "tokens.txt"),
            encoder=str(
                self.model_dir /
                "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
            ),
            decoder=str(
                self.model_dir /
                "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
            ),
            joiner=str(
                self.model_dir /
                "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
            ),
            keywords_file=str(self.model_dir / "keywords.txt"),
            num_threads=num_threads,
            provider=provider,
        )

        self.stream = self.spotter.create_stream()

        self._event = threading.Event()
        self.keyword = None

        print("Wakeup ready.")
        print("============================\n")

    def _audio_callback(self, indata, frames, time, status):

        if status:
            print(status, file=sys.stderr)

        samples = indata.reshape(-1)

        if self.echo_canceler:
            samples = self.echo_canceler.process(samples)

        if self._needs_resample:
            samples = _resample(
                samples, self.capture_sample_rate, self.sample_rate
            )

        self.stream.accept_waveform(
            self.sample_rate,
            samples,
        )

        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)

        result = self.spotter.get_result(self.stream)

        keyword = (
            result
            if isinstance(result, str)
            else getattr(result, "keyword", "")
        )

        if keyword:

            self.keyword = keyword

            self.spotter.reset_stream(self.stream)

            self._event.set()

    def wait(self):

        self.keyword = None
        self._event.clear()

        print("Waiting wakeup...")

        with sd.InputStream(
            device=self.device,
            samplerate=self.capture_sample_rate,
            blocksize=self._capture_block_size,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
        ):

            self._event.wait()

        print(f"Wakeup detected: {self.keyword}")

        return self.keyword
