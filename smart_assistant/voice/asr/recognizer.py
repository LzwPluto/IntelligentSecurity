from pathlib import Path
import re
import os
import subprocess
import tempfile

import soundfile as sf

from .sensevoice_rknn import recognize


class SenseVoiceRecognizer:
    """
    SenseVoice RKNN 语音识别封装
    """

    def __init__(
        self,
        model_dir=None,
        device=-1,
        num_threads=4,
        language="auto",
        use_itn=False,
    ):
        if model_dir is None:
            model_dir = Path(__file__).parent

        self.model_dir = str(model_dir)
        self.device = device
        self.num_threads = num_threads
        self.language = language
        self.use_itn = use_itn

    # ----------------------------------------------------------
    # 文本清洗
    # ----------------------------------------------------------

    def _clean_text(self, text: str) -> str:

        if not text:
            return ""

        # 删除 SenseVoice 标签
        text = re.sub(r"<\|.*?\|>", "", text)

        # 去除首尾空白
        text = text.strip()

        # 多空格压缩
        text = re.sub(r"\s+", " ", text)

        return text

    # ----------------------------------------------------------
    # 检查音频格式
    # ----------------------------------------------------------

    def _check_audio(self, wav_path):

        data, sample_rate = sf.read(wav_path)

        if len(data.shape) == 1:
            channels = 1
        else:
            channels = data.shape[1]

        print("\n========== Audio Check ==========")
        print(f"Sample Rate : {sample_rate}")
        print(f"Channels    : {channels}")
        print(f"Data Type   : {data.dtype}")

        if sample_rate == 16000 and channels == 1:
            print("Audio format is OK.")
            print("=================================\n")
            return True

        print("Audio format needs conversion.")
        print("=================================\n")
        return False

    # ----------------------------------------------------------
    # 自动转换音频
    # ----------------------------------------------------------

    def _convert_audio(self, wav_path):

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        temp_path = temp_file.name
        temp_file.close()

        print("Converting audio format...")

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            wav_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            temp_path,
        ]

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        print(f"Converted file : {temp_path}\n")

        return temp_path

    # ----------------------------------------------------------
    # 语音识别
    # ----------------------------------------------------------

    def recognize(self, wav_path):

        temp_file = None

        try:

            # ---------- 检查格式 ----------
            if self._check_audio(wav_path):

                audio_path = wav_path

            else:

                temp_file = self._convert_audio(wav_path)

                audio_path = temp_file

            # ---------- 调用 SenseVoice ----------
            result = recognize(
                audio_file=audio_path,
                download_path=self.model_dir,
                device=self.device,
                num_threads=self.num_threads,
                language=self.language,
                use_itn=self.use_itn,
            )

            # ---------- 文本清洗 ----------
            result = self._clean_text(result)

            return result

        finally:

            # 删除临时文件
            if temp_file is not None:

                try:
                    os.remove(temp_file)
                except Exception:
                    pass
