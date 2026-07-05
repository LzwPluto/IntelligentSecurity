import json
import time
import threading
from collections import deque

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

MAX_READINGS = 10

_sensor_readings = {
    "temperature": deque(maxlen=MAX_READINGS),
    "humidity": deque(maxlen=MAX_READINGS),
    "smoke": deque(maxlen=MAX_READINGS),
    "pir": deque(maxlen=MAX_READINGS),
}

_lock = threading.Lock()
_client = None
_started = False
_alert_callback = None
_alert_cooldown = {}

ALERT_COOLDOWN_SEC = 1800

SMOKE_COOLDOWN_SEC = 300

SMOKE_THRESHOLD = 500
TEMP_HIGH_THRESHOLD = 40.0
TEMP_LOW_THRESHOLD = 0.0


def set_alert_callback(callback):
    global _alert_callback
    _alert_callback = callback


def _check_danger(sensor_type, reading):
    if sensor_type == "smoke":
        value = reading.get("value", 0)
        if value >= SMOKE_THRESHOLD:
            return True, f"smoke_level_{int(value)}"
    elif sensor_type == "temperature":
        value = reading.get("value", 0)
        if value >= TEMP_HIGH_THRESHOLD:
            return True, f"temp_high_{int(value)}"
        if value <= TEMP_LOW_THRESHOLD:
            return True, f"temp_low_{int(value)}"
    elif sensor_type == "pir":
        detected = reading.get("detected", 0)
        if detected:
            hour = time.localtime().tm_hour
            if hour >= 22 or hour < 6:
                return True, "pir_triggered"
    return False, ""


def _trigger_alert(sensor_type, reading):
    if _alert_callback is None:
        return

    danger, key = _check_danger(sensor_type, reading)
    if not danger:
        return

    now = time.time()
    cooldown = SMOKE_COOLDOWN_SEC if sensor_type == "smoke" else ALERT_COOLDOWN_SEC
    if key in _alert_cooldown:
        if now - _alert_cooldown[key] < cooldown:
            return

    _alert_cooldown[key] = now

    if sensor_type == "smoke":
        title = "🚨 Smoke Alert"
        content = (
            f"Smoke detected! Level: {reading.get('value', 0)}\n"
            "Please check the premises immediately."
        )
    elif sensor_type == "temperature":
        value = reading.get("value", 0)
        if value >= TEMP_HIGH_THRESHOLD:
            title = "🔥 High Temperature Alert"
            content = (
                f"Temperature is too high: {value}°C\n"
                "Please check the environment."
            )
        else:
            title = "❄️ Low Temperature Alert"
            content = (
                f"Temperature is too low: {value}°C\n"
                "Risk of freezing."
            )
    elif sensor_type == "pir":
        title = "👤 Motion Detected"
        content = (
            "Motion detected by PIR sensor.\n"
            "Someone may be present."
        )
    else:
        return

    _alert_callback(title, content, "danger")


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("home/sensor")
        client.subscribe("home/sensor/pir")
        print("[SensorData] MQTT connected, subscribed to sensor topics")
    else:
        print(f"[SensorData] MQTT connection failed, rc={rc}")


def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        sensor_type = data.get("type", "")

        reading = {"ts": int(time.time())}

        if sensor_type == "pir":
            reading["detected"] = data.get("detected", 0)
        else:
            reading["value"] = data.get("value", 0)

        with _lock:
            if sensor_type in _sensor_readings:
                _sensor_readings[sensor_type].append(reading)

        _trigger_alert(sensor_type, reading)
    except Exception:
        pass


def start(broker_host="localhost", broker_port=1883):

    global _client, _started

    if _started:
        return

    if mqtt is None:
        print("[SensorData] paho-mqtt not available, sensor data disabled")
        return

    _client = mqtt.Client()
    _client.on_connect = _on_connect
    _client.on_message = _on_message

    try:
        _client.connect(broker_host, broker_port, 60)
        thread = threading.Thread(target=_client.loop_forever, daemon=True)
        thread.start()
        _started = True
        print(f"[SensorData] MQTT subscriber started on {broker_host}:{broker_port}")
    except Exception as e:
        print(f"[SensorData] Failed to start MQTT subscriber: {e}")


def get_recent_data(limit=10):

    with _lock:
        result = {}
        for sensor_type, dq in _sensor_readings.items():
            readings = list(dq)[-limit:]
            if readings:
                result[sensor_type] = readings
        return result
