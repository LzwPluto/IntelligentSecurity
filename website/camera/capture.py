import threading
import time
import logging

logger = logging.getLogger('camera.capture')

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning('[Camera] OpenCV (cv2) 未安装, 摄像头功能不可用')

camera_lock = threading.Lock()


def _parse_device(device):
    try:
        return int(device)
    except (ValueError, TypeError):
        return device


class CameraCapture:
    def __init__(self, device='/dev/video21', width=640, height=480):
        self.device = _parse_device(device)
        self.width = width
        self.height = height
        self.cap = None
        self.is_available = False

    def open(self):
        if not CV2_AVAILABLE:
            return False

        logger.info(f'[Camera] 尝试打开摄像头, device={self.device!r}')

        attempts = [
            ('default', self.device),
        ]
        if isinstance(self.device, str):
            attempts.append(('index0', 0))

        for label, dev in attempts:
            try:
                logger.info(f'[Camera] 尝试 {label}: dev={dev!r}')
                self.cap = cv2.VideoCapture(dev)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    ret, _ = self.cap.read()
                    if ret:
                        self.is_available = True
                        logger.info(f'[Camera] 摄像头已打开 ({label}: {dev})')
                        return True
                    else:
                        self.cap.release()
                        logger.warning(f'[Camera] {label}:{dev} 打开成功但读帧失败')
                else:
                    self.cap.release()
                    logger.warning(f'[Camera] {label}:{dev} isOpened=False')
            except Exception as e:
                logger.warning(f'[Camera] {label}:{dev} 异常: {e}')

        logger.error('[Camera] 所有方式均失败, 摄像头不可用')
        self.is_available = False
        return False

    def read_frame(self):
        if not self.is_available or self.cap is None:
            if not self.open():
                return False, None
        ret, frame = self.cap.read()
        if not ret:
            self.is_available = False
            return False, None
        _, jpeg = cv2.imencode('.jpg', frame)
        return True, jpeg.tobytes()

    def read_raw_frame(self):
        if not self.is_available or self.cap is None:
            if not self.open():
                return False, None
        ret, frame = self.cap.read()
        if not ret:
            self.is_available = False
            return False, None
        return True, frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.is_available = False


def _init_camera():
    from flask import current_app
    device = current_app.config.get('CAMERA_DEVICE', '/dev/video21')
    width = current_app.config.get('CAMERA_WIDTH', 640)
    height = current_app.config.get('CAMERA_HEIGHT', 480)
    return CameraCapture(device=device, width=width, height=height)


camera = None


def _get_camera():
    global camera
    if camera is None:
        try:
            camera = _init_camera()
        except RuntimeError:
            camera = CameraCapture()
    return camera


def generate_frames():
    if not CV2_AVAILABLE:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               b'\r\n')
        return

    cam = _get_camera()

    while True:
        acquired = camera_lock.acquire(timeout=1)
        if not acquired:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   b'\r\n')
            time.sleep(0.5)
            continue

        try:
            ok, jpeg = cam.read_frame()
            if ok:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            else:
                time.sleep(0.1)
        finally:
            camera_lock.release()
