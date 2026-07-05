#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/timerfd.h>
#include <gpiod.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <stdint.h>

#include "aht20.h"
#include "queue.h"
#include "log.h"

#define LOG_MODULE "EPOLL"

#define GPIO_CHIP       "gpiochip3"
#define SR501_OFFSET    3
#define MQ_RAW_PATH     "/sys/bus/iio/devices/iio:device0/in_voltage6_raw"

#define MAX_EVENTS      4

queue_t g_queue;

/* 日志等级 */
int g_log_level = LOG_LEVEL_DEBUG;

void* process_thread(void* arg);

int main() {

    LOG_INFO_M(LOG_MODULE, "系统启动");

    struct gpiod_chip *chip;
    struct gpiod_line *line;
    struct gpiod_line_event event;

    int epoll_fd, mq_fd;
    struct epoll_event ev, events[MAX_EVENTS];
    char buf[64];

    /* ===== 初始化队列 ===== */
    queue_init(&g_queue);

    /* ===== 启动处理线程 ===== */
    pthread_t process_tid;
    pthread_create(&process_tid, NULL, process_thread, NULL);

    /* ===== 打开 AHT20 ===== */
    int aht_fd = aht20_open();
    if (aht_fd < 0) {
        LOG_ERROR_M(LOG_MODULE, "AHT20打开失败");
        return 1;
    }

    /* ===== 创建 AHT20 timerfd ===== */
    int aht_tfd = timerfd_create(CLOCK_MONOTONIC, 0);
    if (aht_tfd < 0) {
        LOG_ERROR_M(LOG_MODULE, "AHT20 timerfd创建失败");
        return 1;
    }

    struct itimerspec aht_ts = {
        .it_interval = {2, 0},   // 2秒
        .it_value    = {1, 0}
    };
    timerfd_settime(aht_tfd, 0, &aht_ts, NULL);

    /* ===== 创建 MQ timerfd ===== */
    int mq_tfd = timerfd_create(CLOCK_MONOTONIC, 0);
    if (mq_tfd < 0) {
        LOG_ERROR_M(LOG_MODULE, "MQ timerfd创建失败");
        return 1;
    }

    struct itimerspec mq_ts = {
        .it_interval = {0, 500000000}, // ⭐ 500ms
        .it_value    = {0, 500000000}
    };
    timerfd_settime(mq_tfd, 0, &mq_ts, NULL);

    /* ===== GPIO 初始化 ===== */
    chip = gpiod_chip_open_by_name(GPIO_CHIP);
    if (!chip) {
        LOG_ERROR_M(LOG_MODULE, "GPIO chip打开失败");
        return 1;
    }

    line = gpiod_chip_get_line(chip, SR501_OFFSET);
    if (!line) {
        LOG_ERROR_M(LOG_MODULE, "GPIO line获取失败");
        return 1;
    }

    if (gpiod_line_request_rising_edge_events(line, "sr501") < 0) {
        LOG_ERROR_M(LOG_MODULE, "GPIO事件请求失败");
        return 1;
    }

    int gpio_fd = gpiod_line_event_get_fd(line);

    /* ===== MQ 初始化 ===== */
    mq_fd = open(MQ_RAW_PATH, O_RDONLY);
    if (mq_fd < 0) {
        LOG_ERROR_M(LOG_MODULE, "MQ打开失败");
        return 1;
    }

    /* ===== epoll 初始化 ===== */
    epoll_fd = epoll_create1(0);
    if (epoll_fd < 0) {
        LOG_ERROR_M(LOG_MODULE, "epoll创建失败");
        return 1;
    }

    /* ===== 注册 GPIO ===== */
    ev.events = EPOLLIN;
    ev.data.fd = gpio_fd;
    epoll_ctl(epoll_fd, EPOLL_CTL_ADD, gpio_fd, &ev);

    /* ===== 注册 AHT20 timer ===== */
    ev.events = EPOLLIN;
    ev.data.fd = aht_tfd;
    epoll_ctl(epoll_fd, EPOLL_CTL_ADD, aht_tfd, &ev);

    /* ===== 注册 MQ timer ===== */
    ev.events = EPOLLIN;
    ev.data.fd = mq_tfd;
    epoll_ctl(epoll_fd, EPOLL_CTL_ADD, mq_tfd, &ev);

    LOG_INFO_M(LOG_MODULE, "系统运行中");

    int last_mq_val = -1;
    time_t last_timeout_log = 0;

    while (1) {

        int n = epoll_wait(epoll_fd, events, MAX_EVENTS, 500);

        if (n < 0) {
            if (errno == EINTR) continue;
            LOG_ERROR_M(LOG_MODULE, "epoll_wait错误");
            break;
        }

        /* ===== timeout ===== */
        if (n == 0) {
            time_t now = time(NULL);
            if (now != last_timeout_log) {
                LOG_DEBUG_M(LOG_MODULE, "epoll timeout");
                last_timeout_log = now;
            }
        }

        for (int i = 0; i < n; i++) {

            /* ================= PIR ================= */
            if (events[i].data.fd == gpio_fd) {

                if (gpiod_line_event_read(line, &event) == 0) {

                    if (event.event_type == GPIOD_LINE_EVENT_RISING_EDGE) {

                        sensor_packet_t pkt;

                        pkt.type = SENSOR_MOTION;
                        pkt.ts = time(NULL);
                        pkt.data.motion.detected = 1;

                        push_queue(&g_queue, pkt);

                        LOG_DEBUG_M(LOG_MODULE, "PIR触发");
                    }
                }
            }

            /* ================= AHT20 ================= */
            else if (events[i].data.fd == aht_tfd) {

                uint64_t exp;
                read(aht_tfd, &exp, sizeof(exp));

                float t, h;

                if (aht20_read_once(aht_fd, &t, &h) == 0) {

                    sensor_packet_t pkt;

                    pkt.type = SENSOR_AHT20;
                    pkt.ts = time(NULL);
                    pkt.data.aht20.temperature = t;
                    pkt.data.aht20.humidity = h;

                    push_queue(&g_queue, pkt);

                    LOG_DEBUG_M(LOG_MODULE,
                        "AHT20采集 T=%.1f H=%.1f", t, h);
                }
                else {
                    LOG_WARN_M(LOG_MODULE, "AHT20读取失败");
                }
            }

            /* ================= MQ ================= */
            else if (events[i].data.fd == mq_tfd) {

                uint64_t exp;
                read(mq_tfd, &exp, sizeof(exp)); // ⭐ 必须读

                lseek(mq_fd, 0, SEEK_SET);
                int len = read(mq_fd, buf, sizeof(buf) - 1);

                if (len > 0) {

                    buf[len] = '\0';
                    int raw_val = atoi(buf);

                    if (abs(raw_val - last_mq_val) > 10) {

                        sensor_packet_t pkt;

                        pkt.type = SENSOR_MQ;
                        pkt.ts = time(NULL);
                        pkt.data.mq.raw = raw_val;

                        push_queue(&g_queue, pkt);

                        LOG_DEBUG_M(LOG_MODULE, "MQ=%d", raw_val);

                        last_mq_val = raw_val;
                    }
                }
            }
        }
    }

    return 0;
}
