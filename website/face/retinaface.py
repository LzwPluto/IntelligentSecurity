import cv2
import numpy as np
from . import config

from math import ceil
from itertools import product


# =========================================
# PriorBox
# =========================================
def PriorBox(image_size):

    anchors = []

    min_sizes = [
        [16, 32],
        [64, 128],
        [256, 512]
    ]

    steps = [8, 16, 32]

    feature_maps = [
        [
            ceil(image_size[0] / step),
            ceil(image_size[1] / step)
        ]
        for step in steps
    ]

    for k, f in enumerate(feature_maps):

        min_sizes_ = min_sizes[k]

        for i, j in product(
            range(f[0]),
            range(f[1])
        ):

            for min_size in min_sizes_:

                s_kx = min_size / image_size[1]
                s_ky = min_size / image_size[0]

                dense_cx = [
                    x * steps[k] / image_size[1]
                    for x in [j + 0.5]
                ]

                dense_cy = [
                    y * steps[k] / image_size[0]
                    for y in [i + 0.5]
                ]

                for cy, cx in product(
                    dense_cy,
                    dense_cx
                ):

                    anchors += [
                        cx,
                        cy,
                        s_kx,
                        s_kx,
                    ]

    output = np.array(
        anchors
    ).reshape(-1, 4)

    return output


# =========================================
# box decode
# =========================================
def box_decode(loc, priors):

    variances = [0.1, 0.2]

    boxes = np.concatenate(

        (
            priors[:, :2] +
            loc[:, :2] *
            variances[0] *
            priors[:, 2:],

            priors[:, 2:] *
            np.exp(
                loc[:, 2:] *
                variances[1]
            )
        ),

        axis=1
    )

    boxes[:, :2] -= boxes[:, 2:] / 2

    boxes[:, 2:] += boxes[:, :2]

    return boxes


# =========================================
# landmark decode
# =========================================
def decode_landm(pre, priors):

    variances = [0.1, 0.2]

    landmarks = np.concatenate((

        priors[:, :2] + pre[:, :2] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 2:4] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 4:6] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 6:8] * variances[0] * priors[:, 2:],
        priors[:, :2] + pre[:, 8:10] * variances[0] * priors[:, 2:]

    ), axis=1)

    return landmarks


# =========================================
# NMS
# =========================================
def nms(dets, thresh):

    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (
        (x2 - x1 + 1) *
        (y2 - y1 + 1)
    )

    order = scores.argsort()[::-1]

    keep = []

    while order.size > 0:

        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h

        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]

    return keep


# =========================================
# 🔥 修正版：RetinaFace人脸检测（适配MobileFaceNet）
# =========================================
def detect_face(detector, frame):

    img_height, img_width = frame.shape[:2]

    # =====================================
    # 🔥 修改1：官方标准预处理（必加！精度核心）
    # =====================================
    img = cv2.resize(frame, (config.DET_SIZE, config.DET_SIZE))
    img = np.float32(img)  # 转浮点
    img -= (104, 117, 123)  # 官方固定减均值
    img = np.expand_dims(img, axis=0)

    # 推理
    outputs = detector.inference(inputs=[img])
    loc, conf, landms = outputs

    # PriorBox
    priors = PriorBox((config.DET_SIZE, config.DET_SIZE))

    # 解码
    boxes = box_decode(loc.squeeze(0), priors)
    landms = decode_landm(landms.squeeze(0), priors)

    # 缩放坐标
    scale_boxes = np.array([config.DET_SIZE]*4)
    boxes = boxes * scale_boxes

    scale_landms = np.array([config.DET_SIZE]*10)
    landms = landms * scale_landms

    # =====================================
    # 🔥 修改2：置信度提升为官方标准 0.9
    # =====================================
    scores = conf.squeeze(0)[:, 1]
    inds = np.where(scores > 0.9)[0]

    boxes = boxes[inds]
    scores = scores[inds]
    landms = landms[inds]

    if len(boxes) == 0:
        return None

    # =====================================
    # 🔥 修改3：新增Top-K过滤（提速+减冗余）
    # =====================================
    order = scores.argsort()[::-1][:5000]
    boxes = boxes[order]
    scores = scores[order]
    landms = landms[order]

    # NMS
    dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
    keep = nms(dets, 0.4)
    dets = dets[keep]
    landms = landms[keep]
    dets = dets[:750, :]
    landms = landms[:750, :]

    # 取最优人脸
    face = dets[0]
    landmark = landms[0]
    x1, y1, x2, y2, score = face

    # =====================================
    # 🔥 修改4：先映射回原图 → 再扩大框（顺序修正！）
    # =====================================
    x1 = int(x1 * img_width / config.DET_SIZE)
    y1 = int(y1 * img_height / config.DET_SIZE)
    x2 = int(x2 * img_width / config.DET_SIZE)
    y2 = int(y2 * img_height / config.DET_SIZE)

    # =====================================
    # 🔥 修改5：人脸框全方位外扩（适配对齐）
    # =====================================
    h = y2 - y1
    w = x2 - x1
    # 顶部扩5%（额头），底部扩15%（下巴）
    y1 = max(y1 - int(h * 0.05), 0)
    y2 = min(y2 + int(h * 0.15), img_height)
    # 左右各扩10%（脸颊）
    x1 = max(x1 - int(w * 0.1), 0)
    x2 = min(x2 + int(w * 0.1), img_width)

    # 关键点格式转换
    landmark = landmark.reshape(5, 2)
    # 关键点映射回原图
    landmark[:, 0] *= (img_width / config.DET_SIZE)
    landmark[:, 1] *= (img_height / config.DET_SIZE)
    landmark = landmark.astype(np.float32)

    # 边界限制
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_width, x2)
    y2 = min(img_height, y2)

    # 关键点裁剪
    landmark[:, 0] = np.clip(landmark[:, 0], x1, x2)
    landmark[:, 1] = np.clip(landmark[:, 1], y1, y2)

    # Debug
    print(f"face score = {score:.4f}")
    print(f"face box = {x1} {y1} {x2} {y2}")
    print("landmark =")
    print(landmark)

    if x2 <= x1 or y2 <= y1:
        return None

    # =====================================
    # 🔥 修改6：五点顺序 100% 对齐官方标准
    # 左眼、右眼、鼻尖、左嘴角、右嘴角
    # 完美适配MobileFaceNet对齐接口
    # =====================================
    return x1, y1, x2, y2, landmark
