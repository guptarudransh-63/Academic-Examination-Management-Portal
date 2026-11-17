import os
import pytest
import tempfile
import sqlite3
from datetime import datetime, timedelta
from app import create_app
from database import init_db
from werkzeug.security import generate_password_hash

@pytest.fixture
def test_setup():
    db_fd, db_path = tempfile.mkstemp()
    test_config = {
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test-secret-suite'
    }
    app = create_app(test_config)

    with app.app_context():
        init_db(app)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('admin', ?, 'Admin', 'admin@emp.edu', 'admin', 1, 1)
        """, (generate_password_hash('Admin@12345'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('examiner1', ?, 'Dr. Ramesh Sharma', 'ramesh@emp.edu', 'examiner', 1, 1)
        """, (generate_password_hash('Examiner@123'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('examiner2', ?, 'Dr. Anita Rao', 'anita@emp.edu', 'examiner', 1, 1)
        """, (generate_password_hash('Examiner@123'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('examiner_pend', ?, 'Dr. Priya Patel', 'priya@emp.edu', 'examiner', 0, 1)
        """, (generate_password_hash('Examiner@123'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('student1', ?, 'Aarav Mehta', 'aarav@student.emp.edu', 'student', 1, 1)
        """, (generate_password_hash('Student@123'),))
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES ('student2', ?, 'Sanya Verma', 'sanya@student.emp.edu', 'student', 1, 1)
        """, (generate_password_hash('Student@123'),))

        cursor.execute("""
            INSERT INTO courses (course_code, course_name, description)
            VALUES ('CS101', 'MAD-1', 'App Dev')
        """)
        course_id = cursor.lastrowid

        now = datetime.now()
        sc_start = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        sc_end = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        bk_start = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        bk_end = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
        cn_dead = (now + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M")

        cursor.execute("""
            INSERT INTO examinations (course_id, title, description, slot_creation_start, slot_creation_end, booking_start, booking_end, cancellation_deadline, results_published)
            VALUES (?, 'Project Viva', 'Viva Voce', ?, ?, ?, ?, ?, 0)
        """, (course_id, sc_start, sc_end, bk_start, bk_end, cn_dead))
        exam_id = cursor.lastrowid

        cursor.execute("SELECT id FROM users WHERE username IN ('examiner1', 'examiner2')")
        for row in cursor.fetchall():
            cursor.execute("INSERT INTO examiner_assignments (examination_id, examiner_id) VALUES (?, ?)", (exam_id, row[0]))

        cursor.execute("INSERT INTO rubrics (examination_id, total_max_marks) VALUES (?, 100.0)", (exam_id,))
        rubric_id = cursor.lastrowid
        cursor.execute("INSERT INTO rubric_criteria (rubric_id, criterion_name, max_marks) VALUES (?, ?, ?)", (rubric_id, 'Architecture', 50.0))
        cursor.execute("INSERT INTO rubric_criteria (rubric_id, criterion_name, max_marks) VALUES (?, ?, ?)", (rubric_id, 'Viva Defense', 50.0))

        conn.commit()
        conn.close()

    yield app, db_path

    if os.path.exists(db_path):
        try:
            os.close(db_fd)
            os.unlink(db_path)
        except Exception:
            pass

def test_admin_approves_examiner(test_setup):
    app, db_path = test_setup
    client = app.test_client()

    client.post('/auth/login', data={'username': 'admin', 'password': 'Admin@12345'})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = 'examiner_pend'")
    p_id = cur.fetchone()[0]
    conn.close()

    resp = client.post(f'/admin/users/{p_id}/approve', follow_redirects=True)
    assert resp.status_code == 200

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT is_approved FROM users WHERE id = ?", (p_id,))
    approved = cur.fetchone()[0]
    conn.close()
    assert approved == 1

def test_examiner_slot_creation_window(test_setup):
    app, db_path = test_setup
    client = app.test_client()

    client.post('/auth/login', data={'username': 'examiner1', 'password': 'Examiner@123'})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM examinations WHERE title = 'Project Viva'")
    exam_id = cur.fetchone()[0]
    conn.close()

    now = datetime.now()
    s_start = (now + timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M")
    s_end = (now + timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M")

    resp = client.post('/examiner/slots', data={
        'examination_id': exam_id,
        'start_time': s_start,
        'end_time': s_end,
        'capacity': 1,
        'location_or_link': 'Room 101'
    }, follow_redirects=True)
    assert b"Examination slot created successfully" in resp.data

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    past_time = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    cur.execute("UPDATE examinations SET slot_creation_end = ? WHERE id = ?", (past_time, exam_id))
    conn.commit()
    conn.close()

    resp_fail = client.post('/examiner/slots', data={
        'examination_id': exam_id,
        'start_time': s_start,
        'end_time': s_end,
        'capacity': 1
    }, follow_redirects=True)
    assert b"Slot creation is only permitted" in resp_fail.data

def test_student_booking_and_capacity_limits(test_setup):
    app, db_path = test_setup
    client = app.test_client()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM examinations WHERE title = 'Project Viva'")
    exam_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'examiner1'")
    ex1_id = cur.fetchone()[0]

    now = datetime.now()
    s_start = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    s_end = (now + timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M")

    cur.execute("""
        INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count)
        VALUES (?, ?, ?, ?, 1, 0)
    """, (exam_id, ex1_id, s_start, s_end))
    slot_id = cur.lastrowid
    conn.commit()
    conn.close()

    client.post('/auth/login', data={'username': 'student1', 'password': 'Student@123'})
    resp_book = client.post(f'/student/slots/{slot_id}/book', follow_redirects=True)
    assert resp_book.status_code == 200
    assert b"Slot successfully booked" in resp_book.data

    resp_dup = client.post(f'/student/slots/{slot_id}/book', follow_redirects=True)
    assert b"already have an active booking" in resp_dup.data

    client.get('/auth/logout')
    client.post('/auth/login', data={'username': 'student2', 'password': 'Student@123'})
    resp_full = client.post(f'/student/slots/{slot_id}/book', follow_redirects=True)
    assert b"reached its maximum student capacity" in resp_full.data

    client.get('/auth/logout')
    client.post('/auth/login', data={'username': 'student1', 'password': 'Student@123'})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM bookings WHERE slot_id = ? AND student_id = (SELECT id FROM users WHERE username = 'student1')", (slot_id,))
    bk_id = cur.fetchone()[0]
    conn.close()

    resp_cancel = client.post(f'/student/bookings/{bk_id}/cancel', follow_redirects=True)
    assert b"has been cancelled" in resp_cancel.data

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT booked_count FROM slots WHERE id = ?", (slot_id,))
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0

def test_examiner_evaluation_and_ownership(test_setup):
    app, db_path = test_setup
    client = app.test_client()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM examinations WHERE title = 'Project Viva'")
    exam_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'examiner1'")
    ex1_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'student1'")
    st1_id = cur.fetchone()[0]

    now = datetime.now()
    s_start = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    s_end = (now + timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M")

    cur.execute("""
        INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count)
        VALUES (?, ?, ?, ?, 1, 1)
    """, (exam_id, ex1_id, s_start, s_end))
    slot_id = cur.lastrowid

    cur.execute("""
        INSERT INTO bookings (slot_id, student_id, examination_id, status)
        VALUES (?, ?, ?, 'booked')
    """, (slot_id, st1_id, exam_id))
    booking_id = cur.lastrowid

    cur.execute("SELECT id FROM rubric_criteria WHERE rubric_id = (SELECT id FROM rubrics WHERE examination_id = ?)", (exam_id,))
    crit_rows = cur.fetchall()
    c1_id = crit_rows[0][0]
    c2_id = crit_rows[1][0]
    conn.commit()
    conn.close()

    client.post('/auth/login', data={'username': 'examiner2', 'password': 'Examiner@123'})
    resp_unauth = client.get(f'/examiner/bookings/{booking_id}/evaluate')
    assert resp_unauth.status_code == 403

    client.get('/auth/logout')
    client.post('/auth/login', data={'username': 'examiner1', 'password': 'Examiner@123'})
    resp_eval = client.post(f'/examiner/bookings/{booking_id}/evaluate', data={
        f'crit_{c1_id}': '45',
        f'rem_{c1_id}': 'Solid architecture',
        f'crit_{c2_id}': '48',
        f'rem_{c2_id}': 'Well explained',
        'general_remarks': 'Overall good demonstration'
    }, follow_redirects=True)
    assert resp_eval.status_code == 200
    assert b"submitted successfully" in resp_eval.data

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT total_marks_awarded FROM evaluations WHERE booking_id = ?", (booking_id,))
    total = cur.fetchone()[0]
    cur.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,))
    bk_status = cur.fetchone()[0]
    conn.close()
    assert total == 93.0
    assert bk_status == 'completed'

def test_admin_reschedule_and_reassign(test_setup):
    app, db_path = test_setup
    client = app.test_client()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM examinations WHERE title = 'Project Viva'")
    exam_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'examiner1'")
    ex1_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'examiner2'")
    ex2_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = 'student1'")
    st1_id = cur.fetchone()[0]

    now = datetime.now()
    s1_start = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    s1_end = (now + timedelta(days=1, hours=1)).strftime("%Y-%m-%dT%H:%M")
    s2_start = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    s2_end = (now + timedelta(days=2, hours=1)).strftime("%Y-%m-%dT%H:%M")

    cur.execute("""
        INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count)
        VALUES (?, ?, ?, ?, 1, 1)
    """, (exam_id, ex1_id, s1_start, s1_end))
    slot1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count)
        VALUES (?, ?, ?, ?, 1, 0)
    """, (exam_id, ex1_id, s2_start, s2_end))
    slot2_id = cur.lastrowid

    cur.execute("""
        INSERT INTO bookings (slot_id, student_id, examination_id, status)
        VALUES (?, ?, ?, 'booked')
    """, (slot1_id, st1_id, exam_id))
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    client.post('/auth/login', data={'username': 'admin', 'password': 'Admin@12345'})

    resp_resched = client.post(f'/admin/bookings/{booking_id}/reschedule', data={
        'new_slot_id': slot2_id,
        'reason': 'Student timetable conflict'
    }, follow_redirects=True)
    assert resp_resched.status_code == 200
    assert b"successfully rescheduled" in resp_resched.data

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT slot_id FROM bookings WHERE id = ?", (booking_id,))
    cur_slot = cur.fetchone()[0]
    cur.execute("SELECT booked_count FROM slots WHERE id = ?", (slot1_id,))
    s1_count = cur.fetchone()[0]
    cur.execute("SELECT booked_count FROM slots WHERE id = ?", (slot2_id,))
    s2_count = cur.fetchone()[0]
    conn.close()

    assert cur_slot == slot2_id
    assert s1_count == 0
    assert s2_count == 1

    resp_reassign = client.post(f'/admin/slots/{slot1_id}/reassign', data={
        'new_examiner_id': ex2_id,
        'reason': 'Faculty reassignment'
    }, follow_redirects=True)
    assert resp_reassign.status_code == 200
    assert b"reassigned to" in resp_reassign.data

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT examiner_id FROM slots WHERE id = ?", (slot1_id,))
    new_ex = cur.fetchone()[0]
    conn.close()
    assert new_ex == ex2_id
