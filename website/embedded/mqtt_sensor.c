/*
 * IoT 智能家居 - MQTT 传感器客户端
 *
 * 功能: 读取温湿度(DHT11)和烟雾(MQ-2)传感器, 通过MQTT发送到服务器
 *
 * 编译: gcc -o mqtt_sensor mqtt_sensor.c -lmosquitto -lwiringPi -lpthread
 * 运行: ./mqtt_sensor
 *
 * 注意: 需要先安装 mosquitto-dev 和 wiringPi
 *   sudo apt-get install libmosquitto-dev
 *   sudo apt-get install wiringpi  (树莓派)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <mosquitto.h>

/* ============ 配置区 - 根据你的环境修改 ============ */

#define MQTT_BROKER     "192.168.1.100"   /* MQTT服务器IP, 改成你电脑的IP */
#define MQTT_PORT       1883
#define MQTT_TOPIC      "home/sensor"
#define MQTT_USERNAME   ""                /* 如果Mosquitto没设密码, 留空 */
#define MQTT_PASSWORD   ""

/* DHT11 接线 */
#define DHT11_PIN       7                 /* BCM GPIO 4 = wiringPi 7 */

/* MQ-2 烟雾传感器 (ADC读取, 需要MCP3008或类似ADC芯片) */
/* 如果直接读取数字输出, 用普通GPIO即可 */
#define SMOKE_DO_PIN    0                 /* 数字输出引脚 */

/* 发送间隔(秒) */
#define SEND_INTERVAL   5

/* ============ 全局变量 ============ */

static volatile int running = 1;
static struct mosquitto *mosq = NULL;

/* 信号处理 - Ctrl+C 优雅退出 */
void signal_handler(int sig) {
    (void)sig;
    running = 0;
}

/* ============ DHT11 读取 (简化版, 实际项目建议用库) ============ */

/*
 * DHT11 时序比较复杂, 这里给出框架代码
 * 推荐使用已有的DHT11库, 比如:
 *   - wiringPi 自带的 dht11 读取函数
 *   - 或者用 pigpio 库
 *
 * 下面是伪代码框架, 实际使用时替换为真实读取函数
 */
int read_dht11(float *temperature, float *humidity) {
    /*
     * TODO: 替换为你的DHT11读取代码
     * 推荐方式:
     *   1. 使用 wiringPi 库
     *   2. 使用 pigpio 库
     *   3. 使用 Python 脚本调用 Adafruit_DHT 库, 通过管道读取
     */

    /* 模拟数据 - 测试用, 实际替换为真实读取 */
    *temperature = 25.0 + (rand() % 100) / 10.0;  /* 25.0 ~ 35.0 */
    *humidity = 50.0 + (rand() % 300) / 10.0;     /* 50.0 ~ 80.0 */

    return 0;  /* 0=成功, -1=失败 */
}

/* ============ MQ-2 烟雾传感器读取 ============ */

int read_smoke(float *smoke_ppm) {
    /*
     * MQ-2 有两种输出:
     *   1. 模拟输出(AO): 需要ADC芯片(如MCP3008)读取, 返回0-1023
     *   2. 数字输出(DO): 超过阈值输出高电平, 可直接用GPIO读取
     *
     * 这里演示数字输出方式:
     *   - HIGH(1): 检测到烟雾
     *   - LOW(0): 正常
     *
     * 如果用ADC, 读取后做线性映射:
     *   smoke_ppm = (adc_value / 1023.0) * 1000.0;
     */

    /* 模拟数据 - 测试用, 实际替换为真实读取 */
    *smoke_ppm = (float)(rand() % 200);  /* 0 ~ 200 ppm */

    return 0;
}

/* ============ MQTT 回调函数 ============ */

void on_connect(struct mosquitto *mosq, void *userdata, int rc) {
    (void)mosq;
    (void)userdata;
    if (rc == 0) {
        printf("[MQTT] 连接成功!\n");
    } else {
        fprintf(stderr, "[MQTT] 连接失败, 错误码: %d\n", rc);
    }
}

void on_disconnect(struct mosquitto *mosq, void *userdata, int rc) {
    (void)mosq;
    (void)userdata;
    if (rc != 0) {
        fprintf(stderr, "[MQTT] 意外断开 (rc=%d), 将自动重连...\n", rc);
    }
}

void on_publish(struct mosquitto *mosq, void *userdata, int mid) {
    (void)mosq;
    (void)userdata;
    (void)mid;
    /* 消息发送成功, 可以在这里添加日志 */
}

/* ============ 发送传感器数据 ============ */

int publish_sensor(const char *type, float value) {
    char payload[128];
    int ret;

    /* JSON格式: {"type":"temperature","value":25.5} */
    snprintf(payload, sizeof(payload),
             "{\"type\":\"%s\",\"value\":%.1f}", type, value);

    ret = mosquitto_publish(mosq, NULL, MQTT_TOPIC,
                            (int)strlen(payload), payload, 0, false);
    if (ret != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "[MQTT] 发送失败: %s (type=%s, value=%.1f)\n",
                mosquitto_strerror(ret), type, value);
        return -1;
    }

    printf("[Sensor] %s = %.1f\n", type, value);
    return 0;
}

/* ============ 主函数 ============ */

int main(int argc, char *argv[]) {
    (void)argc;
    (void)argv;

    float temperature, humidity, smoke_ppm;
    int ret;

    printf("========================================\n");
    printf("  IoT 智能家居 - MQTT 传感器客户端\n");
    printf("========================================\n");
    printf("MQTT Broker: %s:%d\n", MQTT_BROKER, MQTT_PORT);
    printf("Topic: %s\n", MQTT_TOPIC);
    printf("发送间隔: %d 秒\n", SEND_INTERVAL);
    printf("========================================\n\n");

    /* 注册信号处理 */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    /* 初始化随机数种子 */
    srand((unsigned int)time(NULL));

    /* 初始化 mosquitto 库 */
    mosquitto_lib_init();

    /* 创建 mosquitto 客户端实例 */
    mosq = mosquitto_new("iot-embedded-client", true, NULL);
    if (!mosq) {
        fprintf(stderr, "错误: 无法创建 mosquitto 实例\n");
        return 1;
    }

    /* 设置回调函数 */
    mosquitto_connect_callback_set(mosq, on_connect);
    mosquitto_disconnect_callback_set(mosq, on_disconnect);
    mosquitto_publish_callback_set(mosq, on_publish);

    /* 设置用户名密码(如果配置了的话) */
    if (strlen(MQTT_USERNAME) > 0) {
        ret = mosquitto_username_pw_set(mosq, MQTT_USERNAME, MQTT_PASSWORD);
        if (ret != MOSQ_ERR_SUCCESS) {
            fprintf(stderr, "设置用户名密码失败: %s\n", mosquitto_strerror(ret));
        }
    }

    /* 设置自动重连: 最小1秒, 最大60秒 */
    mosquitto_reconnect_delay_set(mosq, 1, 60, true);

    /* 连接 MQTT Broker */
    printf("正在连接 MQTT Broker %s:%d ...\n", MQTT_BROKER, MQTT_PORT);
    ret = mosquitto_connect(mosq, MQTT_BROKER, MQTT_PORT, 60);
    if (ret != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "连接失败: %s\n", mosquitto_strerror(ret));
        fprintf(stderr, "请检查:\n");
        fprintf(stderr, "  1. MQTT Broker 是否已启动 (mosquitto)\n");
        fprintf(stderr, "  2. IP地址是否正确\n");
        fprintf(stderr, "  3. 防火墙是否放行 1883 端口\n");
        mosquitto_destroy(mosq);
        mosquitto_lib_cleanup();
        return 1;
    }

    /* 启动网络循环(后台线程处理重连和消息收发) */
    ret = mosquitto_loop_start(mosq);
    if (ret != MOSQ_ERR_SUCCESS) {
        fprintf(stderr, "启动网络循环失败: %s\n", mosquitto_strerror(ret));
        mosquitto_destroy(mosq);
        mosquitto_lib_cleanup();
        return 1;
    }

    printf("开始采集传感器数据...\n\n");

    /* 主循环: 读取传感器 -> 发送MQTT */
    while (running) {
        /* 读取温湿度 */
        if (read_dht11(&temperature, &humidity) == 0) {
            publish_sensor("temperature", temperature);
            usleep(200000);  /* 间隔200ms避免消息过快 */
            publish_sensor("humidity", humidity);
            usleep(200000);
        } else {
            fprintf(stderr, "[Sensor] DHT11 读取失败\n");
        }

        /* 读取烟雾浓度 */
        if (read_smoke(&smoke_ppm) == 0) {
            publish_sensor("smoke", smoke_ppm);
        } else {
            fprintf(stderr, "[Sensor] MQ-2 读取失败\n");
        }

        printf("---\n");

        /* 等待下一次采集 */
        for (int i = 0; i < SEND_INTERVAL && running; i++) {
            sleep(1);
        }
    }

    /* 清理 */
    printf("\n正在退出...\n");
    mosquitto_loop_stop(mosq, true);
    mosquitto_disconnect(mosq);
    mosquitto_destroy(mosq);
    mosquitto_lib_cleanup();

    printf("已退出.\n");
    return 0;
}
