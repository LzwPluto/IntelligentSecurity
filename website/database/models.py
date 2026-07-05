from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # homeowner / member
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    weather_location = db.Column(db.String(50), default='xian')  # 天气查询城市
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    family_members = db.relationship('FamilyMember', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class SensorData(db.Model):
    __tablename__ = 'sensor_data'

    id = db.Column(db.Integer, primary_key=True)
    sensor_type = db.Column(db.String(20), nullable=False, index=True)  # temperature / humidity / smoke
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.sensor_type,
            'value': self.value,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<SensorData {self.sensor_type}={self.value}>'


class FamilyMember(db.Model):
    __tablename__ = 'family_members'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    relationship = db.Column(db.String(40))  # 父亲/母亲/儿子/女儿 etc.
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FamilyMember {self.name}>'


class FaceFeature(db.Model):
    """已录入的人脸特征（关联 family_members）"""
    __tablename__ = 'face_features'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    feature = db.Column(db.LargeBinary, nullable=False)  # 128维 float32 numpy array → tobytes
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id'))
    enrolled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FaceFeature {self.name}>'


class FaceLog(db.Model):
    """人脸识别日志"""
    __tablename__ = 'face_logs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    is_stranger = db.Column(db.Boolean, default=False)
    distance = db.Column(db.Float)
    snapshot = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_stranger': self.is_stranger,
            'distance': self.distance,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

    def __repr__(self):
        return f'<FaceLog {self.name or "stranger"}>'
