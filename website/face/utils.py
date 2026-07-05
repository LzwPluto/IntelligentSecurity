# utils.py - RKNN 模型加载工具

from rknnlite.api import RKNNLite


def load_model(model_path):
    rknn = RKNNLite()
    ret = rknn.load_rknn(model_path)
    if ret != 0:
        raise RuntimeError(f"RKNN模型加载失败: {model_path}")
    ret = rknn.init_runtime()
    if ret != 0:
        raise RuntimeError(f"RKNN Runtime初始化失败: {model_path}")
    return rknn
