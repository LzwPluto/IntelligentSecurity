---
license: agpl-3.0
language:
- en
- zh
- ja
- ko
base_model: lovemefan/SenseVoice-onnx
tags:
- rknn
---

# SenseVoiceSmall-RKNN2

### (English README see below)

SenseVoice是具有音频理解能力的音频基础模型， 包括语音识别（ASR）、语种识别（LID）、语音情感识别（SER）和声学事件分类（AEC）或声学事件检测（AED）。

当前SenseVoice-small支持中、粤、英、日、韩语的多语言语音识别，情感识别和事件检测能力，具有极低的推理延迟。 

- 推理速度(RKNN2)：RK3588上单核NPU推理速度约20倍 (每秒识别20秒的音频), 比官方rknn-model-zoo中提供的whisper约快6倍.
- 内存占用(RKNN2)：约1.1GB

## 使用方法

1. 克隆项目到本地

2. 安装依赖

```bash
pip install kaldi_native_fbank onnxruntime sentencepiece soundfile pyyaml "numpy<2" rknn-toolkit-lite2
```

1. 运行

```bash
python ./sensevoice_rknn.py --audio_file output.wav
```

如果使用自己的音频文件测试发现识别不正常，你可能需要提前将它转换为16kHz, 16bit, 单声道的wav格式。

```bash
ffmpeg -i input.mp3 -f wav -acodec pcm_s16le -ac 1 -ar 16000 output.wav
```

## RKNN模型转换

你需要提前安装rknn-toolkit2, 测试可用的版本为2.3.3a25，可从https://console.zbox.filez.com/l/I00fc3 下载(密码为"rknn")

1. 下载或转换onnx模型

可以从 https://huggingface.co/lovemefan/SenseVoice-onnx 下载到onnx模型.  
应该也可以根据 https://github.com/FunAudioLLM/SenseVoice 中的文档从Pytorch模型转换得到onnx模型.

模型文件应该命名为'sense-voice-encoder.onnx', 放在转换脚本所在目录.

2. 转换为rknn模型
```bash
python convert_rknn.py ./sense-voice-encoder.onnx
```

## 已知问题

- ~~RKNN2使用fp16推理时可能会出现溢出，导致结果为inf，可以尝试修改输入数据的缩放比例来解决.  
  在`sensevoice_rknn.py`中将`SPEECH_SCALE`设置为更小的值.~~ (现在应该已经通过模型内部插入缩放算子解决了)

## 参考
- [FunAudioLLM/SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)
- [lovemefan/SenseVoice-python](https://github.com/lovemefan/SenseVoice-python)

# English README

# SenseVoiceSmall-RKNN2

SenseVoice is an audio foundation model with audio understanding capabilities, including Automatic Speech Recognition (ASR), Language Identification (LID), Speech Emotion Recognition (SER), and Acoustic Event Classification (AEC) or Acoustic Event Detection (AED).

Currently, SenseVoice-small supports multilingual speech recognition, emotion recognition, and event detection for Chinese, Cantonese, English, Japanese, and Korean, with extremely low inference latency.

- Inference speed (RKNN2): About 20x real-time on a single NPU core of RK3588 (processing 20 seconds of audio per second), approximately 6 times faster than the official whisper model provided in the rknn-model-zoo.
- Memory usage (RKNN2): About 1.1GB

## Usage

1. Clone the project to your local machine

2. Install dependencies

```bash
pip install kaldi_native_fbank onnxruntime sentencepiece soundfile pyyaml "numpy<2" rknn-toolkit-lite2
```

3. Run

```bash
python ./sensevoice_rknn.py --audio_file output.wav
```

If you find that recognition is not working correctly when testing with your own audio files, you may need to convert them to 16kHz, 16-bit, mono WAV format in advance.

```bash
ffmpeg -i input.mp3 -f wav -acodec pcm_s16le -ac 1 -ar 16000 output.wav
```

## RKNN Model Conversion

You need to install rknn-toolkit2 in advance. The tested working version is 2.3.3a25, which can be downloaded from https://console.zbox.filez.com/l/I00fc3 (password: "rknn").

1. Download or convert the ONNX model

You can download the ONNX model from https://huggingface.co/lovemefan/SenseVoice-onnx.
It should also be possible to convert from a PyTorch model to an ONNX model according to the documentation at https://github.com/FunAudioLLM/SenseVoice.

The model file should be named 'sense-voice-encoder.onnx' and placed in the same directory as the conversion script.

2. Convert to RKNN model
```bash
python convert_rknn.py ./sense-voice-encoder.onnx
```

## Known Issues

- ~~When using fp16 inference with RKNN2, overflow may occur, resulting in inf values. You can try modifying the scaling ratio of the input data to resolve this.  
  Set `SPEECH_SCALE` to a smaller value in `sensevoice_rknn.py`.~~ (This issue should now be resolved by inserting scaling operators inside the model.)

## References
- [FunAudioLLM/SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)
- [lovemefan/SenseVoice-python](https://github.com/lovemefan/SenseVoice-python)
