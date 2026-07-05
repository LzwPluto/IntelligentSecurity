#ifndef LED_CONTROL_H
#define LED_CONTROL_H

#include <gpiod.h>
#include <time.h>

/* 初始化 LED GPIO（返回 0 成功，-1 失败） */
int led_init(const char *chip_path, unsigned int line_offset);

/* 释放 GPIO 并熄灭 LED */
void led_cleanup(void);

/* 非阻塞 LED 控制
 * enable: 1-闪烁模式开启，0-熄灭
 * last_toggle: 传入上次切换的时间戳（由调用者维护）
 * led_state: 传入当前 LED 状态指针（0灭/1亮），函数会更新它
 */
void led_control(int enable, struct timespec *last_toggle, int *led_state);

/* 设置闪烁间隔（单位毫秒），默认 200ms */
void led_set_blink_interval_ms(int interval_ms);

#endif
