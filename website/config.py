import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'iot-smart-home-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "data", "iot.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MQTT settings
    MQTT_BROKER = os.environ.get('MQTT_BROKER', 'localhost')
    MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
    MQTT_TOPIC = os.environ.get('MQTT_TOPIC', 'home/sensor')
    MQTT_USERNAME = os.environ.get('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
    MQTT_ENABLED = os.environ.get('MQTT_ENABLED', 'true').lower() == 'true'

    # TCP Socket settings (alternative to MQTT)
    SOCKET_HOST = os.environ.get('SOCKET_HOST', '0.0.0.0')
    SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 5050))
    SOCKET_ENABLED = os.environ.get('SOCKET_ENABLED', 'false').lower() == 'true'

    # Camera settings
    # CAMERA_DEVICE: 设备路径(如 /dev/video21) 或数字索引(如 0)
    CAMERA_DEVICE = os.environ.get('CAMERA_DEVICE', '/dev/video21')
    CAMERA_WIDTH = int(os.environ.get('CAMERA_WIDTH', 640))
    CAMERA_HEIGHT = int(os.environ.get('CAMERA_HEIGHT', 480))

    # Weather API - Seniverse (optional, wttr.in fallback if not configured)
    SENIVERSE_API_KEY = os.environ.get('SENIVERSE_API_KEY', '')
    SENIVERSE_LOCATION = os.environ.get('SENIVERSE_LOCATION', 'shanghai')

    # Sensor thresholds (for alerts)
    TEMP_HIGH = float(os.environ.get('TEMP_HIGH', 35.0))
    TEMP_LOW = float(os.environ.get('TEMP_LOW', 10.0))
    HUMIDITY_HIGH = float(os.environ.get('HUMIDITY_HIGH', 80.0))
    HUMIDITY_LOW = float(os.environ.get('HUMIDITY_LOW', 20.0))
    SMOKE_HIGH = float(os.environ.get('SMOKE_HIGH', 300.0))

    # Face recognition
    FACE_ENABLED = os.environ.get('FACE_ENABLED', 'true').lower() == 'true'
    FACE_THRESHOLD = float(os.environ.get('FACE_THRESHOLD', 0.9))
