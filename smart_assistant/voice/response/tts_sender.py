import os
import subprocess
from pathlib import Path


class TTSSender:

    def __init__(self, tts_bin, encoder_path, decoder_path, config_path,
                 output_file=None, play_device=None, play_cmd="aplay"):

        self.tts_bin = tts_bin
        self.encoder = encoder_path
        self.decoder = decoder_path
        self.config = config_path
        self.output_file = output_file or "/tmp/tts_output.wav"
        self.play_device = play_device
        self.play_cmd = play_cmd

    def send(self, text):

        if not text or not text.strip():
            return

        if not os.path.exists(self.tts_bin):
            print(f"[TTS] paroli-cli not found: {self.tts_bin}")
            return

        try:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)

            proc = subprocess.run(
                [
                    self.tts_bin,
                    "--encoder", self.encoder,
                    "--decoder", self.decoder,
                    "-c", self.config,
                    "-f", self.output_file,
                    "--quiet",
                ],
                input=text.strip() + "\n",
                capture_output=True,
                text=True,
                timeout=30,
            )

            if proc.returncode != 0:
                print(f"[TTS] paroli-cli error: {proc.stderr}")
                return

            if os.path.exists(self.output_file):
                play_args = [self.play_cmd]
                if self.play_device:
                    play_args += ["-D", self.play_device]
                play_args.append(self.output_file)
                subprocess.run(
                    play_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                print("[TTS] Output file not generated")

        except subprocess.TimeoutExpired:
            print("[TTS] Timed out")
        except Exception as e:
            print(f"[TTS] Error: {e}")
