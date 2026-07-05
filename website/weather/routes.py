from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from weather.service import get_current_weather, get_forecast_weather
from extensions import db

weather_bp = Blueprint('weather', __name__, url_prefix='/weather')


def _get_location():
    """获取当前用户的天气城市, 优先用用户设置, 兜底用配置."""
    if current_user.is_authenticated and current_user.weather_location:
        return current_user.weather_location
    return current_app.config.get('SENIVERSE_LOCATION', 'xian')


def _make_config(location=None):
    """构造 weather service 需要的 config dict."""
    loc = location or _get_location()
    return {
        'SENIVERSE_API_KEY': current_app.config.get('SENIVERSE_API_KEY', ''),
        'SENIVERSE_LOCATION': loc,
    }


@weather_bp.route('/api/current')
@login_required
def current():
    data = get_current_weather(_make_config())
    if data:
        return jsonify(data)
    return jsonify({'error': '无法获取天气数据'}), 503


@weather_bp.route('/api/forecast')
@login_required
def forecast():
    data = get_forecast_weather(_make_config())
    if data:
        return jsonify(data)
    return jsonify({'error': '无法获取天气预报数据'}), 503


@weather_bp.route('/api/location', methods=['GET'])
@login_required
def get_location():
    return jsonify({'location': _get_location()})


@weather_bp.route('/api/location', methods=['POST'])
@login_required
def set_location():
    data = request.get_json()
    if not data or 'location' not in data:
        return jsonify({'error': '缺少 location 参数'}), 400

    loc = data['location'].strip()
    if not loc:
        return jsonify({'error': '城市名不能为空'}), 400

    current_user.weather_location = loc
    db.session.commit()

    # 立即返回新天气数据
    weather = get_current_weather(_make_config(loc))
    return jsonify({'location': loc, 'weather': weather, 'message': f'已切换到 {loc}'})
