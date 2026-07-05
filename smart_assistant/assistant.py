#!/usr/bin/env python3

"""
assistant.py

整个语音助手唯一入口。

流程：

Wakeup
    ↓
Recorder
    ↓
VoiceAssistant
    ↓
等待下一次唤醒
"""

from weakup.wakeup import Wakeup
from voice.recorder.recorder import Recorder
from voice.main import VoiceAssistant
from voice.services.music import MusicService
from voice.services.feishu import FeishuService
from voice.services.weather import WeatherService
from voice.services.sensor_data import start as start_sensor_data, set_alert_callback
from voice.aec.echo_canceler import EchoCanceler
from voice.llm.api_client import DeepSeekClient
from voice.response.tts_sender import TTSSender
from config import (
    RECORD_DURATION, MIC_DEVICE, SAMPLE_RATE, CAPTURE_SAMPLE_RATE,
    WAKEUP_BLOCK_SIZE, AEC_ENABLED, AEC_FILTER_LENGTH, AEC_MU,
    MUSIC_DIR, SPEAKER_DEVICE,
    FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_CHAT_ID,
    WEATHER_API_KEY, WEATHER_DEFAULT_CITY,
    API_KEY, MODEL, TTS_BIN, TTS_ENCODER, TTS_DECODER, TTS_CONFIG, TTS_OUTPUT_DIR,
)


def main():

    print("\n===================================")
    print("      Smart Voice Assistant")
    print("===================================\n")

    # ---------------- 初始化 ----------------

    aec = None
    if AEC_ENABLED:
        aec = EchoCanceler(
            sample_rate=CAPTURE_SAMPLE_RATE,
            filter_length=AEC_FILTER_LENGTH,
            mu=AEC_MU,
        )
        aec.start()

    wakeup = Wakeup(
        device=MIC_DEVICE,
        sample_rate=SAMPLE_RATE,
        capture_sample_rate=CAPTURE_SAMPLE_RATE,
        block_size=WAKEUP_BLOCK_SIZE,
        echo_canceler=aec,
    )

    recorder = Recorder(
        duration=RECORD_DURATION,
        device=MIC_DEVICE,
        sample_rate=SAMPLE_RATE,
        capture_sample_rate=CAPTURE_SAMPLE_RATE,
    )

    music_service = MusicService(
        music_dir=MUSIC_DIR,
        audio_device=SPEAKER_DEVICE,
    )

    feishu_service = FeishuService(
        app_id=FEISHU_APP_ID,
        app_secret=FEISHU_APP_SECRET,
        chat_id=FEISHU_CHAT_ID,
    )

    def on_sensor_alert(title, content, level):
        feishu_service.send_alert(title, content, level)

    set_alert_callback(on_sensor_alert)

    weather_service = WeatherService(
        api_key=WEATHER_API_KEY,
        default_city=WEATHER_DEFAULT_CITY,
    )

    llm_client = DeepSeekClient(api_key=API_KEY, model=MODEL)

    weather_service.set_llm(
        lambda msgs: llm_client.chat(msgs, json_mode=False)
    )

    def speak_weather(text):
        TTSSender(
            TTS_BIN, TTS_ENCODER, TTS_DECODER, TTS_CONFIG,
            TTS_OUTPUT_DIR + "/tts_output.wav",
            play_device=SPEAKER_DEVICE,
        ).send(text)

    def feishu_weather(title, content, level):
        feishu_service.send_alert(title, content, level)

    weather_service.start_scheduler(
        tts_callback=speak_weather,
        feishu_alert=feishu_weather,
    )

    assistant = VoiceAssistant(
        music_service=music_service,
        feishu_service=feishu_service,
        weather_service=weather_service,
    )

    start_sensor_data()

    print("System Ready.\n")

    # ---------------- 主循环 ----------------

    while True:

        try:

            print("\n==============================")
            print("Waiting for wakeup...")
            print("==============================")

            keyword = wakeup.wait()

            print(f"Wakeup Word : {keyword}")

            music_service.on_wakeup()

            print("\nStart Recording...")

            wav_path = recorder.record()

            print(f"Audio : {wav_path}")

            print("\nProcessing...")

            assistant.run(wav_path)

            music_service.on_interaction_done()

            print("\nConversation Finished.")

        except KeyboardInterrupt:

            print("\nExit.")

            weather_service.stop_scheduler()
            if aec:
                aec.stop()
            music_service._stop()

            break

        except Exception as e:

            print(f"\nAssistant Error : {e}")

            music_service.on_interaction_done()

            continue


if __name__ == "__main__":

    main()
