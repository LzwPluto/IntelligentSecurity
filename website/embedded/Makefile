# IoT 智能家居 - 嵌入式 MQTT 传感器客户端 Makefile
#
# 依赖:
#   sudo apt-get install libmosquitto-dev wiringpi
#
# 编译:
#   make
#
# 运行:
#   make run
#   或: ./mqtt_sensor

CC = gcc
CFLAGS = -Wall -Wextra -O2
LDFLAGS = -lmosquitto -lpthread

# 如果使用 wiringPi, 取消下面的注释
# LDFLAGS += -lwiringPi

TARGET = mqtt_sensor
SRC = mqtt_sensor.c

.PHONY: all clean run install-deps

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

# 安装依赖 (Debian/Ubuntu/Raspberry Pi OS)
install-deps:
	sudo apt-get update
	sudo apt-get install -y libmosquitto-dev
	# 如果是树莓派, 取消下面的注释
	# sudo apt-get install -y wiringpi
