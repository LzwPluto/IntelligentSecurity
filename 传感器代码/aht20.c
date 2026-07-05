#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <time.h>
#include <pthread.h>
#include <errno.h>
#include <string.h>

#include "aht20.h"
#include "queue.h"
#include "log.h"

#define LOG_MODULE "AHT20"

/* ===== 设备参数 ===== */
#define AHT20_DEV  "/dev/i2c-4"
#define AHT20_ADDR 0x38

#define AHT20_CMD_INIT   0xBE
#define AHT20_CMD_MEAS   0xAC
#define AHT20_CMD_RESET  0xBA

extern queue_t g_queue;

/* ===== I2C写 ===== */
static int aht20_write(int fd, uint8_t *buf, int len) {
    if (write(fd, buf, len) != len) {
        LOG_ERROR_M(LOG_MODULE, "I2C写失败");
        return -1;
    }
    return 0;
}

/* ===== I2C读 ===== */
static int aht20_read(int fd, uint8_t *buf, int len) {
    if (read(fd, buf, len) != len) {
        LOG_ERROR_M(LOG_MODULE, "I2C读失败");
        return -1;
    }
    return 0;
}

/* ===== 软复位 ===== */
static void aht20_reset(int fd) {
    uint8_t cmd = AHT20_CMD_RESET;
    write(fd, &cmd, 1);
    usleep(20000); // 20ms
}

/* ===== 初始化 ===== */
static int aht20_init(int fd) {

    uint8_t cmd[3] = {AHT20_CMD_INIT, 0x08, 0x00};

    if (aht20_write(fd, cmd, 3) < 0)
        return -1;

    usleep(10000); // 10ms

    return 0;
}

/* ===== 检查是否校准 ===== */
static int aht20_check_calibrated(int fd) {

    uint8_t status;

    if (read(fd, &status, 1) != 1) {
        LOG_ERROR_M(LOG_MODULE, "读取状态失败");
        return -1;
    }

    if (!(status & 0x08)) {
        LOG_WARN_M(LOG_MODULE, "未校准");
        return -1;
    }

    return 0;
}


/* ===== 打开设备 ===== */
int aht20_open(void) {

    int fd = open(AHT20_DEV, O_RDWR);
    if (fd < 0) {
        LOG_ERROR_M(LOG_MODULE, "打开I2C失败: %s", strerror(errno));
        return -1;
    }

    if (ioctl(fd, I2C_SLAVE, AHT20_ADDR) < 0) {
        LOG_ERROR_M(LOG_MODULE, "设置I2C地址失败");
        close(fd);
        return -1;
    }

    /* ===== 1. 软复位 ===== */
    uint8_t reset_cmd = AHT20_CMD_RESET;
    write(fd, &reset_cmd, 1);
    usleep(20000);  // 20ms

    /* ===== 2. 初始化 ===== */
    uint8_t init_cmd[3] = {AHT20_CMD_INIT, 0x08, 0x00};
    write(fd, init_cmd, 3);
    usleep(10000);

    /* ===== 3. 检查校准 ===== */
    uint8_t status;
    if (read(fd, &status, 1) != 1) {
        LOG_ERROR_M(LOG_MODULE, "读取状态失败");
        close(fd);
        return -1;
    }

    if (!(status & 0x08)) {
        LOG_ERROR_M(LOG_MODULE, "AHT20未校准！");
        close(fd);
        return -1;
    }

    LOG_INFO_M(LOG_MODULE, "AHT20初始化成功");

    return fd;
}

/* ===== 单次读取 ===== */
int aht20_read_once(int fd, float *temp, float *hum)
{
    uint8_t cmd[3] = {0xAC, 0x33, 0x00};
    uint8_t data[6];

    /* 1. 触发测量 */
    if (write(fd, cmd, 3) != 3)
        return -1;

    /* 2. 等待（必须有） */
    usleep(100000);   // ⭐ 建议100ms

    /* 3. 一次性读取6字节 */
    if (read(fd, data, 6) != 6)
        return -1;

    LOG_DEBUG_M(LOG_MODULE,
    "RAW: %02x %02x %02x %02x %02x %02x",
    data[0], data[1], data[2],
    data[3], data[4], data[5]);

    /* 4. status就在 data[0] */
    if (data[0] & 0x80)
        return -1;

    /* 5. 解析 */
    uint32_t raw_hum = (data[1] << 12) | (data[2] << 4) | (data[3] >> 4);
    uint32_t raw_temp = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5];

    *hum  = raw_hum * 100.0 / (1 << 20);
    *temp = raw_temp * 200.0 / (1 << 20) - 50;


    return 0;
}

