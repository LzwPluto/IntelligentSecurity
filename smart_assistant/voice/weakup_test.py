import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

# ========== 配置区域 ==========
MODEL_DIR = Path(__file__).parent

TOKEN_FILE = str(MODEL_DIR / "tokens.txt")
ENCODER_FILE = str(MODEL_DIR / "encoder-epoch-13-avg-2-chunk-16-left-64.onnx")
DECODER_FILE = str(MODEL_DIR / "decoder-epoch-13-avg-2-chunk-16-left-64.onnx")
JOINER_FILE = str(MODEL_DIR / "joiner-epoch-13-avg-2-chunk-16-left-64.onnx")
KEYWORDS_FILE = str(MODEL_DIR / "keywords.txt")
TEST_WAV_PATH = str(MODEL_DIR / "test_keyword.wav")
SAMPLE_RATE = 16000
# ==============================

def read_wav(file_path):
    with wave.open(file_path, 'rb') as wf:
        assert wf.getframerate() == SAMPLE_RATE, "采样率必须为 16000"
        assert wf.getnchannels() == 1, "必须为单声道"
        assert wf.getsampwidth() == 2, "必须为16bit PCM"
        
        raw_data = wf.readframes(wf.getnframes())
        samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    return samples

def main():
    print("⏳ 正在加载唤醒模型...")
    try:
        spotter = sherpa_onnx.KeywordSpotter(
            tokens=TOKEN_FILE,
            encoder=ENCODER_FILE,
            decoder=DECODER_FILE,
            joiner=JOINER_FILE,
            keywords_file=KEYWORDS_FILE,
            num_threads=2,
            max_active_paths=4,
            keywords_threshold=0.2,  # 测试用低阈值，优先保证命中
            num_trailing_blanks=1,
        )
    except Exception as e:
        print(f"❌ 模型加载失败：{e}")
        return
    print("✅ 模型加载成功")

    print(f"\n📂 读取测试音频：{TEST_WAV_PATH}")
    try:
        samples = read_wav(TEST_WAV_PATH)
    except Exception as e:
        print(f"❌ 音频读取失败：{e}")
        return
    print(f"✅ 音频时长：{len(samples) / SAMPLE_RATE:.2f} 秒")

    stream = spotter.create_stream()
    stream.accept_waveform(SAMPLE_RATE, samples)
    stream.input_finished()

    result = spotter.get_result(stream)

    if result:
        print(f"\n🎉 测试成功！命中唤醒词：【{result}】")
    else:
        print("\n❌ 未命中任何关键词")
        print("建议：把 keywords_threshold 调到 0.1 再试；确认录音发音清晰")

if __name__ == "__main__":
    main()
