import cv2
import numpy as np
from . import config
import os

# =========================================
# 官方标准：112x112 人脸基准关键点（MobileFaceNet专用）
# =========================================
REFERENCE_FACIAL_POINTS = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041]
], dtype=np.float32)

# =========================================
# 纯OpenCV高速人脸对齐（替代慢速skimage）
# =========================================
def align_face_official(src_img, facial_pts):
    try:
        src_pts = facial_pts.astype(np.float32)
        matrix = cv2.estimateAffinePartial2D(
            src_pts,
            REFERENCE_FACIAL_POINTS,
            method=cv2.LMEDS,
            maxIters=2000
        )[0]
        aligned_face = cv2.warpAffine(src_img, matrix, (112, 112))
        return aligned_face
    except:
        return cv2.resize(src_img, (112, 112))

# =========================================
# 优化版：MobileFaceNet特征提取（保留存图调试）
# =========================================
def extract_feature(
    recog,
    face_crop,
    landmarks=None,
    offset_x=0,
    offset_y=0
):
    # 初始化计数器和保存目录（只执行一次）
    if not hasattr(extract_feature, "save_count"):
        extract_feature.save_count = 0
        extract_feature.save_dir = "picture"
        os.makedirs(extract_feature.save_dir, exist_ok=True)

    if face_crop is None or face_crop.size == 0:
        return None

    # =====================================
    # 人脸对齐
    # =====================================
    if landmarks is not None:
        landmarks_local = landmarks.copy()
        landmarks_local[:, 0] -= offset_x
        landmarks_local[:, 1] -= offset_y

        face = align_face_official(face_crop, landmarks_local)

        # 保留：调试保存10张对齐照片
        if extract_feature.save_count < 10:
            save_path = os.path.join(
                extract_feature.save_dir,
                f"align_{extract_feature.save_count}.jpg"
            )
            cv2.imwrite(save_path, face)
            extract_feature.save_count += 1
        if extract_feature.save_count >= 10:
            extract_feature.save_count = 0
    else:
        face = cv2.resize(face_crop, (config.FACE_SIZE, config.FACE_SIZE))

    # =====================================
    # MobileFaceNet预处理
    # =====================================
    face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    face = face.astype(np.float32)
    face = (face - 127.5) / 128.0
    face = np.expand_dims(face, axis=0)

    # =====================================
    # RKNN推理
    # =====================================
    outputs = recog.inference(inputs=[face])
    feature = outputs[0].flatten()

    # =====================================
    # L2归一化
    # =====================================
    norm = np.linalg.norm(feature)
    if norm > 0:
        feature = feature / norm

    return feature

# =========================================
# 欧氏距离
# =========================================
def calc_distance(feature1, feature2):
    return np.linalg.norm(feature1 - feature2)
