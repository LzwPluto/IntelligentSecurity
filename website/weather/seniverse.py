import time
import requests


class SeniverseWeather:
    """心知天气 API client with caching."""

    BASE_URL = 'https://api.seniverse.com/v3'

    def __init__(self, api_key, location='shanghai'):
        self.api_key = api_key
        self.location = location
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 900  # 15 minutes

    def _is_cached(self, key):
        if key in self._cache and key in self._cache_time:
            if time.time() - self._cache_time[key] < self._cache_ttl:
                return True
        return False

    def _get(self, endpoint, params=None):
        if params is None:
            params = {}
        params['key'] = self.api_key
        params['location'] = self.location
        params['language'] = 'zh-Hans'
        params['unit'] = 'c'

        cache_key = f'{endpoint}:{str(params)}'
        if self._is_cached(cache_key):
            return self._cache[cache_key]

        try:
            resp = requests.get(f'{self.BASE_URL}/{endpoint}', params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = data
            self._cache_time[cache_key] = time.time()
            return data
        except Exception as e:
            print(f'[Seniverse] API error: {e}')
            return None

    def get_current(self):
        """Get current weather conditions."""
        data = self._get('weather/now.json')
        if not data or 'results' not in data:
            return None
        now = data['results'][0]
        n = now['now']
        return {
            'location': now['location']['name'],
            'text': n.get('text', ''),
            'code': n.get('code', ''),
            'temperature': n.get('temperature', ''),
            'humidity': n.get('humidity', '--'),
            'wind_speed': n.get('wind_speed', '--'),
            'wind_direction': n.get('wind_direction', ''),
            'updated': now.get('last_update', '')
        }

    def get_forecast(self, days=3):
        """Get daily weather forecast."""
        data = self._get('weather/daily.json', {'days': str(days)})
        if not data or 'results' not in data:
            return None
        results = data['results'][0]
        forecast = []
        for day in results['daily']:
            forecast.append({
                'date': day.get('date', ''),
                'text_day': day.get('text_day', ''),
                'text_night': day.get('text_night', ''),
                'high': day.get('high', ''),
                'low': day.get('low', ''),
                'humidity': day.get('humidity', ''),
                'wind_direction': day.get('wind_direction', ''),
                'wind_scale': day.get('wind_scale', ''),
            })
        return {
            'location': results['location']['name'],
            'forecast': forecast
        }


# Weather code to icon mapping
WEATHER_ICONS = {
    '0': 'bi-sun',           # 晴
    '1': 'bi-sun',           # 晴
    '2': 'bi-sun',           # 晴
    '3': 'bi-cloud-sun',     # 多云
    '4': 'bi-clouds',        # 阴
    '5': 'bi-cloud-drizzle', # 小雨
    '6': 'bi-cloud-rain',    # 中雨
    '7': 'bi-cloud-rain-heavy', # 大雨
    '8': 'bi-cloud-rain-heavy', # 暴雨
    '9': 'bi-cloud-snow',    # 雪
    '10': 'bi-cloud-rain',   # 阵雨
    '11': 'bi-cloud-lightning', # 雷阵雨
    '13': 'bi-cloud-snow',   # 雪
    '14': 'bi-cloud-snow',   # 小雪
    '15': 'bi-cloud-snow',   # 中雪
    '16': 'bi-cloud-snow',   # 大雪
    '17': 'bi-cloud-snow',   # 暴雪
    '18': 'bi-cloud-fog2',   # 雾
    '19': 'bi-cloud-haze2',  # 霾
    '20': 'bi-wind',         # 沙尘暴
}


def get_weather_icon(code):
    return WEATHER_ICONS.get(str(code), 'bi-cloud')
