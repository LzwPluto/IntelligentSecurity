# 基于多模态AI的家庭智能安防系统

> 2026年全国大学生嵌入式芯片与系统设计竞赛 — 方向一：边缘人工智能应用  
> 硬件平台：ELF 2 开发板（瑞芯微 RK3588）

## 系统架构

系统采用四层架构：**传感器层 → 边缘AI推理层 → Web可视化层 → 云端LLM层**，各层通过 MQTT 消息中间件松耦合通信。

```
┌─────────────────────────────────────┐
│          云端 LLM 层                  │
│    DeepSeek API (语义理解)            │
└────────────────┬────────────────────┘
                 │ HTTPS
┌────────────────▼────────────────────┐
│    边缘 AI 推理层 (ELF 2 / RK3588)    │
│                                      │
│  ┌── 边缘Agent ─────────────────┐   │
│  │ Wakeup→Recorder→ASR(NPU)→   │   │
│  │ LLM→Dispatcher→TTS(NPU)     │   │
│  └──────────────────────────────┘   │
│  ┌── 人脸识别 ─────────────────┐   │
│  │ RetinaFace(NPU)→MobileFace  │   │
│  │ (NPU)→Match→SocketIO        │   │
│  └──────────────────────────────┘   │
│  ┌── Web仪表盘 ────────────────┐   │
│  │  Flask+SocketIO+Chart.js    │   │
│  └──────────────────────────────┘   │
└────────────────┬────────────────────┘
                 │ MQTT Broker
┌────────────────▼────────────────────┐
│     传感器层 (ELF 2 40pin GPIO)       │
│  AHT20(I²C)  MQ-2(ADC)  PIR(GPIO)  │
└─────────────────────────────────────┘
```

## 快速开始

### 1. 克隆代码

```bash
git clone https://github.com/LzwPluto/IntelligentSecurity.git
cd IntelligentSecurity
```

### 2. 部署模型文件

模型文件（`.rknn` / `.onnx`，共 ~633 MB）因体积大未包含在 Git 仓库中。

**方式一**：从 GitHub Releases 下载（推荐）
```bash
# 下载模型压缩包
wget https://github.com/LzwPluto/IntelligentSecurity/releases/download/v1.0/models.tar.gz
tar -xzf models.tar.gz
./deploy_models.sh models/
```

**方式二**：自行转换
```bash
# ASR 模型转换
cd smart_assistant/voice/asr
python convert_rknn.py

# TTS 模型转换
cd smart_assistant/TTS/paroli-on-orangepi/tools
python decoder2rknn.py --model decoder-en.onnx
```

### 3. 配置密钥

```bash
export DEEPSEEK_API_KEY="sk-xxx"
export SENIVERSE_API_KEY="your_key"
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_CHAT_ID="oc_xxx"
```

### 4. 运行

```bash
# 启动 Mosquitto MQTT Broker
mosquitto -c website/mosquitto.conf -d

# 启动传感器采集（需 GPIO 权限）
sudo 传感器代码/sensor_app

# 启动 Web 仪表盘
cd website && python app.py

# 启动语音助手
python smart_assistant/assistant.py
```

## 项目结构

```
IntelligentSecurity/
├── smart_assistant/          # 边缘AI语音助手
│   ├── assistant.py          # 主入口
│   ├── config.py             # 配置（环境变量）
│   ├── weakup/               # 唤醒词 (sherpa-onnx)
│   ├── voice/                # 语音流水线
│   │   ├── asr/              # SenseVoice ASR (NPU)
│   │   ├── llm/              # DeepSeek API + Parser
│   │   ├── dispatcher/       # 意图分发
│   │   ├── services/         # 业务服务 (天气/音乐/传感器等)
│   │   ├── response/         # TTS 输出
│   │   └── recorder/         # 音频采集
│   └── TTS/                  # Piper TTS (NPU)
├── website/                  # Flask Web 仪表盘
│   ├── app.py                # Flask 入口
│   ├── face/                 # 人脸识别 (RetinaFace + MobileFaceNet)
│   ├── sensor/               # MQTT 传感器接收
│   ├── camera/               # 摄像头
│   ├── weather/              # 天气
│   └── templates/            # 前端页面
├── 传感器代码/                # C 语言传感器采集程序
│   ├── epoll_queue.c         # epoll 事件驱动
│   ├── aht20.c               # AHT20 温湿度
│   └── mqtt_client.c         # MQTT 发布
├── models/                   # 模型文件（需自行下载）
├── performance_test.py       # 性能测试套件
├── MODELS.md                 # 模型清单
├── deploy_models.sh          # 模型部署脚本 (Linux)
└── deploy_models.ps1         # 模型部署脚本 (Windows)
```

## 性能指标

| 指标 | 目标 | 实测 |
|------|------|------|
| ASR 推理实时率 (RTF) | < 0.3 | **0.0702** |
| TTS 合成速度 | < 1s/句 | **0.847 s/句** |
| 人脸检测帧率 | > 10 FPS | **41.65 FPS** |
| 人脸识别准确率 | > 95% | **95.2%** |
| 唤醒词响应延迟 | < 500ms | **47.48 ms** |
| 传感器采集-显示延迟 | < 2s | **0.004 s** |
| 四模型并发内存占用 | < 2 GB | **1.595 GB** |
| NPU 利用率 | > 50% | **61.3%** |
| Web 仪表盘刷新延迟 | < 1s | **96.5 ms** |

## 关键技术栈

| 类别 | 技术 |
|------|------|
| 语音唤醒 | sherpa-onnx (Zipformer-Transducer) |
| 语音识别 | SenseVoice (RKNN on NPU) |
| 语义理解 | DeepSeek API + System Prompt |
| 语音合成 | Piper TTS (RKNN on NPU) |
| 人脸检测 | RetinaFace (RKNN on NPU) |
| 人脸识别 | MobileFaceNet (RKNN on NPU) |
| Web 框架 | Flask + SocketIO + Chart.js |
| 消息中间件 | Mosquitto MQTT |
| 传感器 | AHT20 / MQ-2 / PIR |
| NPU 驱动 | RKNN Runtime (rknnlite) |

## 许可证

本项目仅用于竞赛目的。
