#ifndef LOG_H
#define LOG_H

#include <stdio.h>
#include <time.h>
#include <stdarg.h>

/* ===== 日志等级 ===== */
#define LOG_LEVEL_DEBUG 0
#define LOG_LEVEL_INFO  1
#define LOG_LEVEL_WARN  2
#define LOG_LEVEL_ERROR 3

/* ===== 全局日志等级 ===== */
extern int g_log_level;

/* ===== 内部函数 ===== */
static inline void log_print(int level, const char *level_str,
                             const char *module,
                             const char *fmt, ...) {

    if (level < g_log_level)
        return;

    time_t t = time(NULL);
    struct tm *tm = localtime(&t);

    char buf[32];
    strftime(buf, sizeof(buf), "%H:%M:%S", tm);

    printf("[%s] [%s] [%s] ", buf, level_str, module);

    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);

    printf("\n");
}

/* ===== 默认模块 SYS ===== */
#define LOG_DEBUG(fmt, ...) \
    log_print(LOG_LEVEL_DEBUG, "DEBUG", "SYS", fmt, ##__VA_ARGS__)

#define LOG_INFO(fmt, ...) \
    log_print(LOG_LEVEL_INFO, "INFO ", "SYS", fmt, ##__VA_ARGS__)

#define LOG_WARN(fmt, ...) \
    log_print(LOG_LEVEL_WARN, "WARN ", "SYS", fmt, ##__VA_ARGS__)

#define LOG_ERROR(fmt, ...) \
    log_print(LOG_LEVEL_ERROR, "ERROR", "SYS", fmt, ##__VA_ARGS__)

/* ===== 模块日志（🔥推荐用这个） ===== */
#define LOG_DEBUG_M(module, fmt, ...) \
    log_print(LOG_LEVEL_DEBUG, "DEBUG", module, fmt, ##__VA_ARGS__)

#define LOG_INFO_M(module, fmt, ...) \
    log_print(LOG_LEVEL_INFO, "INFO ", module, fmt, ##__VA_ARGS__)

#define LOG_WARN_M(module, fmt, ...) \
    log_print(LOG_LEVEL_WARN, "WARN ", module, fmt, ##__VA_ARGS__)

#define LOG_ERROR_M(module, fmt, ...) \
    log_print(LOG_LEVEL_ERROR, "ERROR", module, fmt, ##__VA_ARGS__)

/* ===== 兼容旧接口 ===== */
#define LOGD(fmt, ...) LOG_DEBUG(fmt, ##__VA_ARGS__)
#define LOGI(fmt, ...) LOG_INFO(fmt, ##__VA_ARGS__)
#define LOGW(fmt, ...) LOG_WARN(fmt, ##__VA_ARGS__)
#define LOGE(fmt, ...) LOG_ERROR(fmt, ##__VA_ARGS__)

#endif
