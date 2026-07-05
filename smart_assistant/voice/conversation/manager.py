# voice/conversation/manager.py

from collections import deque
from voice.llm.prompt import SYSTEM_PROMPT


class ConversationManager:

    def __init__(self, max_turns=8):

        # 保存历史（user + assistant）
        self.history = deque(maxlen=max_turns * 2)

        # system prompt 永远在最前
        self.system = {
            "role": "system",
            "content": SYSTEM_PROMPT
        }

    # ----------------------------

    def add_user(self, text: str):
        """加入用户输入"""
        self.history.append({
            "role": "user",
            "content": text
        })

    # ----------------------------

    def add_assistant(self, text: str):
        """加入助手回复"""
        self.history.append({
            "role": "assistant",
            "content": text
        })

    # ----------------------------

    def build_messages(self):
        """构造给LLM的完整上下文"""

        messages = [self.system]
        messages.extend(list(self.history))

        return messages

    # ----------------------------

    def clear(self):
        """清空历史"""
        self.history.clear()

    # ----------------------------

    def get_history(self):
        return list(self.history)
