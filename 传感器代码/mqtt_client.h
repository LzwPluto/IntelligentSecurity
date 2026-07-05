#ifndef _MQTT_CLIENT_H_
#define _MQTT_CLIENT_H_

int mqtt_init(void);
int mqtt_publish(const char *topic, const char *payload);

#endif

