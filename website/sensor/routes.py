from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required
from database.models import SensorData
from extensions import db

sensor_bp = Blueprint('sensor', __name__, url_prefix='/sensor')


@sensor_bp.route('/api/latest')
@login_required
def latest():
    """Get the latest value for each sensor type."""
    result = {}
    for stype in ['temperature', 'humidity', 'smoke']:
        record = SensorData.query.filter_by(sensor_type=stype) \
            .order_by(SensorData.timestamp.desc()).first()
        if record:
            result[stype] = record.to_dict()
        else:
            result[stype] = {'type': stype, 'value': None, 'timestamp': None}
    return jsonify(result)


@sensor_bp.route('/api/history')
@login_required
def history():
    """Get historical sensor data for charts."""
    sensor_type = request.args.get('type', 'temperature')
    range_str = request.args.get('range', '24h')

    range_map = {
        '1h': timedelta(hours=1),
        '6h': timedelta(hours=6),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
    }
    delta = range_map.get(range_str, timedelta(hours=24))
    since = datetime.utcnow() - delta

    records = SensorData.query.filter(
        SensorData.sensor_type == sensor_type,
        SensorData.timestamp >= since
    ).order_by(SensorData.timestamp.asc()).all()

    return jsonify({
        'type': sensor_type,
        'range': range_str,
        'data': [r.to_dict() for r in records]
    })


@sensor_bp.route('/history')
@login_required
def history_page():
    """Render the historical data trends page."""
    return render_template('sensor/history.html')


@sensor_bp.route('/api/thresholds')
@login_required
def thresholds():
    """Get configured sensor thresholds."""
    from flask import current_app
    return jsonify({
        'temperature': {
            'high': current_app.config['TEMP_HIGH'],
            'low': current_app.config['TEMP_LOW']
        },
        'humidity': {
            'high': current_app.config['HUMIDITY_HIGH'],
            'low': current_app.config['HUMIDITY_LOW']
        },
        'smoke': {
            'high': current_app.config['SMOKE_HIGH']
        }
    })


@sensor_bp.route('/api/connection')
@login_required
def connection_status():
    """Get sensor receiver connection status."""
    from sensor.receiver import mqtt_connected
    return jsonify({
        'mqtt': {
            'connected': mqtt_connected.is_set(),
            'message': 'MQTT 已连接' if mqtt_connected.is_set() else 'MQTT 未连接'
        }
    })
