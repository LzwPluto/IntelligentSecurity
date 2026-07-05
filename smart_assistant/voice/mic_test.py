import sys
import numpy as np
import sounddevice as sd

# 配置项
SAMPLE_RATE = 16000  # 采样率
BLOCK_SIZE = 1600    # 每次读取 0.1 秒的音频 (16000 * 0.1)
CHANNELS = 1         # 单声道

def audio_callback(indata, frames, time_info, status):
    """
    回调函数：声卡每收到一段数据就会执行一次
    """
    if status:
        print(f"\n⚠️ 警告: {status}", file=sys.stderr)
    
    # 获取音频数据并转成 1 维数组
    audio_data = indata[:, 0]
    
    # 计算当前这段音频的音量 (使用 RMS: 均方根)
    volume_rms = np.sqrt(np.mean(audio_data**2))
    
    # 为了让音量条更明显，我们把它放大一点，并转换成 0-50 的刻度
    volume_scaled = int(volume_rms * 1000)
    # 限制最大长度不超过 50
    volume_scaled = min(volume_scaled, 50) 
    
    # 打印音量条 (用 █ 表示音量)
    bar = "█" * volume_scaled
    print(f"\r🎤 实时音量: |{bar:<50}|", end="", flush=True)

def main():
    print("🔎 正在查找系统中的音频设备...")
    print(sd.query_devices())
    print("\n--------------------------------------------------")
    
    try:
        # 启动麦克风监听
        print(f"✅ 准备就绪！开始监听麦克风 (采样率: {SAMPLE_RATE}Hz)...")
        print("请对着麦克风说话，观察音量条变化 (按 Ctrl+C 退出)\n")
        
        with sd.InputStream(device=1,
                            samplerate=SAMPLE_RATE, 
                            blocksize=BLOCK_SIZE, 
                            channels=CHANNELS, 
                            dtype='float32', 
                            callback=audio_callback):
            # 保持主线程不退出
            while True:
                sd.sleep(100)
                
    except KeyboardInterrupt:
        print("\n\n🛑 已手动停止测试。")
    except Exception as e:
        print(f"\n\n❌ 打开麦克风失败！\n{e}")
        print("\n💡 提示：")
        print("1. 检查你的麦克风是否插好。")
        print("2. 看看上面打印的设备列表，如果默认设备不是麦克风，请在 InputStream 中手动指定 device=你的麦克风ID。")
        print("   例如：with sd.InputStream(device=2, ...)")

if __name__ == "__main__":
    main()
