from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
from database import get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_valid_email(email):
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_regex, email) is not None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'examiner':
            return redirect(url_for('examiner.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return render_template('auth/login.html', username=username)

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', username=username)

        if not user['is_active']:
            flash('This account has been deactivated. Please contact the administrator.', 'danger')
            return render_template('auth/login.html')

        if user['role'] == 'examiner' and not user['is_approved']:
            flash('Your examiner registration is awaiting administrator approval. Please try again later.', 'warning')
            return render_template('auth/login.html', username=username)

        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        session['is_approved'] = user['is_approved']

        flash(f"Welcome back, {user['full_name']}!", 'success')

        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'examiner':
            return redirect(url_for('examiner.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if 'user_id' in session:
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        errors = []
        if len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        if not full_name:
            errors.append('Full name is required.')
        if not is_valid_email(email):
            errors.append('Please provide a valid email address.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        existing = cursor.fetchone()
        if existing:
            errors.append('Username or email is already registered.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register_student.html', username=username, full_name=full_name, email=email)

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES (?, ?, ?, ?, 'student', 1, 1)
        """, (username, password_hash, full_name, email))
        db.commit()

        flash('Registration successful! You may now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html')

@auth_bp.route('/register/examiner', methods=['GET', 'POST'])
def register_examiner():
    if 'user_id' in session:
        return redirect(url_for('examiner.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        errors = []
        if len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        if not full_name:
            errors.append('Full name is required.')
        if not is_valid_email(email):
            errors.append('Please provide a valid email address.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            errors.append('Username or email is already registered.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register_examiner.html', username=username, full_name=full_name, email=email)

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES (?, ?, ?, ?, 'examiner', 0, 1)
        """, (username, password_hash, full_name, email))
        db.commit()

        flash('Registration submitted successfully! Your account requires Administrator approval before you can log in.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_examiner.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
