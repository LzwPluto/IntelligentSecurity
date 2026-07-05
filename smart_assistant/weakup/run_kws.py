import sys
from pathlib import Path

import sherpa_onnx
import sounddevice as sd
import numpy as np

MODEL_DIR = Path(__file__).parent

# 1. 初始化唤醒器 (新版 API 直接传参，不需要 Config 对象)
try:
    spotter = sherpa_onnx.KeywordSpotter(
        tokens=str(MODEL_DIR / "tokens.txt"),
        encoder=str(MODEL_DIR / "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
        decoder=str(MODEL_DIR / "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
        joiner=str(MODEL_DIR / "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"),
        keywords_file=str(MODEL_DIR / "keywords.txt"),
        num_threads=1,
        provider="cpu"
    )
except Exception as e:
    print(f"模型初始化失败，请检查文件路径或 keywords.txt 的格式！\n错误信息: {e}")
    sys.exit(1)

stream = spotter.create_stream()

print("--------------------------------------------------")
print("初始化成功！模型已加载。")
print("请确保你的 keywords.txt 格式完全正确。")
print("正在监听麦克风，请说话 (按 Ctrl+C 退出)...")
print("--------------------------------------------------")

# 2. 定义麦克风音频回调函数
def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)

    # sounddevice 采集的 float32 数据直接拉平为一维数组
    samples = indata.reshape(-1)

    # 喂给模型
    stream.accept_waveform(16000, samples)

    # 进行推理检测
    while spotter.is_ready(stream):
        spotter.decode_stream(stream)

    # 获取检测结果 (做兼容处理，应对不同版本的返回类型)
    result = spotter.get_result(stream)
    keyword = result if isinstance(result, str) else getattr(result, "keyword", "")

    # 如果检测到唤醒词，终端会打印出来，并重置流准备下一次唤醒
    if keyword:
        print(f"\n【💥 触发唤醒！】检测到关键词: {keyword}")
        # 必须重置音频流，否则会无限循环触发
        spotter.reset_stream(stream)

# 3. 启动麦克风流 (采样率强制指定为 16000，单声道)
try:
    with sd.InputStream(device=1, samplerate=16000, blocksize=4096, channels=1, dtype='float32', callback=audio_callback):
        # 保持主线程运行
        sd.sleep(int(1000 * 60 * 60 * 24))
except KeyboardInterrupt:
    print("\n程序手动退出。")
except Exception as e:
    print(f"\n麦克风启动失败: {e}")
