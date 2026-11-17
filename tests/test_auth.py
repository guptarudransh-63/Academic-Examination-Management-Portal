import os
import pytest
import tempfile
import sqlite3
from app import create_app
from database import init_db
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    test_config = {
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test-secret-key'
    }
    app = create_app(test_config)

    with app.app_context():
        init_db(app)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('admin', ?, 'Administrator', 'admin@emp.edu', 'admin', 1, 1)
        """, (generate_password_hash('Admin@12345'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('examiner1', ?, 'Dr. Ramesh Sharma', 'ramesh@emp.edu', 'examiner', 1, 1)
        """, (generate_password_hash('Examiner@123'),))
        conn.commit()
        conn.close()

    yield app

    if os.path.exists(db_path):
        try:
            os.close(db_fd)
            os.unlink(db_path)
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_admin_pre_existing_login(client):
    response = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'Admin@12345'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Administrator Dashboard" in response.data

def test_invalid_login_credentials(client):
    response = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_student_registration_and_login(client):
    reg_response = client.post('/auth/register/student', data={
        'username': 'newstudent',
        'full_name': 'New Student',
        'email': 'student@test.edu',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert reg_response.status_code == 200
    assert b"Registration successful" in reg_response.data

    login_response = client.post('/auth/login', data={
        'username': 'newstudent',
        'password': 'Password123'
    }, follow_redirects=True)
    assert login_response.status_code == 200
    assert b"Student Dashboard" in login_response.data

def test_examiner_registration_requires_approval(client):
    reg_response = client.post('/auth/register/examiner', data={
        'username': 'newexaminer',
        'full_name': 'Dr. New Examiner',
        'email': 'newexaminer@test.edu',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert reg_response.status_code == 200
    assert b"requires Administrator approval" in reg_response.data

    login_response = client.post('/auth/login', data={
        'username': 'newexaminer',
        'password': 'Password123'
    }, follow_redirects=True)
    assert login_response.status_code == 200
    assert b"awaiting administrator approval" in login_response.data

def test_approved_examiner_login(client):
    response = client.post('/auth/login', data={
        'username': 'examiner1',
        'password': 'Examiner@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Examiner Dashboard" in response.data

def test_unauthorized_role_access(client):
    admin_resp = client.get('/admin/dashboard')
    assert admin_resp.status_code == 302
    assert '/auth/login' in admin_resp.headers['Location']

    student_resp = client.get('/student/dashboard')
    assert student_resp.status_code == 302
    assert '/auth/login' in student_resp.headers['Location']

def test_student_cannot_access_admin_dashboard(client):
    client.post('/auth/register/student', data={
        'username': 'student_user',
        'full_name': 'Student User',
        'email': 'suser@test.edu',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    client.post('/auth/login', data={
        'username': 'student_user',
        'password': 'Password123'
    })

    response = client.get('/admin/dashboard')
    assert response.status_code == 403
    assert b"Access Denied" in response.data

def test_logout(client):
    client.post('/auth/login', data={
        'username': 'admin',
        'password': 'Admin@12345'
    })
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"logged out successfully" in response.data

    dashboard_resp = client.get('/admin/dashboard')
    assert dashboard_resp.status_code == 302
