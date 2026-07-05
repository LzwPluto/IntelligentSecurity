#!/usr/bin/env python
# coding: utf-8

import os
import re
from typing import Optional, Set
from rknn.api import RKNN
from math import exp
from sys import exit
import argparse
import onnxscript
from onnxscript.rewriter import pattern
import onnx.numpy_helper as onh
import numpy as np
import onnx
import onnxruntime as ort
from rknn.utils import onnx_edit

os.chdir(os.path.dirname(os.path.abspath(__file__)))

speech_length = 171

def _remove_file(path: str, *, keep: Optional[Set[str]] = None) -> None:
    if not path:
        return
    keep_paths: Set[str] = {os.path.abspath(item) for item in keep} if keep else set()
    normalized = os.path.abspath(path)
    if keep_paths and normalized in keep_paths:
        return
    if not os.path.exists(normalized):
        return
    try:
        os.remove(normalized)
        print(f'cleaned temp model: {normalized}')
    except OSError as err:
        print(f'warning: failed to remove {normalized}: {err}')

def _with_suffix(path: str, suffix: str) -> str:
    stem, ext = os.path.splitext(path)
    return f"{stem}{suffix}{ext}"

def _sanitize_name(name: str) -> str:
    return re.sub(r'[^0-9A-Za-z_]', '_', name)

def _insert_div_node(model: onnx.ModelProto, tensor_name: str, divisor: float = 16.0) -> bool:
    graph = model.graph

    for node in graph.node:
        if node.op_type == 'Div' and tensor_name in node.output:
            return False

    producer_index = None
    output_index = None
    for idx, node in enumerate(graph.node):
        for out_idx, output in enumerate(node.output):
            if output == tensor_name:
                producer_index = idx
                output_index = out_idx
                producer_node = node
                break
        if producer_index is not None:
            break

    if producer_index is None:
        raise RuntimeError(f"Producer node for tensor {tensor_name} not found.")

    pre_div_output = f"{tensor_name}_pre_div"
    producer_node.output[output_index] = pre_div_output

    sanitized = _sanitize_name(tensor_name)
    const_output = f"{sanitized}_div_const"
    const_node_name = f"{sanitized}_DivConst"
    div_node_name = f"{sanitized}_Div"

    const_tensor = onnx.helper.make_tensor(
        name=f"{const_node_name}_value",
        data_type=onnx.TensorProto.FLOAT,
        dims=[],
        vals=[divisor],
    )

    const_node = onnx.helper.make_node(
        'Constant',
        inputs=[],
        outputs=[const_output],
        value=const_tensor,
        name=const_node_name,
    )

    div_node = onnx.helper.make_node(
        'Div',
        inputs=[pre_div_output, const_output],
        outputs=[tensor_name],
        name=div_node_name,
    )

    graph.node.insert(producer_index + 1, const_node)
    graph.node.insert(producer_index + 2, div_node)
    return True

def _scale_initializer(model: onnx.ModelProto, initializer_name: str, divisor: float = 16.0) -> bool:
    for idx, initializer in enumerate(model.graph.initializer):
        if initializer.name == initializer_name:
            data = onh.to_array(initializer).astype(np.float32, copy=False)
            scaled = data / divisor
            model.graph.initializer[idx].CopyFrom(onh.from_array(scaled, name=initializer_name))
            return True
    return False

def convert_encoder(model_path: str):
    rknn = RKNN(verbose=True)

    ONNX_MODEL = os.path.abspath(model_path)
    if not os.path.isfile(ONNX_MODEL):
        print(f'Model file not found: {model_path}')
        exit(1)
    if not ONNX_MODEL.lower().endswith('.onnx'):
        print(f'Model file must be an ONNX file: {model_path}')
        exit(1)

    RKNN_MODEL = os.path.splitext(ONNX_MODEL)[0] + ".rknn"
    DATASET = "dataset.txt"
    QUANTIZE = False
    original_model = ONNX_MODEL
    preserve_files: Set[str] = {original_model}


    print('--> Patching model to avoid overflow issue')
    base_model = onnx.load(ONNX_MODEL)
    modified = False
    for layer_idx in range(48, 49): 
        for target in [
            f'/encoders.{layer_idx}/feed_forward/activation/Relu_output_0',
            f'/encoders.{layer_idx}/norm2/Cast_output_0',
        ]:
            modified |= _insert_div_node(base_model, target, divisor=2.0)
    bias_scaled = False
    if modified:
        for layer_idx in range(48, 49): 
            bias_scaled |= _scale_initializer(base_model, f'model.encoders.{layer_idx}.feed_forward.w_2.bias', divisor=2.0)
    div_model_path = _with_suffix(ONNX_MODEL, "_div")
    onnx.save(base_model, div_model_path)
    if os.path.exists(div_model_path):
        previous_model = ONNX_MODEL
        ONNX_MODEL = div_model_path
        _remove_file(previous_model, keep=preserve_files)
    if modified:
        if bias_scaled:
            print('done (created div-adjusted model and scaled bias)')
        else:
            print('done (created div-adjusted model; bias initializer not found)')
    else:
        print('done (div nodes already present)')
        
    #开局先给我来个大惊喜，rknn做第一步常量折叠的时候就会在这个子图里报错，所以要单独拿出来先跑一遍
    #然后把这个子图的输出结果保存下来喂给rknn
    extract_model_path = os.path.join(os.getcwd(), "extract_model.onnx")
    onnx.utils.extract_model(ONNX_MODEL, extract_model_path, ['speech_lengths'], ['/make_pad_mask/Cast_2_output_0'])
    sess = ort.InferenceSession(extract_model_path, providers=['CPUExecutionProvider'])
    extract_result = sess.run(None, {"speech_lengths": np.array([speech_length], dtype=np.int64)})[0]
    _remove_file(extract_model_path)

    # 删掉模型最后的多余transpose, 速度从365ms提升到259ms
    edited_model_path = _with_suffix(ONNX_MODEL, "_edited")
    ret = onnx_edit(model = ONNX_MODEL,
        export_path = edited_model_path,
        # # 1, len, 25055 -> 1, 25055, 1, len   # 这个是坏的, 我真服了，
        outputs_transform = {'encoder_out': 'a,b,c->a,c,1,b'},
        # outputs_transform = {'encoder_out': 'a,b,c->a,c,b'},
    )
    if os.path.exists(edited_model_path):
        previous_model = ONNX_MODEL
        ONNX_MODEL = edited_model_path
        _remove_file(previous_model, keep=preserve_files)

    # pre-process config
    print('--> Config model')
    rknn.config(quantized_algorithm='normal', quantized_method='channel', target_platform='rk3588', optimization_level=3)
    print('done')

    # Load ONNX model
    print("--> Loading model")
    current_model_path = ONNX_MODEL
    ret = rknn.load_onnx(
        model=current_model_path,
        inputs=["speech", "/make_pad_mask/Cast_2_output_0"],
        input_size_list=[[1, speech_length, 560], [extract_result.shape[0], extract_result.shape[1]]],
        input_initial_val=[None, extract_result],
        # outputs=["output"]
    )

    if ret != 0:
        print('Load model failed!')
        exit(ret)
    print('done')
    _remove_file(current_model_path, keep=preserve_files)

    # Build model
    print('--> Building model')
    ret = rknn.build(do_quantization=QUANTIZE, dataset=DATASET, rknn_batch_size=None)
    if ret != 0:
        print('Build model failed!')
        exit(ret)
    print('done')

    # export
    print('--> Export RKNN model')
    ret = rknn.export_rknn(RKNN_MODEL)
    if ret != 0:
        print('Export RKNN model failed!')
        exit(ret)
    print('done')
    # 精度分析(可选)
    # rknn.accuracy_analysis(inputs=["input_content.npy"], target="rk3588", device_id=None)

# usage: python convert_rknn.py path/to/model.onnx

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=str, help="path to source ONNX model")
    args = parser.parse_args()

    convert_encoder(args.model_path)
