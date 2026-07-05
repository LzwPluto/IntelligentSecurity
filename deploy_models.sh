#!/bin/bash
# ============================================================
# 模型部署脚本 — 将模型文件复制到目标路径
# 用法: ./deploy_models.sh /path/to/model/source
# 默认从当前目录下的 models/ 文件夹获取
# ============================================================
set -euo pipefail

SRC="${1:-models}"
BASE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$SRC" ]; then
    echo "错误: 未找到模型源目录 '$SRC'"
    echo "用法: $0 [模型目录路径]"
    exit 1
fi

echo "从 $SRC 部署模型到 $BASE ..."

declare -A MAP=(
    ["$SRC/asr/sense-voice-encoder.rknn"]="$BASE/smart_assistant/voice/asr/sense-voice-encoder.rknn"
    ["$SRC/asr/fsmnvad-offline.onnx"]="$BASE/smart_assistant/voice/asr/fsmnvad-offline.onnx"
    ["$SRC/asr/embedding.npy"]="$BASE/smart_assistant/voice/asr/embedding.npy"
    ["$SRC/tts/encoder-en.onnx"]="$BASE/smart_assistant/TTS/encoder-en.onnx"
    ["$SRC/tts/decoder-en-3588.rknn"]="$BASE/smart_assistant/TTS/decoder-en-3588.rknn"
    ["$SRC/tts/decoder_rk3588.rknn"]="$BASE/smart_assistant/TTS/decoder_rk3588.rknn"
    ["$SRC/face/RetinaFace.rknn"]="$BASE/website/models/RetinaFace.rknn"
    ["$SRC/face/MobileFaceNet_fp16.rknn"]="$BASE/website/models/MobileFaceNet_fp16.rknn"
    ["$SRC/wakeup/encoder.rknn"]="$BASE/smart_assistant/voice/encoder.rknn"
    ["$SRC/wakeup/decoder.rknn"]="$BASE/smart_assistant/voice/decoder.rknn"
    ["$SRC/wakeup/joiner.rknn"]="$BASE/smart_assistant/voice/joiner.rknn"
    ["$SRC/wakeup/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"]="$BASE/smart_assistant/weakup/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
    ["$SRC/wakeup/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"]="$BASE/smart_assistant/weakup/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
    ["$SRC/wakeup/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"]="$BASE/smart_assistant/weakup/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
)

for src_file in "${!MAP[@]}"; do
    dst="${MAP[$src_file]}"
    if [ -f "$src_file" ]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src_file" "$dst"
        echo "  OK  $src_file -> $dst"
    else
        echo "  MISS  $src_file (跳过)"
    fi
done

echo "部署完成。"
