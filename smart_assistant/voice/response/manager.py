from .console_sender import ConsoleSender


class ResponseManager:

    def __init__(self):

        self.senders = []

        # 当前只有控制台输出
        self.senders.append(ConsoleSender())

    def send(self, reply):

        if not reply:
            return

        for sender in self.senders:
            sender.send(reply)
