import paho.mqtt.publish as publish


class MQTTSender:

    def __init__(self):

        self.host = "192.168.1.100"

        self.topic = "assistant/reply"

    def send(self, reply):

        publish.single(
            self.topic,
            reply,
            hostname=self.host
        )
