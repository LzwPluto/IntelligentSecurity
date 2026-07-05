#ifndef _AHT20_H_
#define _AHT20_H_

int aht20_open(void);
int aht20_read_once(int fd, float *temp, float *hum);

#endif

