# recorder/test_recorder.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from voice.recorder.recorder import Recorder
from voice.asr.recognizer import SenseVoiceRecognizer


def main():

    # ---------- Recorder ----------
    recorder = Recorder(
        duration=5,
        device=1,
    )

    wav_path = recorder.record()

    print("\n========== Recorder ==========")
    print(wav_path)

    # ---------- ASR ----------
    recognizer = SenseVoiceRecognizer()

    result = recognizer.recognize(wav_path)

    print("\n========== ASR Result ==========")
    print(result)
    print("===============================")


if __name__ == "__main__":
    main()
