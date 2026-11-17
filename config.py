import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mad1-exam-portal-secret-key-2026')
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'emp.db')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600                           
