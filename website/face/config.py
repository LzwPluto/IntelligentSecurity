import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# 模型路径
MODEL_DIR = os.path.join(PROJECT_DIR, 'models')
DET_MODEL = os.path.join(MODEL_DIR, 'RetinaFace.rknn')
REC_MODEL = os.path.join(MODEL_DIR, 'MobileFaceNet_fp16.rknn')

# 摄像头（与 loT 的 .env 配置一致）
CAMERA_ID = '/dev/video21'
CAM_WIDTH = 640
CAM_HEIGHT = 480

# RetinaFace 参数
DET_SIZE = 320
FACE_SIZE = 112

# 识别阈值（欧氏距离，越小越匹配）
THRESHOLD = 0.9

# 录入采集帧数
ENROLL_FRAMES = 10
