#ifndef QUEUE_H
#define QUEUE_H

#include <pthread.h>
#include <time.h>

/* ===== 队列大小 ===== */
#define QUEUE_SIZE 64

/* ===== 传感器类型定义 ===== */
typedef enum {
    SENSOR_MOTION = 0,
    SENSOR_MQ,
    SENSOR_DHT11,
    SENSOR_AHT20
} sensor_type_t;

/* ===== 通用数据包 ===== */
typedef struct {

    sensor_type_t type;   // 数据类型
    time_t ts;            // 时间戳

    union {

        /* PIR */
        struct {
            int detected;   // 0/1
        } motion;

        /* MQ */
        struct {
            int raw;
        } mq;

        /* DHT11 */
        struct {
            float temperature;
            float humidity;
        } dht11;

        /* AHT20 */
        struct {
            float temperature;
            float humidity;
        } aht20;

    } data;

} sensor_packet_t;

/* ===== 队列结构 ===== */
typedef struct {

    sensor_packet_t buffer[QUEUE_SIZE];

    int head;
    int tail;

    pthread_mutex_t mutex;
    pthread_cond_t cond;

} queue_t;

/* ===== 接口 ===== */

/* 初始化 */
void queue_init(queue_t *q);

/* 入队（生产者） */
void push_queue(queue_t *q, sensor_packet_t pkt);

/* 出队（消费者，阻塞） */
int pop_queue(queue_t *q, sensor_packet_t *pkt);

/* 非阻塞出队（可选） */
int try_pop_queue(queue_t *q, sensor_packet_t *pkt);

#endif

