#include <stdio.h>
#include <string.h>
#include "MQTTClient.h"

/* ===== MQTT 配置 ===== */
/* 修改为你电脑的 IP 地址, 本机测试用 localhost */
#define ADDRESS     "tcp://localhost:1883"
#define CLIENTID    "elf2_sensor_client"

static MQTTClient client;

int mqtt_init(void)
{
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;

    MQTTClient_create(&client, ADDRESS, CLIENTID,
                      MQTTCLIENT_PERSISTENCE_NONE, NULL);

    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;

    int rc = MQTTClient_connect(client, &conn_opts);
    if (rc != MQTTCLIENT_SUCCESS) {
        printf("MQTT连接失败: %d\n", rc);
        printf("请检查:\n");
        printf("  1. Mosquitto 是否已启动\n");
        printf("  2. IP地址是否正确: %s\n", ADDRESS);
        printf("  3. 防火墙是否放行 1883 端口\n");
        return -1;
    }

    printf("MQTT连接成功: %s\n", ADDRESS);
    return 0;
}

int mqtt_publish(const char *topic, const char *payload)
{
    MQTTClient_message msg = MQTTClient_message_initializer;
    msg.payload = (void*)payload;
    msg.payloadlen = strlen(payload);
    msg.qos = 0;
    msg.retained = 0;

    MQTTClient_deliveryToken token;
    MQTTClient_publishMessage(client, topic, &msg, &token);
    MQTTClient_waitForCompletion(client, token, 1000);

    return 0;
}
