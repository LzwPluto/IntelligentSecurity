import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import sherpa_onnx

# ================= 配置区域 =================
MODEL_DIR = Path(__file__).parent

TOKEN_FILE = str(MODEL_DIR / "tokens.txt")
ENCODER_FILE = str(MODEL_DIR / "encoder-epoch-13-avg-2-chunk-16-left-64.onnx")
DECODER_FILE = str(MODEL_DIR / "decoder-epoch-13-avg-2-chunk-16-left-64.onnx")
JOINER_FILE = str(MODEL_DIR / "joiner-epoch-13-avg-2-chunk-16-left-64.onnx")
KEYWORDS_FILE = str(MODEL_DIR / "keywords.txt")

# 音频参数
SAMPLE_RATE = 16000
MIC_DEVICE_ID = 1  # 板载麦克风对应硬件设备ID

# 唤醒效果调优
NUM_THREADS = 2
MAX_ACTIVE_PATHS = 4
KEYWORDS_THRESHOLD = 0.5
KEYWORDS_SCORE = 0.0
NUM_TRAILING_BLANKS = 1
# ============================================

def main():
    print("⏳ 正在加载唤醒模型，请稍候...")
    
    # 1. 初始化关键词唤醒器
    try:
        spotter = sherpa_onnx.KeywordSpotter(
            tokens=TOKEN_FILE,
            encoder=ENCODER_FILE,
            decoder=DECODER_FILE,
            joiner=JOINER_FILE,
            keywords_file=KEYWORDS_FILE,
            num_threads=NUM_THREADS,
            max_active_paths=MAX_ACTIVE_PATHS,
            keywords_threshold=KEYWORDS_THRESHOLD,
            keywords_score=KEYWORDS_SCORE,
            num_trailing_blanks=NUM_TRAILING_BLANKS,
        )
    except Exception as e:
        print(f"❌ 模型加载失败，请检查文件路径与模型版本是否匹配！\n{e}")
        return

    print("✅ 模型加载成功！")
    
    # 2. 创建解码流
    stream = spotter.create_stream()

    # 3. 麦克风音频回调
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"⚠ 音频状态警告: {status}", file=sys.stderr)
        
        samples = indata[:, 0].astype(np.float32)
        stream.accept_waveform(SAMPLE_RATE, samples)

    # 4. 启动麦克风并进入监听循环
    print("\n🎤 正在启动麦克风...")
    try:
        with sd.InputStream(
            device=MIC_DEVICE_ID,
            channels=1,
            dtype="float32",
            samplerate=SAMPLE_RATE,
            callback=audio_callback
        ):
            print("=========================================")
            print("👂 监听已启动，请说出唤醒词")
            print("   按 Ctrl+C 退出程序")
            print("=========================================\n")
            
            # 主循环：get_result 返回字符串，非空即命中关键词
            while True:
                result = spotter.get_result(stream)
                
                if result:
                    print(f"\n🔥 唤醒成功！命中词：【{result}】")
                    spotter.reset(stream)
                
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🛑 已停止监听，退出程序。")
    except Exception as e:
        print(f"\n❌ 运行出错：{e}")
        print("\n排查建议：")
        print("1. 音频相关错误：检查麦克风设备ID是否正确")
        print("2. 权限问题：将用户加入 audio 组后重新登录")

if __name__ == "__main__":
    main()
