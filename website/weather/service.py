"""Weather service with Seniverse API + wttr.in free fallback."""

import logging
import requests
from weather.seniverse import SeniverseWeather

logger = logging.getLogger('weather.service')


def _get_wttr_current(location):
    """Get current weather from wttr.in (free, no API key needed)."""
    try:
        # Map Chinese city names to English for wttr.in
        city_map = {
            'shanghai': 'Shanghai', 'beijing': 'Beijing',
            'guangzhou': 'Guangzhou', 'shenzhen': 'Shenzhen',
            'hangzhou': 'Hangzhou', 'nanjing': 'Nanjing',
            'chengdu': 'Chengdu', 'wuhan': 'Wuhan',
        }
        city = city_map.get(location.lower(), location)
        resp = requests.get(f'https://wttr.in/{city}?format=j1', timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data['current_condition'][0]
        return {
            'location': city,
            'text': current.get('lang_zh', [{}])[0].get('value',
                   current.get('weatherDesc', [{}])[0].get('value', '未知')),
            'code': '0',
            'temperature': current.get('temp_C', '0'),
            'humidity': current.get('humidity', '0'),
            'wind_speed': current.get('windspeedKmph', '0'),
            'wind_direction': current.get('winddir16Point', ''),
            'updated': '',
        }
    except Exception as e:
        logger.warning(f'[Weather] wttr.in current failed: {e}')
        return None


def _get_wttr_forecast(location, days=3):
    """Get weather forecast from wttr.in (free, no API key needed)."""
    try:
        city_map = {
            'shanghai': 'Shanghai', 'beijing': 'Beijing',
            'guangzhou': 'Guangzhou', 'shenzhen': 'Shenzhen',
            'hangzhou': 'Hangzhou', 'nanjing': 'Nanjing',
            'chengdu': 'Chengdu', 'wuhan': 'Wuhan',
        }
        city = city_map.get(location.lower(), location)
        resp = requests.get(f'https://wttr.in/{city}?format=j1', timeout=10)
        resp.raise_for_status()
        data = resp.json()
        forecast = []
        for day in data.get('weather', [])[:days]:
            forecast.append({
                'date': day.get('date', ''),
                'text_day': day.get('hourly', [{}])[4].get('lang_zh', [{}])[0].get('value',
                           day.get('hourly', [{}])[4].get('weatherDesc', [{}])[0].get('value', '')),
                'text_night': day.get('hourly', [{}])[7].get('lang_zh', [{}])[0].get('value',
                             day.get('hourly', [{}])[7].get('weatherDesc', [{}])[0].get('value', '')),
                'high': day.get('maxtempC', '0'),
                'low': day.get('mintempC', '0'),
                'humidity': day.get('hourly', [{}])[4].get('humidity', '0'),
                'wind_direction': day.get('hourly', [{}])[4].get('winddir16Point', ''),
                'wind_scale': day.get('hourly', [{}])[4].get('BeaufortScale', '0'),
            })
        return {
            'location': city,
            'forecast': forecast,
        }
    except Exception as e:
        logger.warning(f'[Weather] wttr.in forecast failed: {e}')
        return None


def get_current_weather(config):
    """Get current weather. Tries Seniverse first, falls back to wttr.in."""
    api_key = config.get('SENIVERSE_API_KEY', '')
    location = config.get('SENIVERSE_LOCATION', 'shanghai')

    # Try Seniverse if API key is configured
    if api_key and api_key != 'your_seniverse_api_key_here':
        try:
            client = SeniverseWeather(api_key=api_key, location=location)
            data = client.get_current()
            if data:
                return data
        except Exception as e:
            logger.warning(f'[Weather] Seniverse failed: {e}')

    # Fallback to wttr.in
    return _get_wttr_current(location)


def get_forecast_weather(config, days=3):
    """Get weather forecast. Tries Seniverse first, falls back to wttr.in."""
    api_key = config.get('SENIVERSE_API_KEY', '')
    location = config.get('SENIVERSE_LOCATION', 'shanghai')

    # Try Seniverse if API key is configured
    if api_key and api_key != 'your_seniverse_api_key_here':
        try:
            client = SeniverseWeather(api_key=api_key, location=location)
            data = client.get_forecast(days)
            if data:
                return data
        except Exception as e:
            logger.warning(f'[Weather] Seniverse failed: {e}')

    # Fallback to wttr.in
    return _get_wttr_forecast(location, days)
