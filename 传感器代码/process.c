#include <stdio.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <unistd.h>
#include "mqtt_client.h"
#include "led_control.h"

#include "queue.h"
#include "log.h"

/* ===== MQ参数 ===== */
#define VOLTAGE_SUPPLY    5.0
#define LOAD_RESISTOR     10.0
#define RO_CLEAN_DRY_AIR  35.0

/* ===== 阈值（LED 报警触发） ===== */
#define TEMP_THRESHOLD   30.0   // 温度超过 30°C 触发
#define SMOKE_THRESHOLD  500.0  // 烟雾 ppm 超过 500 触发

#define MQ_SCALE_PATH "/sys/bus/iio/devices/iio:device0/in_voltage_scale"

/*led硬件配置*/
#define LED_CHIP_PATH   "/dev/gpiochip3"   // 根据实际 GPIO chip 修改
#define LED_LINE_OFFSET 11                 // 你的 LED 对应的 line 号

/* ===== 时间窗口参数 ===== */
#define PRESENCE_HOLD_TIME 5
#define KEEP_INTERVAL 2
#define MIN_TRIGGER_GAP_MS 200

/* ===== 轮询控制 ===== */
#define LOOP_INTERVAL_US 100000

/* ===== MQTT Topic ===== */
#define TOPIC_SENSOR    "home/sensor"       /* Flask 仪表盘监听的 topic */
#define TOPIC_PIR       "home/sensor/pir"   /* PIR 人体感应 (单独 topic) */

extern queue_t g_queue;

/* ===== 读取float ===== */
float read_float_from_file(const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        LOGE("[SYS] fopen scale failed");
        return 0.0;
    }

    float val;
    if (fscanf(fp, "%f", &val) != 1) {
        fclose(fp);
        return 0.0;
    }

    fclose(fp);
    return val;
}

/* ===== MQ计算 ===== */
float MQ2_GetPPM(int adc_raw, float adc_scale) {

    float v_out = (float)adc_raw * adc_scale * 3.0 / 1000.0;

    if (v_out <= 0.01 || v_out >= VOLTAGE_SUPPLY)
        return -1;

    float rs = LOAD_RESISTOR * ((VOLTAGE_SUPPLY / v_out) - 1.0);
    float ratio = rs / RO_CLEAN_DRY_AIR;

    return 1000.0 / pow(ratio, 0.62);
}

/* ===== 发送传感器数据到 Flask ===== */
static void publish_sensor(const char *type, float value) {
    char json[128];
    snprintf(json, sizeof(json),
        "{\"type\":\"%s\",\"value\":%.1f}", type, value);
    mqtt_publish(TOPIC_SENSOR, json);
    LOG_INFO_M("MQTT", "发送: %s = %.1f", type, value);
}

/* ===== 处理线程 ===== */
void* process_thread(void* arg) {

    /* MQTT初始化 */
    if (mqtt_init() != 0) {
        LOGE("[SYS] MQTT初始化失败, 数据将无法上报");
    }
    
        /*===== LED初始化 =====*/
    if (led_init(LED_CHIP_PATH, LED_LINE_OFFSET) != 0) {
        LOGE("[LED] 初始化失败，LED 功能不可用");
    printf("led initial unsucessful");
    } else {
        // 可设置闪烁间隔（可选）
        printf("led_init success\n");
        led_set_blink_interval_ms(200);  // 200ms 亮灭切换

    }

    sensor_packet_t pkt;

    int last_state = 0;

    time_t last_keep_time = 0;
    time_t last_log_time  = 0;

    struct timespec last_trigger_ts = {0};
    time_t last_motion_time = 0;

    float adc_scale = read_float_from_file(MQ_SCALE_PATH);
    if (adc_scale == 0.0)
        adc_scale = 0.439453125;

        /* ===== 最新传感器值 ===== */
    float latest_temp = 25.0;
    float latest_humid = 50.0;
    float latest_smoke = 0.0;

    /* ===== LED 控制变量 ===== */
    struct timespec last_led_toggle = {0, 0};
    int led_on_off = 0;          // 当前 LED 状态
    int need_blink = 0;          // 是否需要闪烁
    clock_gettime(CLOCK_MONOTONIC, &last_led_toggle);

    LOGI("[SYS] process线程启动, ADC scale=%.8f", adc_scale);

    while (1) {

        time_t now = time(NULL);

        /* ===================== 队列 ===================== */
        while (try_pop_queue(&g_queue, &pkt)) {

            /* ===== PIR 人体感应 ===== */
            if (pkt.type == SENSOR_MOTION && pkt.data.motion.detected) {

                struct timespec ts;
                clock_gettime(CLOCK_MONOTONIC, &ts);

                long gap_ms = (ts.tv_sec - last_trigger_ts.tv_sec) * 1000 +
                              (ts.tv_nsec - last_trigger_ts.tv_nsec) / 1000000;

                if (gap_ms < MIN_TRIGGER_GAP_MS)
                    continue;

                last_trigger_ts = ts;
                last_motion_time = now;

                LOGD("[SYS] PIR触发");

                if (last_state == 0) {
                    LOGI("[SYS] SR: 有人进入");
                    last_state = 1;
                }

                /* PIR 数据发到单独 topic (Flask 暂不处理, 留给后续扩展) */
                char json[128];
                snprintf(json, sizeof(json),
                    "{\"type\":\"pir\",\"detected\":1}");
                mqtt_publish(TOPIC_PIR, json);
            }

            /* ===== AHT20 温湿度 ===== */
            if (pkt.type == SENSOR_AHT20) {

                float t = pkt.data.aht20.temperature;
                float h = pkt.data.aht20.humidity;
		latest_temp = t;

                LOG_INFO_M("SYS", "AHT20 温湿度 T=%.1f°C H=%.1f%%", t, h);

                /* 分两条消息发送, 格式与 Flask 仪表盘一致 */
                publish_sensor("temperature", t);
                usleep(100000);  /* 间隔100ms */
                publish_sensor("humidity", h);
            }

            /* ===== MQ-2 烟雾 ===== */
            if (pkt.type == SENSOR_MQ) {

                int raw = pkt.data.mq.raw;

                float ppm = MQ2_GetPPM(raw, adc_scale);
                float voltage = (float)raw * adc_scale * 3.0 / 1000.0;
		latest_smoke = ppm;
                if (ppm < 0) {
                    LOGW("[SYS] MQ数据异常 raw=%d", raw);
                    continue;
                }

                LOGD("[SYS] MQ raw=%d V=%.3f ppm=%.2f",
                     raw, voltage, ppm);

                /* 发送烟雾浓度 */
                publish_sensor("smoke", ppm);

                if (last_state == 1 && ppm > 300) {
                    LOGW("[SYS] 危险：有人 + 气体异常");
                }
            }
        }

        /* ===== 状态机 ===== */
        if (last_state == 1) {

            if (now - last_motion_time <= PRESENCE_HOLD_TIME) {

                if (now - last_keep_time >= KEEP_INTERVAL) {
                    LOGI("[SYS] SR: 有人逗留");
                    last_keep_time = now;
                }

            } else {
                LOGI("[SYS] SR: 人已离开");
                last_state = 0;
            }
        }

        if (now != last_log_time) {
            LOGD("[SYS] 状态=%s",
                 last_state ? "有人" : "无人");
            last_log_time = now;
        }


	        /* ===== LED 闪烁判断 ===== */
        if (latest_temp > TEMP_THRESHOLD || latest_smoke > SMOKE_THRESHOLD) {
            need_blink = 1;
            LOGD("[LED] 触发闪烁 (T=%.1f, Smoke=%.1f)", latest_temp, latest_smoke);
        } else {
            need_blink = 0;
        }

        // 调用 LED 控制（非阻塞）
        led_control(need_blink, &last_led_toggle, &led_on_off);

        if (now != last_log_time) {
            LOGD("[SYS] 状态=%s",
                 last_state ? "有人" : "无人");
            last_log_time = now;
        }
        usleep(LOOP_INTERVAL_US);
    }
    led_cleanup();

    return NULL;
}
