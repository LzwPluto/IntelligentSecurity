import threading
import time

import requests

from .base import BaseService

CACHE_TTL_SEC = 1800
MORNING_HOUR = 7
MORNING_MINUTE = 0


class WeatherService(BaseService):

    def __init__(self, api_key, default_city="beijing"):
        self.api_key = api_key
        self.default_city = default_city
        self.base_url = "https://api.seniverse.com/v3/weather/daily.json"
        self._cache = None
        self._cache_time = 0
        self._lock = threading.Lock()

        self._scheduler_thread = None
        self._scheduler_running = False
        self._tts_callback = None
        self._feishu_alert = None
        self._llm_chat = None

    def execute(self, params):
        city = params.get("city", self.default_city)
        return self._get_weather_analysis(city, "en")

    def set_llm(self, chat_func):
        self._llm_chat = chat_func

    def start_scheduler(self, tts_callback=None, feishu_alert=None):
        self._tts_callback = tts_callback
        self._feishu_alert = feishu_alert
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self._scheduler_thread.start()
        print(
            f"[Weather] Morning report scheduled at "
            f"{MORNING_HOUR:02d}:{MORNING_MINUTE:02d} daily."
        )

    def stop_scheduler(self):
        self._scheduler_running = False

    def _scheduler_loop(self):
        last_report_date = None
        while self._scheduler_running:
            now = time.localtime()
            today = now.tm_yday
            if (
                today != last_report_date
                and now.tm_hour >= MORNING_HOUR
                and now.tm_min >= MORNING_MINUTE
            ):
                last_report_date = today
                self._do_morning_report()
            time.sleep(30)

    def _do_morning_report(self):
        print("[Weather] Generating morning report...")
        data = self._fetch_weather(self.default_city)
        if not data:
            return

        en_analysis = self._build_analysis(data, "en")
        zh_analysis = self._build_analysis(data, "zh")

        if en_analysis and self._tts_callback:
            self._tts_callback(en_analysis)
        if zh_analysis and self._feishu_alert:
            self._feishu_alert("Daily Weather Report", zh_analysis, "info")

    def _get_weather_analysis(self, city, language="en"):
        data = self._fetch_weather(city)
        if not data:
            return None
        return self._build_analysis(data, language)

    def _build_analysis(self, data, language):
        weather_text = self._format_weather(data, language)
        if not self._llm_chat:
            return weather_text
        return self._analyze_with_llm(weather_text, language)

    def _fetch_weather(self, city):
        with self._lock:
            now = time.time()
            cache_key = city.lower()
            if (
                self._cache
                and self._cache.get("_key") == cache_key
                and (now - self._cache_time) < CACHE_TTL_SEC
            ):
                print(f"[Weather] Using cached data for {city}")
                return self._cache

        params = {
            "key": self.api_key,
            "location": city,
            "language": "zh-Hans",
            "unit": "c",
            "start": 0,
            "days": 3,
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "results" not in data or not data["results"]:
                print(f"[Weather] No results for {city}")
                return None

            with self._lock:
                data["_key"] = cache_key
                self._cache = data
                self._cache_time = now

            print(f"[Weather] Fetched data for {city}")
            return data
        except Exception as e:
            print(f"[Weather] API error: {e}")
            return None

    def _format_weather(self, data, language="zh"):
        result = data["results"][0]
        loc = result["location"]["name"]
        daily = result["daily"]

        if language == "en":
            lines = [f"Location: {loc} | Weather Forecast:"]
            for day in daily:
                date = day["date"]
                text_day = day["text_day"]
                text_night = day.get("text_night", "")
                high = day["high"]
                low = day["low"]
                humidity = day.get("humidity", "")
                wind = day.get("wind_direction", "")
                wind_scale = day.get("wind_scale", "")
                line = (
                    f"{date}: Day {text_day}, Night {text_night}, "
                    f"{low} to {high} C"
                )
                if humidity:
                    line += f", Humidity {humidity}%"
                if wind:
                    line += f", {wind} {wind_scale}"
                lines.append(line)
        else:
            lines = [f"{loc} 天气预报："]
            for day in daily:
                date = day["date"]
                text_day = day["text_day"]
                text_night = day.get("text_night", "")
                high = day["high"]
                low = day["low"]
                humidity = day.get("humidity", "")
                wind = day.get("wind_direction", "")
                wind_scale = day.get("wind_scale", "")
                line = (
                    f"{date}：白天{text_day}，夜间{text_night}，"
                    f"气温{low}°C ~ {high}°C"
                )
                if humidity:
                    line += f"，湿度{humidity}%"
                if wind:
                    line += f"，{wind} {wind_scale}级"
                lines.append(line)

        return "\n".join(lines)

    def _analyze_with_llm(self, weather_text, language="zh"):
        if not self._llm_chat:
            return weather_text

        if language == "en":
            system_prompt = (
                "You are a weather forecaster. Based on the data below, "
                "give a short spoken summary.\n\n"
                "Requirements:\n"
                "- Very short, under 60 words, suitable for TTS voice\n"
                "- Include: today's weather, temperature range, "
                "one key advice (umbrella / coat / sunscreen etc.)\n"
                "- Speak naturally in English\n"
                "- Do NOT output Markdown or JSON"
            )
            user_prompt = (
                f"Weather data:\n{weather_text}\n\n"
                "Give a short spoken weather briefing."
            )
        else:
            system_prompt = (
                "You are a weather forecaster. Based on the data below, "
                "give a concise and comprehensive analysis in Chinese.\n\n"
                "Analysis points:\n"
                "1. Today's weather summary\n"
                "2. Clothing advice\n"
                "3. Travel advice\n"
                "4. Special notes\n\n"
                "Requirements:\n"
                "- Comprehensive but concise, suitable for reading in Feishu\n"
                "- Analyze all available days\n"
                "- Plain text, no Markdown or JSON"
            )
            user_prompt = (
                f"Weather data:\n{weather_text}\n\n"
                "Please analyze and provide advice."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            return self._llm_chat(messages)
        except Exception as e:
            print(f"[Weather] LLM analysis failed: {e}")
            return weather_text
