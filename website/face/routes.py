from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from auth.utils import homeowner_required

face_bp = Blueprint('face', __name__, url_prefix='/face')


@face_bp.route('/status')
@login_required
def status():
    return render_template('face/status.html')


@face_bp.route('/api/status')
@login_required
def api_status():
    from face.service import get_face_service
    svc = get_face_service()
    return jsonify({
        'running': svc.running if svc else False,
        'known_count': len(svc.known_features) if svc else 0,
        'last_result': {'name': svc._last_result['name'], 'is_stranger': svc._last_result['is_stranger'], 'distance':
  float(svc._last_result['distance'])} if svc and svc._last_result else None
    })


@face_bp.route('/api/logs')
@login_required
def api_logs():
    from database.models import FaceLog
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = FaceLog.query.order_by(FaceLog.timestamp.desc())
    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({'total': total, 'page': page, 'logs': [l.to_dict() for l in logs]})


@face_bp.route('/enroll', methods=['GET', 'POST'])
@login_required
@homeowner_required
def enroll():
    from database.models import FamilyMember

    if request.method == 'GET':
        family_members = FamilyMember.query.filter_by(
            user_id=current_user.id
        ).all()
        return render_template('face/enroll.html', family_members=family_members)

    import numpy as np
    from extensions import db
    from database.models import FaceFeature
    from face.service import get_face_service

    member_id = request.json.get('family_member_id')
    if not member_id:
        return jsonify({'error': '请选择家人'}), 400

    member = FamilyMember.query.filter_by(
        id=member_id, user_id=current_user.id
    ).first()
    if not member:
        return jsonify({'error': '家人不存在'}), 404

    svc = get_face_service()
    if not svc or not svc.running:
        return jsonify({'error': '人脸识别服务未运行'}), 503

    features = svc.capture_enroll_frames(count=10)
    if len(features) == 0:
        return jsonify({'error': '未检测到人脸，请调整位置后重试'}), 400

    avg_feature = np.mean(features, axis=0)
    norm = np.linalg.norm(avg_feature)
    if norm > 0:
        avg_feature = avg_feature / norm

    record = FaceFeature(
        name=member.name,
        feature=avg_feature.astype(np.float32).tobytes(),
        family_member_id=member.id,
        enrolled_by=current_user.id
    )
    db.session.add(record)
    db.session.commit()
    svc.refresh_known_features()

    return jsonify({'success': True, 'name': member.name, 'frames': len(features)})


@face_bp.route('/members')
@login_required
def list_members():
    from database.models import FaceFeature, FamilyMember
    records = FaceFeature.query.outerjoin(
        FamilyMember, FaceFeature.family_member_id == FamilyMember.id
    ).add_columns(
        FaceFeature.id, FaceFeature.name, FaceFeature.created_at,
        FamilyMember.relationship
    ).order_by(FaceFeature.created_at.desc()).all()

    return jsonify({
        'members': [
            {
                'id': r.id,
                'name': r.name,
                'relationship': r.relationship or '',
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
            }
            for r in records
        ]
    })


@face_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@homeowner_required
def delete_face(id):
    from extensions import db
    from database.models import FaceFeature
    from face.service import get_face_service

    record = FaceFeature.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    svc = get_face_service()
    if svc:
        svc.refresh_known_features()
    return jsonify({'success': True})
