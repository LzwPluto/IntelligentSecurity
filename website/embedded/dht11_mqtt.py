#!/usr/bin/env python3
"""
IoT 智能家居 - DHT11 + MQ-2 传感器 MQTT 客户端 (树莓派)

功能: 读取 DHT11 温湿度传感器 + MQ-2 烟雾传感器, 通过 MQTT 发送数据

依赖安装:
    pip install paho-mqtt Adafruit_DHT

接线:
    DHT11:
        VCC -> 3.3V
        GND -> GND
        DATA -> GPIO4 (BCM编号, 物理引脚7)
        (DATA和VCC之间接10K上拉电阻)

    MQ-2:
        VCC -> 5V
        GND -> GND
        DO  -> GPIO17 (BCM编号, 物理引脚11) (数字输出)
        AO  -> 需要ADC芯片读取 (如MCP3008)

用法:
    python dht11_mqtt.py
    python dht11_mqtt.py --broker 192.168.1.100
"""

import json
import time
import argparse
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("请安装: pip install paho-mqtt")
    sys.exit(1)

try:
    import Adafruit_DHT
    DHT_SENSOR = Adafruit_DHT.DHT11
    DHT_PIN = 4  # BCM GPIO 4
    HAS_DHT = True
except ImportError:
    print("[警告] 未安装 Adafruit_DHT, 将使用模拟数据")
    print("  安装: pip install Adafruit_DHT")
    HAS_DHT = False

try:
    import RPi.GPIO as GPIO
    SMOKE_PIN = 17  # BCM GPIO 17
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SMOKE_PIN, GPIO.IN)
    HAS_GPIO = True
except (ImportError, RuntimeError):
    print("[警告] 未检测到 RPi.GPIO, 将使用模拟数据")
    HAS_GPIO = False


def read_dht11():
    """读取 DHT11 温湿度传感器."""
    if HAS_DHT:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
    # 模拟数据
    import random
    return round(22 + random.uniform(-3, 8), 1), round(55 + random.uniform(-10, 15), 1)


def read_smoke():
    """读取 MQ-2 烟雾传感器 (数字输出)."""
    if HAS_GPIO:
        # 数字输出: 1=检测到烟雾, 0=正常
        smoke_detected = GPIO.input(SMOKE_PIN)
        return 150.0 if smoke_detected else 20.0
    # 模拟数据
    import random
    return round(random.uniform(0, 50) + (100 if random.random() < 0.02 else 0), 1)


def main():
    parser = argparse.ArgumentParser(description='DHT11 + MQ-2 MQTT 客户端')
    parser.add_argument('--broker', default='localhost', help='MQTT Broker IP')
    parser.add_argument('--port', type=int, default=1883, help='MQTT 端口')
    parser.add_argument('--topic', default='home/sensor', help='MQTT Topic')
    parser.add_argument('--interval', type=int, default=5, help='采集间隔(秒)')
    parser.add_argument('--username', default='', help='MQTT 用户名')
    parser.add_argument('--password', default='', help='MQTT 密码')
    args = parser.parse_args()

    print("=" * 50)
    print("  IoT 智能家居 - 传感器 MQTT 客户端")
    print("=" * 50)
    print(f"  DHT11: {'GPIO' + str(DHT_PIN) if HAS_DHT else '模拟'}")
    print(f"  MQ-2:  {'GPIO' + str(SMOKE_PIN) if HAS_GPIO else '模拟'}")
    print(f"  Broker: {args.broker}:{args.port}")
    print("=" * 50)

    client = mqtt.Client(client_id='iot-rpi-sensor', clean_session=True)
    if args.username:
        client.username_pw_set(args.username, args.password)

    try:
        client.connect(args.broker, args.port, keepalive=60)
        client.loop_start()
        print("[OK] 已连接 MQTT Broker\n")
    except Exception as e:
        print(f"[错误] 连接失败: {e}")
        sys.exit(1)

    try:
        while True:
            temp, hum = read_dht11()
            smoke = read_smoke()

            for stype, val in [('temperature', temp), ('humidity', hum), ('smoke', smoke)]:
                payload = json.dumps({'type': stype, 'value': val})
                client.publish(args.topic, payload)
                print(f"  {stype} = {val}")

            print(f"  --- 已发送 ---")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n停止中...")
    finally:
        client.loop_stop()
        client.disconnect()
        if HAS_GPIO:
            GPIO.cleanup()
        print("已退出.")


if __name__ == '__main__':
    main()
