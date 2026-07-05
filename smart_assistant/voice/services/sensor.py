import json

from .base import BaseService
from .sensor_data import get_recent_data
from ..llm.api_client import DeepSeekClient
from config import API_KEY, MODEL

SENSOR_ANALYSIS_SYSTEM_PROMPT = """You are a sensor data analysis expert. Based on real-time sensor data, describe the current environmental conditions in concise, natural English.

CRITICAL: You MUST reply in English ONLY. Never output Chinese characters or any other language. This is a strict requirement for the TTS system which only supports English.

Analysis points:
1. Whether the temperature is comfortable (18-26 C is comfortable)
2. Whether the humidity is appropriate (40-60% is ideal)
3. Whether smoke/gas levels are safe
4. Whether there is human activity
5. Overall environmental assessment

Requirements:
- Reply concisely, suitable for voice broadcast
- If some sensors have no data, only analyze available data
- If no data at all, tell the user sensors are not connected
- Do not output Markdown or JSON
- ENGLISH ONLY"""


class SensorService(BaseService):

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = DeepSeekClient(api_key=API_KEY, model=MODEL)
        return self._client

    def execute(self, params):

        print("\n========== Sensor Analysis ==========")

        sensor_data = get_recent_data()

        if not sensor_data:
            print("No sensor data available")
            print("======================================\n")
            return "No sensor data available. Please check if the sensors are working properly."

        data_str = json.dumps(sensor_data, ensure_ascii=False)
        print(f"Sensor data: {data_str}")

        query = params.get("query", "")

        user_content = f"Sensor data:\n{data_str}"
        if query:
            user_content += f"\n\nUser is asking about: {query}"
        user_content += "\n\nPlease analyze the current environment. Reply in English only."

        messages = [
            {"role": "system", "content": SENSOR_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        client = self._get_client()
        analysis = client.chat(messages, json_mode=False)

        print(analysis)
        print("======================================\n")

        return analysis
