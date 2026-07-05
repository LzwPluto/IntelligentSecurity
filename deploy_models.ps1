<#
.SYNOPSIS
  模型部署脚本 — 将模型文件复制到目标路径
.DESCRIPTION
  从指定源目录将模型文件复制到项目各模块的目标路径。
  默认源目录为当前目录下的 models/ 文件夹。
.PARAMETER Source
  模型文件所在目录，默认为 "models"
.EXAMPLE
  .\deploy_models.ps1
  .\deploy_models.ps1 D:\models
#>
param([string]$Source = "models")

$BASE = $PSScriptRoot

if (-not (Test-Path $Source)) {
    Write-Error "错误: 未找到模型源目录 '$Source'"
    exit 1
}

$map = @{
    "$Source/asr/sense-voice-encoder.rknn"      = "$BASE/smart_assistant/voice/asr/sense-voice-encoder.rknn"
    "$Source/asr/fsmnvad-offline.onnx"           = "$BASE/smart_assistant/voice/asr/fsmnvad-offline.onnx"
    "$Source/asr/embedding.npy"                  = "$BASE/smart_assistant/voice/asr/embedding.npy"
    "$Source/tts/encoder-en.onnx"                = "$BASE/smart_assistant/TTS/encoder-en.onnx"
    "$Source/tts/decoder-en-3588.rknn"           = "$BASE/smart_assistant/TTS/decoder-en-3588.rknn"
    "$Source/tts/decoder_rk3588.rknn"            = "$BASE/smart_assistant/TTS/decoder_rk3588.rknn"
    "$Source/face/RetinaFace.rknn"               = "$BASE/website/models/RetinaFace.rknn"
    "$Source/face/MobileFaceNet_fp16.rknn"       = "$BASE/website/models/MobileFaceNet_fp16.rknn"
    "$Source/wakeup/encoder.rknn"                = "$BASE/smart_assistant/voice/encoder.rknn"
    "$Source/wakeup/decoder.rknn"                = "$BASE/smart_assistant/voice/decoder.rknn"
    "$Source/wakeup/joiner.rknn"                 = "$BASE/smart_assistant/voice/joiner.rknn"
    "$Source/wakeup/encoder-12.onnx"             = "$BASE/smart_assistant/weakup/encoder-epoch-12-avg-2-chunk-16-left-64.onnx"
    "$Source/wakeup/decoder-12.onnx"             = "$BASE/smart_assistant/weakup/decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
    "$Source/wakeup/joiner-12.onnx"              = "$BASE/smart_assistant/weakup/joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
    "$Source/wakeup/encoder-12-int8.onnx"        = "$BASE/smart_assistant/weakup/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
    "$Source/wakeup/decoder-12-int8.onnx"        = "$BASE/smart_assistant/weakup/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
    "$Source/wakeup/joiner-12-int8.onnx"         = "$BASE/smart_assistant/weakup/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
}

Write-Host "从 $Source 部署模型到 $BASE ..." -ForegroundColor Cyan

foreach ($entry in $map.GetEnumerator()) {
    $src = $entry.Key
    $dst = $entry.Value
    if (Test-Path $src) {
        $dir = Split-Path $dst -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $src $dst -Force
        Write-Host "  OK  $src -> $dst" -ForegroundColor Green
    } else {
        Write-Host "  MISS $src (跳过)" -ForegroundColor Yellow
    }
}

Write-Host "部署完成。" -ForegroundColor Cyan
