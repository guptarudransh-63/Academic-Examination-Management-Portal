import os
from flask import Flask, render_template, redirect, url_for, session
from config import Config
from database import close_db

def create_app(test_config=None):
    app = Flask(__name__)

    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'examiner':
                return redirect(url_for('examiner.dashboard'))
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
        return render_template('index.html')

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.examiner import examiner_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(examiner_bp)
    app.register_blueprint(student_bp)

    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f" * Starting Examination Management Portal...", flush=True)
    application = create_app()
    print(f" * Running on http://127.0.0.1:{port}", flush=True)
    print(f" * Press CTRL+C to stop", flush=True)
    application.run(host='127.0.0.1', port=port, debug=False)
