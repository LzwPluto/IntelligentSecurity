#include "queue.h"
#include "log.h"

#define LOG_MODULE "QUEUE"

/* 判空 */
static int queue_is_empty(queue_t *q) {
    return q->head == q->tail;
}

/* 判满 */
static int queue_is_full(queue_t *q) {
    return ((q->tail + 1) % QUEUE_SIZE) == q->head;
}

/* ===== 初始化 ===== */
void queue_init(queue_t *q) {

    q->head = 0;
    q->tail = 0;

    pthread_mutex_init(&q->mutex, NULL);
    pthread_cond_init(&q->cond, NULL);

    LOG_INFO_M(LOG_MODULE, "队列初始化完成");
}

/* ===== 入队 ===== */
void push_queue(queue_t *q, sensor_packet_t pkt) {

    pthread_mutex_lock(&q->mutex);

    if (queue_is_full(q)) {

        LOG_WARN_M(LOG_MODULE, "队列已满，丢弃 type=%d", pkt.type);

    } else {

        q->buffer[q->tail] = pkt;
        q->tail = (q->tail + 1) % QUEUE_SIZE;

        pthread_cond_signal(&q->cond);
    }

    pthread_mutex_unlock(&q->mutex);
}

/* ===== 阻塞出队 ===== */
int pop_queue(queue_t *q, sensor_packet_t *pkt) {

    pthread_mutex_lock(&q->mutex);

    while (queue_is_empty(q)) {
        LOG_DEBUG_M(LOG_MODULE, "队列为空，阻塞等待");
        pthread_cond_wait(&q->cond, &q->mutex);
    }

    *pkt = q->buffer[q->head];
    q->head = (q->head + 1) % QUEUE_SIZE;

    pthread_mutex_unlock(&q->mutex);

    return 1;
}

/* ===== 非阻塞出队 ===== */
int try_pop_queue(queue_t *q, sensor_packet_t *pkt) {

    int ret = 0;

    pthread_mutex_lock(&q->mutex);

    if (!queue_is_empty(q)) {

        *pkt = q->buffer[q->head];
        q->head = (q->head + 1) % QUEUE_SIZE;

        ret = 1;

    } else {
        ret = 0;
    }

    pthread_mutex_unlock(&q->mutex);

    return ret;
}
