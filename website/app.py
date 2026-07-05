import threading
from flask import Flask
from config import Config
from extensions import db, login_manager, socketio


def _migrate_add_column(table, column, col_def):
    """给旧表加字段, 已存在则跳过."""
    import sqlalchemy
    try:
        with db.engine.connect() as conn:
            conn.execute(sqlalchemy.text(f'ALTER TABLE {table} ADD COLUMN {column} {col_def}'))
            conn.commit()
    except Exception:
        pass  # 字段已存在, 忽略


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading')

    # Register blueprints
    from auth.routes import auth_bp
    from main.routes import main_bp
    from sensor.routes import sensor_bp
    from camera.routes import camera_bp
    from weather.routes import weather_bp
    from family.routes import family_bp
    from face.routes import face_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(sensor_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(family_bp)
    app.register_blueprint(face_bp)

    # Register user_loader (must happen after extensions are initialized)
    from database.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create database tables & migrate
    with app.app_context():
        db.create_all()
        # 自动给旧表加 weather_location 字段
        _migrate_add_column('users', 'weather_location', 'VARCHAR(50) DEFAULT "xian"')

    # Start sensor receivers in background (non-fatal if they fail)
    if app.config.get('MQTT_ENABLED'):
        try:
            from sensor.receiver import start_mqtt_receiver
            threading.Thread(target=start_mqtt_receiver, args=(app,), daemon=True).start()
            app.logger.info('MQTT receiver thread started')
        except Exception as e:
            app.logger.error(f'Failed to start MQTT receiver: {e}')

    if app.config.get('SOCKET_ENABLED'):
        try:
            from sensor.receiver import start_socket_receiver
            threading.Thread(target=start_socket_receiver, args=(app,), daemon=True).start()
            app.logger.info('Socket receiver thread started')
        except Exception as e:
            app.logger.error(f'Failed to start Socket receiver: {e}')

    # Start face recognition service
    if app.config.get('FACE_ENABLED'):
        try:
            from face.service import start_face_service
            start_face_service(app)
        except Exception as e:
            app.logger.error(f'Failed to start face recognition: {e}')

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
