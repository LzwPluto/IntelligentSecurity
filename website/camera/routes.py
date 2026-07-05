from flask import Blueprint, render_template, Response, jsonify, current_app
from flask_login import login_required
from camera.capture import camera_lock, CV2_AVAILABLE, _get_camera

camera_bp = Blueprint('camera', __name__, url_prefix='/camera')


@camera_bp.route('/stream')
@login_required
def stream_page():
    return render_template('camera/stream.html')


@camera_bp.route('/video_feed')
@login_required
def video_feed():
    if not CV2_AVAILABLE:
        return jsonify({'error': 'OpenCV not installed'}), 503
    from camera.capture import generate_frames
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@camera_bp.route('/api/status')
@login_required
def status():
    device = current_app.config.get('CAMERA_DEVICE', '0')
    acquired = camera_lock.acquire(timeout=0.1)
    if acquired:
        camera_lock.release()
        return jsonify({
            'available': True,
            'device': device,
            'message': f'摄像头可用 ({device})'
        })
    return jsonify({
        'available': False,
        'device': device,
        'message': '摄像头正被占用'
    })
