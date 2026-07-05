"""
全局配置文件

通过环境变量覆盖默认值，避免密钥硬编码。
环境变量不存在时使用占位值（需用户自行填写）。
"""
import os

# ==========================================
# DeepSeek
# ==========================================

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")

MODEL = "deepseek-chat"


# ==========================================
# Audio
# ==========================================

# PortAudio 设备索引：1 = rockchip-nau8822（板载麦克风+耳机）
# 详参 python3 -c "import sounddevice; print(sounddevice.query_devices())"
MIC_DEVICE = 1

# aplay 硬件设备：hw:1,0 = rockchip-nau8822（耳机输出）
# 详参 aplay -l
SPEAKER_DEVICE = "plughw:1,0"

SAMPLE_RATE = 16000

CAPTURE_SAMPLE_RATE = 44100

CHANNELS = 1


# ==========================================
# Recorder
# ==========================================

RECORD_DURATION = 5


# ==========================================
# Wakeup
# ==========================================

WAKEUP_BLOCK_SIZE = 8192


# ==========================================
# ASR
# ==========================================

ASR_LANGUAGE = "auto"

ASR_USE_ITN = False


# ==========================================
# LED
# ==========================================

LED_GPIO_CHIP = "gpiochip3"

LED_GPIO_PIN = 13


# ==========================================
# TTS (Piper / paroli-cli)
# ==========================================

TTS_BIN = os.environ.get(
    "TTS_BIN",
    "/home/elf/project/smart_assistant/TTS/paroli-on-orangepi/build/paroli-cli",
)

TTS_ENCODER = os.environ.get(
    "TTS_ENCODER",
    "/home/elf/project/smart_assistant/TTS/encoder-en.onnx",
)

TTS_DECODER = os.environ.get(
    "TTS_DECODER",
    "/home/elf/project/smart_assistant/TTS/decoder-en-3588.rknn",
)

TTS_CONFIG = os.environ.get(
    "TTS_CONFIG",
    "/home/elf/project/smart_assistant/TTS/config-en.json",
)

TTS_OUTPUT_DIR = "/tmp/tts_output"


# ==========================================
# Weather (Seniverse API)
# ==========================================

WEATHER_API_KEY = os.environ.get("SENIVERSE_API_KEY", "YOUR_SENIVERSE_API_KEY")

WEATHER_DEFAULT_CITY = "beijing"


# ==========================================
# Music
# ==========================================

MUSIC_DIR = "/home/elf/project/smart_assistant/Music"


# ==========================================
# Feishu
# ==========================================

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "YOUR_FEISHU_APP_ID")

FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "YOUR_FEISHU_APP_SECRET")

FEISHU_CHAT_ID = os.environ.get("FEISHU_CHAT_ID", "YOUR_FEISHU_CHAT_ID")


# ==========================================
# AEC (Echo Cancellation)
# ==========================================

AEC_ENABLED = True

AEC_FILTER_LENGTH = 512

AEC_MU = 0.005
