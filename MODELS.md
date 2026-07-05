# 模型文件清单

以下文件因体积较大被 `.gitignore` 排除，不会随 GitHub 仓库上传。
在部署到开发板时需手动放置到对应路径。

## 文件总览

| # | 文件 | 大小 | 原始路径 | 所属模块 | 来源 |
|---|------|------|---------|---------|------|
| 1 | `sense-voice-encoder.rknn` | 462 MB | `smart_assistant/voice/asr/` | ASR 编码器 | SenseVoice ONNX → RKNN 转换 |
| 2 | `decoder-en-3588.rknn` | 46 MB | `smart_assistant/TTS/` | TTS 解码器 | Piper TTS → RKNN 转换 |
| 3 | `encoder-en.onnx` | 27 MB | `smart_assistant/TTS/` | TTS 编码器 | Piper TTS 原版 ONNX |
| 4 | `encoder.onnx` | 27 MB | `smart_assistant/TTS/` | TTS 编码器 | Piper TTS 原始模型 |
| 5 | `decoder_rk3588.rknn` | 19 MB | `smart_assistant/TTS/` | TTS 解码器 | RKNN 格式备用 |
| 6 | `RetinaFace.rknn` | 18 MB | `website/models/` | 人脸检测 | RetinaFace → RKNN 转换 |
| 7 | `encoder.rknn` | 12 MB | `smart_assistant/voice/` | 唤醒词编码器 | sherpa-onnx → RKNN |
| 8 | `encoder-epoch-12-avg-2-chunk-16-left-64.onnx` | 12 MB | `smart_assistant/weakup/` | 唤醒词编码器 | sherpa-onnx 原版 |
| 9 | `MobileFaceNet_fp16.rknn` | 2.3 MB | `website/models/` | 人脸识别 | MobileFaceNet → RKNN |
| 10 | `fsmnvad-offline.onnx` | 1.7 MB | `smart_assistant/voice/asr/` | VAD 检测 | FSMN-VAD ONNX |
| 11 | `decoder.rknn` | 0.8 MB | `smart_assistant/voice/` | 唤醒词解码器 | sherpa-onnx → RKNN |
| 12 | `decoder-epoch-12-avg-2-chunk-16-left-64.onnx` | 0.6 MB | `smart_assistant/weakup/` | 唤醒词解码器 | sherpa-onnx 原版 |
| 13 | `joiner.rknn` | 0.2 MB | `smart_assistant/voice/` | 唤醒词联接器 | sherpa-onnx → RKNN |
| 14 | `joiner-epoch-12-avg-2-chunk-16-left-64.onnx` | 0.2 MB | `smart_assistant/weakup/` | 唤醒词联接器 | sherpa-onnx 原版 |
| 15 | `decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx` | 0.2 MB | `smart_assistant/weakup/` | 唤醒词解码器(INT8) | sherpa-onnx 量化版 |
| 16 | `encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx` | 4.6 MB | `smart_assistant/weakup/` | 唤醒词编码器(INT8) | sherpa-onnx 量化版 |

**总计：约 633 MB**

## 模型获取方式

### 方式一：从原始模型转换（推荐）

项目提供了转换脚本：

```bash
# ASR (SenseVoice)
cd smart_assistant/voice/asr
python convert_rknn.py

# TTS (Piper)
cd smart_assistant/TTS/paroli-on-orangepi/tools
python decoder2rknn.py --model decoder-en.onnx

# 人脸 (RetinaFace / MobileFaceNet)
# 参考 rknn-toolkit2 官方转换指南
```

### 方式二：直接下载预转换模型

（预转换模型下载链接待补充 — 可上传至 GitHub Releases 或网盘）

## 文件结构映射

部署时确保以下路径存在：

```
smart_assistant/
├── voice/asr/
│   ├── sense-voice-encoder.rknn    ← ASR 编码器（NPU）
│   ├── fsmnvad-offline.onnx        ← VAD（CPU）
│   └── embedding.npy               ← 语言嵌入表
├── weakup/
│   ├── encoder-epoch-12-avg-2-chunk-16-left-64.onnx
│   ├── decoder-epoch-12-avg-2-chunk-16-left-64.onnx
│   ├── joiner-epoch-12-avg-2-chunk-16-left-64.onnx
│   ├── tokens.txt                  ← 保留（已跟踪）
│   └── keywords.txt                ← 保留（已跟踪）
├── TTS/
│   ├── encoder-en.onnx
│   ├── decoder-en-3588.rknn
│   └── config-en.json              ← 保留（已跟踪）
└── voice/
    ├── encoder.rknn
    ├── decoder.rknn
    └── joiner.rknn

website/models/
├── RetinaFace.rknn
└── MobileFaceNet_fp16.rknn
```
