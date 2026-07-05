import os
import threading
import time

import numpy as np


class EchoCanceler:

    def __init__(
        self,
        sample_rate=44100,
        filter_length=512,
        mu=0.005,
        fifo_path="/tmp/mpv_ref_fifo",
    ):
        self.sample_rate = sample_rate
        self.filter_length = filter_length
        self.mu = mu

        self.w = np.zeros(filter_length, dtype=np.float32)
        self.ref_buf = np.zeros(filter_length, dtype=np.float32)

        self.fifo_path = fifo_path
        self._fifo_fd = None
        self._ref_data = b""
        self._ref_lock = threading.Lock()
        self._reader_thread = None
        self._running = False

        self._silence_counter = 0
        self._silence_threshold = 5

    def start(self):
        self._create_fifo()
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True
        )
        self._reader_thread.start()

    def stop(self):
        self._running = False
        if self._fifo_fd is not None:
            try:
                os.close(self._fifo_fd)
            except OSError:
                pass
            self._fifo_fd = None
        try:
            os.unlink(self.fifo_path)
        except OSError:
            pass

    def _create_fifo(self):
        try:
            os.unlink(self.fifo_path)
        except OSError:
            pass
        os.mkfifo(self.fifo_path)
        self._fifo_fd = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)

    def _reader_loop(self):
        while self._running:
            try:
                data = os.read(self._fifo_fd, 4096)
                if not data:
                    time.sleep(0.01)
                    continue
                with self._ref_lock:
                    self._ref_data += data
            except BlockingIOError:
                time.sleep(0.01)
            except OSError:
                time.sleep(0.05)

    def process(self, mic_samples):
        n = len(mic_samples)
        ref = self._read_ref(n)

        rms = np.sqrt(np.mean(ref ** 2))
        if rms < 1e-6:
            self._silence_counter += 1
            if self._silence_counter > self._silence_threshold:
                return mic_samples
        else:
            self._silence_counter = 0

        return self._lms_process(mic_samples, ref)

    def _lms_process(self, mic, ref):
        n = len(mic)
        L = self.filter_length
        mu = self.mu

        ref_history = np.concatenate([self.ref_buf, ref])
        self.ref_buf[:] = ref_history[-L:]

        w = self.w.copy()

        echo = np.convolve(ref_history, w[::-1], mode="valid")
        if len(echo) > n:
            echo = echo[:n]
        elif len(echo) < n:
            echo = np.pad(echo, (0, n - len(echo)))

        error = mic - echo

        block = 64
        for start in range(0, n, block):
            end = min(start + block, n)
            for i in range(start, end):
                r = ref_history[i : i + L][::-1]
                w += 2.0 * mu * error[i] * r

        self.w[:] = w
        return error

    def _read_ref(self, n_samples):
        with self._ref_lock:
            data = self._ref_data
            needed = n_samples * 2
            if len(data) >= needed:
                self._ref_data = data[needed:]
                samples = (
                    np.frombuffer(data[:needed], dtype=np.int16)
                    .astype(np.float32)
                    / 32768.0
                )
                return samples
            else:
                self._ref_data = b""
                if len(data) >= 2:
                    usable = len(data) - len(data) % 2
                    samples = (
                        np.frombuffer(data[:usable], dtype=np.int16)
                        .astype(np.float32)
                        / 32768.0
                    )
                    result = np.zeros(n_samples, dtype=np.float32)
                    result[: len(samples)] = samples
                    return result
                return np.zeros(n_samples, dtype=np.float32)
