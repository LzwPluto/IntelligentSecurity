#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import API_KEY, MODEL, TTS_BIN, TTS_ENCODER, TTS_DECODER, TTS_CONFIG, TTS_OUTPUT_DIR, SPEAKER_DEVICE

from voice.asr.recognizer import SenseVoiceRecognizer
from voice.llm.api_client import DeepSeekClient
from voice.llm.parser import LLMParser
from voice.dispatcher.dispatcher import Dispatcher
from voice.response.manager import ResponseManager
from voice.response.tts_sender import TTSSender
from voice.conversation.manager import ConversationManager
from voice.services.sensor import SensorService
from voice.services.weather import WeatherService


class VoiceAssistant:

    def __init__(self, api_key=None, model=None, music_service=None, feishu_service=None, weather_service=None):

        if api_key is None:
            api_key = API_KEY

        if model is None:
            model = MODEL

        self.music_service = music_service
        self.feishu_service = feishu_service
        self.weather_service = weather_service
        self.recognizer = SenseVoiceRecognizer()
        self.client = DeepSeekClient(api_key=api_key, model=model)
        self.parser = LLMParser()
        self.dispatcher = Dispatcher(
            music_service=music_service,
            feishu_service=feishu_service,
        )
        self.response = ResponseManager()
        self.response.senders.append(
            TTSSender(
                TTS_BIN,
                TTS_ENCODER,
                TTS_DECODER,
                TTS_CONFIG,
                TTS_OUTPUT_DIR + "/tts_output.wav",
                play_device=SPEAKER_DEVICE,
            )
        )
        self.conversation = ConversationManager()

    def run(self, wav_file):

        wav_path = Path(wav_file)

        if not wav_path.exists():
            print(f"Audio file not found: {wav_file}")
            return

        # ---------------- ASR ----------------

        print("\n========== ASR ==========\n")

        text = self.recognizer.recognize(str(wav_path))

        print(text)

        if len(text.strip()) == 0:
            print("No speech detected.")
            return

        self.conversation.add_user(text)

        # ---------------- LLM ----------------

        print("\n========== LLM ==========\n")

        messages = self.conversation.build_messages()

        llm_response = None
        for attempt in range(2):
            try:
                llm_response = self.client.chat(messages)
                if llm_response and llm_response.strip():
                    break
            except Exception:
                pass
            print(f"[LLM] Empty response, retry {attempt + 1}/2...")

        print(llm_response)

        # ---------------- Parser ----------------

        print("\n========== Parser ==========\n")

        if not llm_response or not llm_response.strip():
            result = {
                "success": False,
                "tasks": [{"intent": "unknown", "params": {}}],
                "reply": "Sorry, I cannot process that right now.",
            }
        else:
            try:
                result = self.parser.parse(llm_response)
            except Exception:
                result = {
                    "success": False,
                    "tasks": [{"intent": "unknown", "params": {}}],
                    "reply": "Sorry, I had trouble understanding that.",
                }

        print(result)

        self.conversation.add_assistant(result["reply"])

        # Sensor / Weather: fetch real data and get LLM analysis
        sensor_analysis = None
        weather_analysis = None
        normal_tasks = []

        for task in result["tasks"]:
            intent = task.get("intent")
            if intent == "sensor_query":
                if sensor_analysis is None:
                    sensor_analysis = SensorService().execute(
                        task.get("params", {})
                    )
            elif intent == "weather_query":
                if weather_analysis is None and self.weather_service:
                    weather_analysis = self.weather_service.execute(
                        task.get("params", {})
                    )
            else:
                normal_tasks.append(task)

        analysis = sensor_analysis or weather_analysis

        if analysis:
            self.conversation.add_assistant(analysis)

        # ---------------- Dispatcher ----------------

        print("\n========== Dispatcher ==========\n")

        self.dispatcher.dispatch(normal_tasks)

        # ---------------- Response ----------------

        print("\n========== Assistant Reply ==========\n")

        self.response.send(analysis if analysis else result["reply"])


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "wav_file",
        nargs="?",
        default="asr/output.wav",
    )

    parser.add_argument(
        "--api-key",
        default=API_KEY,
        help="DeepSeek API Key",
    )

    parser.add_argument(
        "--model",
        default=MODEL,
    )

    args = parser.parse_args()

    assistant = VoiceAssistant(
        api_key=args.api_key,
        model=args.model,
    )

    assistant.run(args.wav_file)


if __name__ == "__main__":

    main()
