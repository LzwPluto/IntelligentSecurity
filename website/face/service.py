import threading
import time
import logging
import numpy as np
import cv2

from extensions import db, socketio

logger = logging.getLogger('face.service')

_face_service = None


def get_face_service():
  return _face_service


class FaceRecognitionService:
  def __init__(self, app):
      self.app = app
      self.detector = None
      self.recognizer = None
      self.known_features = []  # [(name, np.array), ...]
      self.running = False
      self._last_result = None

  def init_models(self):
      from face.utils import load_model
      from face.config import DET_MODEL, REC_MODEL

      if not self._check_rknn_available():
          raise RuntimeError('rknnlite 不可用，NPU 推理无法运行')

      self.detector = load_model(DET_MODEL)
      self.recognizer = load_model(REC_MODEL)
      self.refresh_known_features()
      logger.info(f'人脸识别模型加载完成，已录入 {len(self.known_features)} 人')

  def _check_rknn_available(self):
      try:
          from rknnlite.api import RKNNLite
          return True
      except ImportError:
          return False

  def refresh_known_features(self):
      from database.models import FaceFeature
      with self.app.app_context():
          records = FaceFeature.query.all()
          self.known_features = [
              (r.name, np.frombuffer(r.feature, dtype=np.float32))
              for r in records
          ]

  def process_frame(self, frame):
      from face.retinaface import detect_face
      from face.mobileface import extract_feature, calc_distance
      from face.config import THRESHOLD

      result = detect_face(self.detector, frame)
      if result is None:
          return None

      x1, y1, x2, y2, landmarks = result
      face_crop = frame[y1:y2, x1:x2]
      if face_crop.size == 0:
          return None

      feature = extract_feature(self.recognizer, face_crop, landmarks, x1, y1)
      if feature is None:
          return None

      best_name = None
      best_distance = float('inf')
      for name, known_feat in self.known_features:
          dist = calc_distance(known_feat, feature)
          if dist < best_distance:
              best_distance = dist
              best_name = name

      if best_distance < THRESHOLD:
          return {'name': best_name, 'is_stranger': False, 'distance': best_distance}
      else:
          return {'name': '陌生人', 'is_stranger': True, 'distance': best_distance}

  def run(self):
      from datetime import datetime
      from database.models import FaceLog
      from camera.capture import camera_lock, _get_camera

      self.running = True
      cam = _get_camera()

      while self.running:
          acquired = camera_lock.acquire(timeout=0.1)
          if not acquired:
              time.sleep(0.3)
              continue

          try:
              ret, frame = cam.read_raw_frame()
          finally:
              camera_lock.release()

          if not ret:
              time.sleep(0.5)
              continue

          result = self.process_frame(frame)
          if result is None:
              time.sleep(0.3)
              continue

          socketio.emit('face_update', {
                  'name': result['name'],
                  'is_stranger': result['is_stranger'],
                  'distance':float(round(result['distance'], 4)),  # ← 改这一行
                  'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
          })

          try:
              with self.app.app_context():
                  log = FaceLog(
                      name=result['name'],
                      is_stranger=result['is_stranger'],
                      distance=result['distance']
                  )
                  db.session.add(log)
                  db.session.commit()
          except Exception as e:
              logger.error(f'写入识别日志失败: {e}')

          self._last_result = result
          logger.info(f'识别: {result["name"]} (距离={result["distance"]:.4f})')
          time.sleep(1)

      logger.info('人脸识别服务已停止')

  def capture_enroll_frames(self, count=10):
      from face.retinaface import detect_face
      from face.mobileface import extract_feature
      from camera.capture import camera_lock, _get_camera

      cam = _get_camera()
      features = []
      attempts = 0
      max_attempts = count * 5

      while len(features) < count and attempts < max_attempts:
          attempts += 1
          acquired = camera_lock.acquire(timeout=0.1)
          if not acquired:
              time.sleep(0.2)
              continue
          try:
              ret, frame = cam.read_raw_frame()
          finally:
              camera_lock.release()

          if not ret:
              continue

          result = detect_face(self.detector, frame)
          if result is None:
              continue

          x1, y1, x2, y2, landmarks = result
          face_crop = frame[y1:y2, x1:x2]
          if face_crop.size == 0:
              continue

          feature = extract_feature(self.recognizer, face_crop, landmarks, x1, y1)
          if feature is not None:
              features.append(feature)
              time.sleep(0.05)

      return features


def start_face_service(app):
    """启动人脸识别服务（供 app.py 调用）"""
    global _face_service

    # 先确保摄像头可用，再加载 RKNN 模型
    from camera.capture import _get_camera
    cam = _get_camera()
    if not cam.is_available:
        cam.open()
        app.logger.info(f'摄像头预加载状态: {"可用" if cam.is_available else "不可用"}')

    _face_service = FaceRecognitionService(app)
    _face_service.init_models()
    threading.Thread(target=_face_service.run, daemon=True).start()
    app.logger.info('人脸识别服务已启动')
