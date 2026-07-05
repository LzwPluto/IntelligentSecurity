from openai import OpenAI

from .prompt import SYSTEM_PROMPT


class DeepSeekClient:

    def __init__(
        self,
        api_key,
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
    ):

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        self.model = model

    def chat(self, messages, json_mode=True):

        if isinstance(messages, str):
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": messages,
                },
            ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)

        return response.choices[0].message.content
