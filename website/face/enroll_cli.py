"""
命令行人脸录入（在 RK3588 上直接运行）
用法: cd "loT(2)" && python -m face.enroll_cli
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
import time
from app import create_app
from extensions import db
from database.models import FaceFeature, FamilyMember
from face.config import CAMERA_ID, CAM_WIDTH, CAM_HEIGHT, DET_MODEL, REC_MODEL, ENROLL_FRAMES
from face.utils import load_model
from face.retinaface import detect_face
from face.mobileface import extract_feature


def main():
    app = create_app()
    with app.app_context():
        members = FamilyMember.query.all()

    if members:
        print('已录入的家人:')
        for m in members:
            print(f'  [{m.id}] {m.name}（{m.relationship or "未填"}）')
        choice = input('输入家人 ID 关联，或直接输入新姓名: ').strip()
        try:
            with app.app_context():
                member = FamilyMember.query.get(int(choice))
            name = member.name
            member_id = member.id
        except (ValueError, TypeError, AttributeError):
            name = choice
            member_id = None
    else:
        name = input('请输入姓名: ').strip()
        member_id = None

    if not name:
        print('姓名不能为空')
        return

    print('加载模型...')
    detector = load_model(DET_MODEL)
    recognizer = load_model(REC_MODEL)

    cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    print(f'3秒后开始采集 {ENROLL_FRAMES} 帧...')
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(1)

    features = []
    while len(features) < ENROLL_FRAMES:
        ret, frame = cap.read()
        if not ret:
            continue
        result = detect_face(detector, frame)
        if result is None:
            continue
        x1, y1, x2, y2, landmarks = result
        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            continue
        feature = extract_feature(recognizer, face_crop, landmarks, x1, y1)
        if feature is None:
            continue
        features.append(feature)
        print(f'已采集 {len(features)}/{ENROLL_FRAMES}')
        time.sleep(0.05)

    cap.release()

    avg = np.mean(features, axis=0)
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm

    with app.app_context():
        record = FaceFeature(
            name=name,
            feature=avg.astype(np.float32).tobytes(),
            family_member_id=member_id
        )
        db.session.add(record)
        db.session.commit()

    print(f'录入成功: {name} ({len(features)} 帧)')


if __name__ == '__main__':
    main()
