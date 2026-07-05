# IoT 智能家居 - 传感器代码 Makefile
#
# 依赖:
#   sudo apt-get install libmosquitto-dev libgpiod-dev libpaho-mqtt-dev
#
# 编译:
#   make
#
# 运行 (需要 root 权限, 因为 GPIO 和实时调度):
#   sudo ./sensor_app

CC = gcc
CFLAGS = -Wall -Wextra -O2 -I.
LDFLAGS = -lpaho-mqtt3c -lgpiod -lpthread -lm

TARGET = sensor_app
SRCS = epoll_queue.c process.c queue.c aht20.c mqtt_client.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean run install-deps

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)

run: $(TARGET)
	sudo ./$(TARGET)

# 安装依赖 (Debian/Ubuntu/Raspberry Pi OS / OpenEuler)
install-deps:
	@echo "正在安装依赖..."
	@echo ""
	@echo "Debian/Ubuntu/Raspberry Pi OS:"
	@echo "  sudo apt-get update"
	@echo "  sudo apt-get install -y libgpiod-dev libpaho-mqtt-dev"
	@echo ""
	@echo "OpenEuler/CentOS:"
	@echo "  sudo yum install -y gpiod-devel paho-c-devel"
	@echo ""
	@echo "如果 libpaho-mqtt 不在包管理器中, 需要手动编译:"
	@echo "  git clone https://github.com/eclipse/paho.mqtt.c.git"
	@echo "  cd paho.mqtt.c && make && sudo make install"
	@echo "  sudo ldconfig"

# 依赖关系
epoll_queue.o: epoll_queue.c aht20.h queue.h log.h
process.o: process.c mqtt_client.h queue.h log.h
queue.o: queue.c queue.h log.h
aht20.o: aht20.c aht20.h queue.h log.h
mqtt_client.o: mqtt_client.c mqtt_client.h
