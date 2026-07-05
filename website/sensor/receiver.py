import json
import time
import socket
import logging
import threading

import paho.mqtt.client as mqtt

logger = logging.getLogger('sensor.receiver')
logger.setLevel(logging.INFO)

# Connection state — exposed so the frontend can show status
mqtt_connected = threading.Event()


def save_sensor_data(app, sensor_type, value):
    """Save sensor data to DB and emit via SocketIO."""
    try:
        with app.app_context():
            from extensions import db, socketio
            from database.models import SensorData

            record = SensorData(sensor_type=sensor_type, value=float(value))
            db.session.add(record)
            db.session.commit()

            socketio.emit('sensor_update', {
                'type': sensor_type,
                'value': float(value),
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
    except Exception as e:
        logger.error(f'[Sensor] Failed to save data: {e}')


def _create_mqtt_client(client_id):
    """Create MQTT client compatible with both paho-mqtt 1.x and 2.x."""
    try:
        # paho-mqtt 2.x - use VERSION1 to keep callback signatures simple
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                           client_id=client_id, clean_session=True)
    except (AttributeError, TypeError):
        # paho-mqtt 1.x
        return mqtt.Client(client_id=client_id, clean_session=True)


# --------------- MQTT Receiver ---------------

def start_mqtt_receiver(app):
    """Background thread: subscribe to MQTT with auto-reconnect."""
    broker = app.config['MQTT_BROKER']
    port = app.config['MQTT_PORT']
    topic = app.config['MQTT_TOPIC']
    username = app.config.get('MQTT_USERNAME', '')
    password = app.config.get('MQTT_PASSWORD', '')
    reconnect_delay = 1          # starts at 1s
    max_delay = 60               # cap at 60s

    def on_connect(client, userdata, flags, rc):
        nonlocal reconnect_delay
        if rc == 0:
            logger.info(f'[MQTT] Connected to {broker}:{port}')
            # Subscribe to main topic and per-type topics
            client.subscribe(topic)
            for stype in ['temperature', 'humidity', 'smoke']:
                client.subscribe(f'{topic}/{stype}')
            logger.info(f'[MQTT] Subscribed to: {topic}, {topic}/temperature, {topic}/humidity, {topic}/smoke')
            mqtt_connected.set()
            reconnect_delay = 1  # reset backoff on success
        else:
            msg = {
                1: '协议版本不正确',
                2: '客户端标识符无效',
                3: '服务器不可用',
                4: '用户名或密码错误',
                5: '未授权',
            }.get(rc, f'未知错误 (rc={rc})')
            logger.error(f'[MQTT] 连接被拒绝: {msg}')

    def on_disconnect(client, userdata, rc):
        mqtt_connected.clear()
        if rc == 0:
            logger.info('[MQTT] 已主动断开连接')
        else:
            logger.warning(f'[MQTT] 连接意外断开 (rc={rc})，将自动重连...')

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8').strip()
            if not payload:
                return

            topic_str = msg.topic

            # Support two formats:
            # Format 1 (JSON): topic=home/sensor, payload={"type":"temperature","value":25.5}
            # Format 2 (simple): topic=home/sensor/temperature, payload=25.5
            if topic_str == topic:
                # JSON format on main topic
                data = json.loads(payload)
                sensor_type = data.get('type')
                value = data.get('value')
                if sensor_type and value is not None:
                    save_sensor_data(app, sensor_type, float(value))
                    logger.info(f'[MQTT] Received: {sensor_type} = {value}')
                else:
                    logger.warning(f'[MQTT] 消息缺少 type 或 value: {payload}')
            elif topic_str.startswith(topic + '/'):
                # Simple format on sub-topic: home/sensor/temperature -> 25.5
                sensor_type = topic_str.split('/')[-1]
                if sensor_type in ('temperature', 'humidity', 'smoke'):
                    value = float(payload)
                    save_sensor_data(app, sensor_type, value)
                    logger.info(f'[MQTT] Received: {sensor_type} = {value}')
                else:
                    logger.warning(f'[MQTT] 未知传感器类型: {sensor_type}')
            else:
                logger.warning(f'[MQTT] 未知 topic: {topic_str}')

        except json.JSONDecodeError:
            logger.warning(f'[MQTT] 非 JSON 消息: {msg.payload}')
        except ValueError as e:
            logger.warning(f'[MQTT] 数值解析错误: {e}, payload: {msg.payload}')
        except Exception as e:
            logger.error(f'[MQTT] 处理消息异常: {e}')

    def on_log(client, userdata, level, buf):
        pass

    while True:
        client = None
        try:
            client = _create_mqtt_client(f'iot-flask-{int(time.time())}')
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_message = on_message
            client.on_log = on_log

            # Set username/password if configured
            if username:
                client.username_pw_set(username, password)

            # Reconnect within the paho loop itself (handles transient drops)
            client.reconnect_delay_set(min_delay=1, max_delay=max_delay)

            logger.info(f'[MQTT] 正在连接 {broker}:{port} ...')
            client.connect(broker, port, keepalive=60)

            # loop_forever blocks and auto-reconnects on transient failures.
            client.loop_forever()

        except ConnectionRefusedError:
            logger.warning(f'[MQTT] 连接被拒绝 ({broker}:{port})，'
                           f'{reconnect_delay}s 后重试...')
        except OSError as e:
            logger.warning(f'[MQTT] 网络错误: {e}，{reconnect_delay}s 后重试...')
        except Exception as e:
            logger.error(f'[MQTT] 未预期异常: {e}，{reconnect_delay}s 后重试...')
        finally:
            mqtt_connected.clear()
            if client:
                try:
                    client.disconnect()
                except Exception:
                    pass

        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_delay)  # exponential backoff


# --------------- TCP Socket Receiver ---------------

def start_socket_receiver(app):
    """Background thread: listen on TCP socket for sensor data."""
    host = app.config['SOCKET_HOST']
    port = app.config['SOCKET_PORT']
    reconnect_delay = 1
    max_delay = 30

    while True:
        server = None
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.settimeout(5)  # so accept() doesn't block forever
            server.bind((host, port))
            server.listen(5)
            logger.info(f'[Socket] Listening on {host}:{port}')
            reconnect_delay = 1  # reset on success

            while True:
                try:
                    client_sock, addr = server.accept()
                    client_sock.settimeout(10)
                    chunks = []
                    while True:
                        try:
                            chunk = client_sock.recv(4096)
                            if not chunk:
                                break
                            chunks.append(chunk)
                        except socket.timeout:
                            break
                    client_sock.close()

                    data = b''.join(chunks).decode('utf-8').strip()
                    if not data:
                        continue

                    msg = json.loads(data)
                    sensor_type = msg.get('type')
                    value = msg.get('value')
                    if sensor_type and value is not None:
                        save_sensor_data(app, sensor_type, value)
                        logger.info(f'[Socket] Received: {sensor_type} = {value}')
                    else:
                        logger.warning(f'[Socket] 消息缺少 type 或 value: {data}')

                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f'[Socket] 非 JSON 数据: {data}')
                except OSError as e:
                    logger.warning(f'[Socket] 客户端连接错误: {e}')
                    continue

        except OSError as e:
            logger.warning(f'[Socket] 绑定/监听失败 ({host}:{port}): {e}，'
                           f'{reconnect_delay}s 后重试...')
        except Exception as e:
            logger.error(f'[Socket] 未预期异常: {e}，{reconnect_delay}s 后重试...')
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_delay)
