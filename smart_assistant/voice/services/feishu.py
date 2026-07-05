import json
import time
import uuid

import requests

from .base import BaseService


class FeishuService(BaseService):

    def __init__(self, app_id, app_secret, chat_id):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self._token = None
        self._token_expires_at = 0
        self._refresh_token()

    def _refresh_token(self):
        url = (
            "https://open.feishu.cn"
            "/open-apis/auth/v3/tenant_access_token/internal"
        )
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        headers = {"Content-Type": "application/json; charset=utf-8"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                self._token = data.get("tenant_access_token")
                self._token_expires_at = time.time() + data.get("expire", 7200) - 300
                print("[Feishu] Token refreshed.")
            else:
                print(f"[Feishu] Token refresh failed: {data}")
        except Exception as e:
            print(f"[Feishu] Token request error: {e}")

    def _ensure_token(self):
        if self._token is None or time.time() >= self._token_expires_at:
            self._refresh_token()
        return self._token is not None

    def execute(self, params):
        action = params.get("action", "send_message")
        content = params.get("content", "")
        title = params.get("title", "")

        if action == "send_message":
            return self.send_text(content)
        elif action == "send_alert":
            return self.send_alert(title, content)
        else:
            return self.send_text(content)

    def send_text(self, text):
        if not text:
            return
        if not self._ensure_token():
            print("[Feishu] No valid token, cannot send message.")
            return

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        params = {"receive_id_type": "chat_id"}

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
            "uuid": str(uuid.uuid4()),
        }

        try:
            resp = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                print(f"[Feishu] Message sent: {text[:50]}...")
            else:
                print(f"[Feishu] Send failed: {data}")
        except Exception as e:
            print(f"[Feishu] Send error: {e}")

    def send_alert(self, title, content, level="warning"):
        if not self._ensure_token():
            print("[Feishu] No valid token, cannot send alert.")
            return

        color_map = {
            "info": "blue",
            "warning": "yellow",
            "danger": "red",
        }
        color = color_map.get(level, "red")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                        + f"\n\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    },
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "Smart Assistant Auto Alert",
                        }
                    ],
                },
            ],
        }

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        params = {"receive_id_type": "chat_id"}

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card),
            "uuid": str(uuid.uuid4()),
        }

        try:
            resp = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                print(f"[Feishu] Alert sent: {title}")
            else:
                print(f"[Feishu] Alert failed: {data}")
        except Exception as e:
            print(f"[Feishu] Alert error: {e}")
