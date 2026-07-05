#include "led_control.h"
#include <stdio.h>
#include <unistd.h>

static struct gpiod_line *led_line = NULL;
static int blink_interval_ms = 200;   // 默认 200ms

int led_init(const char *chip_path, unsigned int line_offset) {
    struct gpiod_chip *chip = gpiod_chip_open(chip_path);
    if (!chip) {
        fprintf(stderr, "[LED] 无法打开 GPIO chip %s\n", chip_path);
        return -1;
    }
    led_line = gpiod_chip_get_line(chip, line_offset);
    if (!led_line) {
        fprintf(stderr, "[LED] 无法获取 GPIO line %d\n", line_offset);
        gpiod_chip_close(chip);
        return -1;
    }
    if (gpiod_line_request_output(led_line, "sensor_led", 0) < 0) {
        fprintf(stderr, "[LED] 无法配置为输出 (可能被占用)\n");
        gpiod_chip_close(chip);
        return -1;
    }
    // 初始熄灭
    gpiod_line_set_value(led_line, 0);
    return 0;
}

void led_cleanup(void) {
    if (led_line) {
        gpiod_line_set_value(led_line, 0);
        gpiod_line_release(led_line);
        led_line = NULL;
    }
}

void led_control(int enable, struct timespec *last_toggle, int *led_state) {
    if (!led_line) return;

    if (!enable) {
        // 熄灭
        if (*led_state == 1) {
            gpiod_line_set_value(led_line, 0);
            *led_state = 0;
        }
        return;
    }

    // 闪烁模式
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);

    long diff_ms = (now.tv_sec - last_toggle->tv_sec) * 1000 +
                   (now.tv_nsec - last_toggle->tv_nsec) / 1000000;

    if (diff_ms >= blink_interval_ms) {
        *led_state = !(*led_state);
        gpiod_line_set_value(led_line, *led_state);
        *last_toggle = now;
    }
}

void led_set_blink_interval_ms(int interval_ms) {
    if (interval_ms > 0) blink_interval_ms = interval_ms;
}
