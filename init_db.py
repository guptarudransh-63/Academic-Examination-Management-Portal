import os
import sqlite3
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config

def initialize_database(seed_sample_data=False):
    db_path = Config.DATABASE_PATH
    schema_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'schema.sql')

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    print("Database schema created successfully.")

    admin_username = os.environ.get('EMP_ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('EMP_ADMIN_PASSWORD', 'Admin@12345')
    admin_email = os.environ.get('EMP_ADMIN_EMAIL', 'admin@emp.edu')
    admin_fullname = os.environ.get('EMP_ADMIN_NAME', 'Portal Administrator')

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (admin_username,))
    existing_admin = cursor.fetchone()

    if not existing_admin:
        hashed_password = generate_password_hash(admin_password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
            VALUES (?, ?, ?, ?, 'admin', 1, 1)
        """, (admin_username, hashed_password, admin_fullname, admin_email))
        conn.commit()
        print(f"Initial Admin created: username='{admin_username}'")
    else:
        print(f"Admin '{admin_username}' already exists. Skipping creation.")

    if seed_sample_data:
        seed_data(conn)
        seed_extra_data(conn)

    conn.close()
    print("Database setup complete.")

def seed_data(conn):
    cursor = conn.cursor()
    now = datetime.now()

    examiners = [
        ('examiner1', 'Dr. Ramesh Sharma', 'ramesh@emp.edu', 'Examiner@123', 1),
        ('examiner2', 'Dr. Anita Rao', 'anita@emp.edu', 'Examiner@123', 1),
        ('examiner_pending', 'Dr. Priya Patel', 'priya@emp.edu', 'Examiner@123', 0),
    ]
    for uname, fname, email, pwd, approved in examiners:
        cursor.execute("SELECT id FROM users WHERE username = ?", (uname,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
                VALUES (?, ?, ?, ?, 'examiner', ?, 1)
            """, (uname, generate_password_hash(pwd), fname, email, approved))

    students = [
        ('student1', 'Aarav Mehta', 'aarav@student.emp.edu', 'Student@123'),
        ('student2', 'Sanya Verma', 'sanya@student.emp.edu', 'Student@123'),
    ]
    for uname, fname, email, pwd in students:
        cursor.execute("SELECT id FROM users WHERE username = ?", (uname,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
                VALUES (?, ?, ?, ?, 'student', 1, 1)
            """, (uname, generate_password_hash(pwd), fname, email))

    courses = [
        ('CS101', 'Modern Application Development I', 'Web architecture, Flask backend frameworks, REST APIs, and relational databases.'),
        ('MA201', 'Linear Algebra and Optimization', 'Vector spaces, matrix decompositions, eigenvalues, and computational methods.'),
    ]
    for code, name, desc in courses:
        cursor.execute("SELECT id FROM courses WHERE course_code = ?", (code,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO courses (course_code, course_name, description)
                VALUES (?, ?, ?)
            """, (code, name, desc))

    conn.commit()

    cursor.execute("SELECT id FROM courses WHERE course_code = 'CS101'")
    cs101_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM users WHERE username = 'examiner1'")
    ex1_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM users WHERE username = 'examiner2'")
    ex2_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM users WHERE username = 'student1'")
    st1_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM users WHERE username = 'student2'")
    st2_id = cursor.fetchone()[0]

    sc_start = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    sc_end = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
    bk_start = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    bk_end = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    cn_dead = (now + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M")

    cursor.execute("SELECT id FROM examinations WHERE title = 'End-Term Project Viva Voce'")
    existing_exam = cursor.fetchone()
    if not existing_exam:
        cursor.execute("""
            INSERT INTO examinations (
                course_id, title, description,
                slot_creation_start, slot_creation_end,
                booking_start, booking_end, cancellation_deadline,
                results_published
            ) VALUES (?, 'End-Term Project Viva Voce', 'Individual project demonstration, architecture defense, and live code walkthrough.',
                      ?, ?, ?, ?, ?, 1)
        """, (cs101_id, sc_start, sc_end, bk_start, bk_end, cn_dead))
        exam_id = cursor.lastrowid

        cursor.execute("INSERT OR IGNORE INTO examiner_assignments (examination_id, examiner_id) VALUES (?, ?)", (exam_id, ex1_id))
        cursor.execute("INSERT OR IGNORE INTO examiner_assignments (examination_id, examiner_id) VALUES (?, ?)", (exam_id, ex2_id))

        cursor.execute("INSERT INTO rubrics (examination_id, total_max_marks, description) VALUES (?, 100.0, 'Comprehensive Evaluation Rubric')", (exam_id,))
        rubric_id = cursor.lastrowid

        criteria_data = [
            ('Code Quality & Flask Architecture', 30.0, 'Proper route modularization, models, error handlers, and code clarity.'),
            ('Viva Explanation & Concept Mastery', 40.0, 'Theoretical understanding of SQLite transactions, RBAC, sessions, and Jinja2.'),
            ('Demonstration & Test Execution', 30.0, 'Successful execution of workflows, validations, and test suites.')
        ]
        crit_ids = []
        for cname, cmax, cdesc in criteria_data:
            cursor.execute("INSERT INTO rubric_criteria (rubric_id, criterion_name, max_marks, description) VALUES (?, ?, ?, ?)", (rubric_id, cname, cmax, cdesc))
            crit_ids.append(cursor.lastrowid)

        slot1_start = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        slot1_end = (now + timedelta(days=1)).replace(hour=10, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        cursor.execute("""
            INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count, location_or_link)
            VALUES (?, ?, ?, ?, 1, 1, 'Google Meet: https://meet.google.com/abc-emp-demo')
        """, (exam_id, ex1_id, slot1_start, slot1_end))
        slot1_id = cursor.lastrowid

        slot2_start = (now + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        slot2_end = (now + timedelta(days=1)).replace(hour=11, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        cursor.execute("""
            INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count, location_or_link)
            VALUES (?, ?, ?, ?, 1, 0, 'Google Meet: https://meet.google.com/abc-emp-demo')
        """, (exam_id, ex1_id, slot2_start, slot2_end))

        slot3_start = (now + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        slot3_end = (now + timedelta(days=2)).replace(hour=14, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
        cursor.execute("""
            INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count, location_or_link)
            VALUES (?, ?, ?, ?, 2, 1, 'Conference Room 204')
        """, (exam_id, ex2_id, slot3_start, slot3_end))
        slot3_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO bookings (slot_id, student_id, examination_id, status)
            VALUES (?, ?, ?, 'completed')
        """, (slot1_id, st1_id, exam_id))
        bk1_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO bookings (slot_id, student_id, examination_id, status)
            VALUES (?, ?, ?, 'booked')
        """, (slot3_id, st2_id, exam_id))

        cursor.execute("""
            INSERT INTO evaluations (booking_id, examiner_id, total_marks_awarded, general_remarks)
            VALUES (?, ?, 92.0, 'Exceptional demonstration! Explained database transactions, role authorization, and test cases with exemplary clarity.')
        """, (bk1_id, ex1_id))
        eval_id = cursor.lastrowid

        cursor.execute("INSERT INTO evaluation_scores (evaluation_id, criterion_id, marks_awarded, remarks) VALUES (?, ?, 28.0, 'Clean architecture and proper blueprints.')", (eval_id, crit_ids[0]))
        cursor.execute("INSERT INTO evaluation_scores (evaluation_id, criterion_id, marks_awarded, remarks) VALUES (?, ?, 37.0, 'Answered all conceptual questions accurately.')", (eval_id, crit_ids[1]))
        cursor.execute("INSERT INTO evaluation_scores (evaluation_id, criterion_id, marks_awarded, remarks) VALUES (?, ?, 27.0, 'Automated tests executed cleanly.')", (eval_id, crit_ids[2]))

        conn.commit()
        print("Realistic demonstration exam, slots, bookings, and evaluations seeded.")

def _fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M")


def _ensure_user(cursor, username, full_name, email, role, password, approved=1, active=1):
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("""
        INSERT INTO users (username, password_hash, full_name, email, role, is_approved, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, generate_password_hash(password), full_name, email, role, approved, active))
    return cursor.lastrowid


def _ensure_course(cursor, code, name, desc):
    cursor.execute("SELECT id FROM courses WHERE course_code = ?", (code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO courses (course_code, course_name, description) VALUES (?, ?, ?)",
                   (code, name, desc))
    return cursor.lastrowid


def _create_exam(cursor, course_id, title, desc, windows, published, examiner_ids, criteria):
    """Create an exam with examiner assignments and a rubric. Returns (exam_id, criterion_rows)."""
    cursor.execute("""
        INSERT INTO examinations (course_id, title, description,
            slot_creation_start, slot_creation_end, booking_start, booking_end,
            cancellation_deadline, results_published)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (course_id, title, desc, *[_fmt(w) for w in windows], published))
    exam_id = cursor.lastrowid
    for ex_id in examiner_ids:
        cursor.execute("INSERT OR IGNORE INTO examiner_assignments (examination_id, examiner_id) VALUES (?, ?)",
                       (exam_id, ex_id))
    total = sum(c[1] for c in criteria)
    cursor.execute("INSERT INTO rubrics (examination_id, total_max_marks, description) VALUES (?, ?, ?)",
                   (exam_id, total, f'Evaluation rubric for {title}'))
    rubric_id = cursor.lastrowid
    crit_rows = []
    for cname, cmax, cdesc in criteria:
        cursor.execute("INSERT INTO rubric_criteria (rubric_id, criterion_name, max_marks, description) VALUES (?, ?, ?, ?)",
                       (rubric_id, cname, cmax, cdesc))
        crit_rows.append((cursor.lastrowid, cmax))
    return exam_id, crit_rows


def _create_slot(cursor, exam_id, examiner_id, start, minutes, capacity, location):
    cursor.execute("""
        INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count, location_or_link)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (exam_id, examiner_id, _fmt(start), _fmt(start + timedelta(minutes=minutes)), capacity, location))
    return cursor.lastrowid


def _book(cursor, slot_id, student_id, exam_id, status='booked'):
    cancelled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'cancelled' else None
    cursor.execute("""
        INSERT INTO bookings (slot_id, student_id, examination_id, status, cancelled_at)
        VALUES (?, ?, ?, ?, ?)
    """, (slot_id, student_id, exam_id, status, cancelled_at))
    if status != 'cancelled':
        cursor.execute("UPDATE slots SET booked_count = booked_count + 1 WHERE id = ?", (slot_id,))
    return cursor.lastrowid


def _evaluate(cursor, booking_id, examiner_id, crit_rows, fractions, remark):
    scores = [round(cmax * f * 2) / 2 for (_, cmax), f in zip(crit_rows, fractions)]
    cursor.execute("""
        INSERT INTO evaluations (booking_id, examiner_id, total_marks_awarded, general_remarks)
        VALUES (?, ?, ?, ?)
    """, (booking_id, examiner_id, sum(scores), remark))
    eval_id = cursor.lastrowid
    for (crit_id, _), score in zip(crit_rows, scores):
        cursor.execute("INSERT INTO evaluation_scores (evaluation_id, criterion_id, marks_awarded, remarks) VALUES (?, ?, ?, ?)",
                       (eval_id, crit_id, score, None))


def seed_extra_data(conn):
    """Larger dummy dataset covering every exam state. Safe to run repeatedly."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM examinations WHERE title = 'Python Programming Oral Exam'")
    if cursor.fetchone():
        print("Extra dummy data already present. Skipping.")
        return

    now = datetime.now()
    day = lambda d, h=10, m=0: (now + timedelta(days=d)).replace(hour=h, minute=m, second=0, microsecond=0)

    # --- Users ---
    ex = {u: _ensure_user(cursor, u, n, e, 'examiner', 'Examiner@123') for u, n, e in [
        ('examiner1', 'Dr. Ramesh Sharma', 'ramesh@emp.edu'),
        ('examiner2', 'Dr. Anita Rao', 'anita@emp.edu'),
        ('examiner3', 'Dr. Vikram Iyer', 'vikram@emp.edu'),
        ('examiner4', 'Dr. Meera Nair', 'meera@emp.edu'),
    ]}
    student_info = [
        ('student3', 'Ishaan Kapoor'), ('student4', 'Diya Malhotra'), ('student5', 'Kabir Singh'),
        ('student6', 'Ananya Iyer'), ('student7', 'Rohan Desai'), ('student8', 'Meher Joshi'),
        ('student9', 'Arjun Reddy'), ('student10', 'Tara Banerjee'), ('student11', 'Vihaan Nair'),
        ('student12', 'Zoya Khan'),
    ]
    st = [_ensure_user(cursor, u, n, f'{u}@student.emp.edu', 'student', 'Student@123') for u, n in student_info]
    _ensure_user(cursor, 'student_inactive', 'Neel Chopra', 'neel@student.emp.edu', 'student', 'Student@123', active=0)

    # --- Courses ---
    c_py = _ensure_course(cursor, 'CS102', 'Programming in Python', 'Core Python, data structures, functions, OOP and file handling.')
    c_ml = _ensure_course(cursor, 'DS201', 'Machine Learning Practice', 'Supervised learning, model evaluation, feature engineering and pipelines.')
    c_db = _ensure_course(cursor, 'CS301', 'Database Management Systems', 'ER modelling, SQL, normalization, indexing and transactions.')
    c_ee = _ensure_course(cursor, 'EE110', 'Digital Electronics', 'Boolean algebra, combinational and sequential circuits, FPGAs.')
    _ensure_course(cursor, 'HS105', 'Technical Communication', 'Report writing, presentations and professional communication.')

    remarks = [
        'Excellent understanding and confident answers.',
        'Good work overall; a few gaps in edge cases.',
        'Satisfactory. Needs more practice with core concepts.',
        'Strong implementation, explanation could be clearer.',
        'Solid attempt with well-structured code.',
    ]
    profiles = [(0.95, 0.9, 0.92), (0.8, 0.75, 0.85), (0.6, 0.55, 0.65), (0.9, 0.7, 0.8), (0.85, 0.82, 0.78)]

    # --- Exam A: finished, results published ---
    exam_a, crit_a = _create_exam(
        cursor, c_py, 'Python Programming Oral Exam', 'Oral exam on Python fundamentals and problem solving.',
        (day(-30), day(-20), day(-25), day(-15), day(-17)), 1, [ex['examiner3']],
        [('Problem Solving', 40.0, 'Approach and correctness.'),
         ('Code Explanation', 35.0, 'Ability to explain written code.'),
         ('Python Concepts', 25.0, 'Theory questions on Python.')])
    for i in range(5):
        slot = _create_slot(cursor, exam_a, ex['examiner3'], day(-12 + i // 2, 10 + (i % 2)), 30, 1, 'Room 101, Academic Block')
        bk = _book(cursor, slot, st[i], exam_a, 'completed')
        _evaluate(cursor, bk, ex['examiner3'], crit_a, profiles[i], remarks[i])

    # --- Exam B: finished and evaluated, results NOT yet published ---
    exam_b, crit_b = _create_exam(
        cursor, c_ml, 'Machine Learning Project Viva', 'Project defence covering model choice, metrics and deployment.',
        (day(-14), day(-7), day(-10), day(-4), day(-6)), 0, [ex['examiner2'], ex['examiner4']],
        [('Model & Methodology', 40.0, 'Choice of models and validation strategy.'),
         ('Results & Analysis', 30.0, 'Metrics, error analysis and insights.'),
         ('Viva Answers', 30.0, 'Response to examiner questions.')])
    slot_b1 = _create_slot(cursor, exam_b, ex['examiner2'], day(-3, 14), 45, 2, 'Google Meet: https://meet.google.com/ml-viva-01')
    slot_b2 = _create_slot(cursor, exam_b, ex['examiner4'], day(-2, 15), 45, 2, 'Google Meet: https://meet.google.com/ml-viva-02')
    for i, (slot, examiner) in enumerate([(slot_b1, 'examiner2'), (slot_b1, 'examiner2'), (slot_b2, 'examiner4')]):
        bk = _book(cursor, slot, st[3 + i], exam_b, 'completed')
        _evaluate(cursor, bk, ex[examiner], crit_b, profiles[(i + 2) % 5], remarks[(i + 1) % 5])
    _book(cursor, slot_b2, st[6], exam_b, 'booked')  # attended but awaiting evaluation

    # --- Exam C: booking window open now ---
    exam_c, _ = _create_exam(
        cursor, c_db, 'DBMS Lab Viva', 'Viva on SQL queries, normalization and transaction management.',
        (day(-5), day(3), day(-2), day(6), day(4)), 0, [ex['examiner1'], ex['examiner3']],
        [('SQL Queries', 40.0, 'Writing and optimizing queries.'),
         ('Schema Design', 30.0, 'ER diagrams and normalization.'),
         ('Transactions & Indexing', 30.0, 'ACID, locking and indexes.')])
    slots_c = [
        _create_slot(cursor, exam_c, ex['examiner1'], day(2, 9), 30, 2, 'Lab 3, CS Department'),
        _create_slot(cursor, exam_c, ex['examiner1'], day(2, 10), 30, 2, 'Lab 3, CS Department'),
        _create_slot(cursor, exam_c, ex['examiner3'], day(3, 11), 30, 3, 'Google Meet: https://meet.google.com/dbms-viva'),
        _create_slot(cursor, exam_c, ex['examiner3'], day(3, 14), 30, 3, 'Google Meet: https://meet.google.com/dbms-viva'),
        _create_slot(cursor, exam_c, ex['examiner1'], day(5, 16), 30, 1, 'Lab 3, CS Department'),
    ]
    _book(cursor, slots_c[0], st[0], exam_c)
    _book(cursor, slots_c[0], st[1], exam_c)            # slot 1 now full
    _book(cursor, slots_c[2], st[2], exam_c)
    _book(cursor, slots_c[2], st[7], exam_c, 'cancelled')
    _book(cursor, slots_c[3], st[8], exam_c)
    rescheduled = _book(cursor, slots_c[1], st[9], exam_c)
    # Move one booking to another slot and record it, as the admin reschedule flow does.
    cursor.execute("UPDATE bookings SET slot_id = ? WHERE id = ?", (slots_c[3], rescheduled))
    cursor.execute("UPDATE slots SET booked_count = booked_count - 1 WHERE id = ?", (slots_c[1],))
    cursor.execute("UPDATE slots SET booked_count = booked_count + 1 WHERE id = ?", (slots_c[3],))
    cursor.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
    admin_id = cursor.fetchone()[0]
    cursor.execute("""
        INSERT INTO reschedule_logs (booking_id, old_slot_id, new_slot_id, changed_by, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (rescheduled, slots_c[1], slots_c[3], admin_id, 'Student had a clash with another exam'))

    # --- Exam D: slot creation open, booking not started yet ---
    exam_d, _ = _create_exam(
        cursor, c_ee, 'Digital Electronics Practical', 'Hands-on circuit building and debugging assessment.',
        (day(-1), day(8), day(10), day(15), day(13)), 0, [ex['examiner4']],
        [('Circuit Design', 50.0, 'Correct design of the given circuit.'),
         ('Implementation', 30.0, 'Breadboard / simulator build.'),
         ('Viva', 20.0, 'Concept questions.')])
    _create_slot(cursor, exam_d, ex['examiner4'], day(11, 10), 60, 4, 'Electronics Lab, Block B')
    _create_slot(cursor, exam_d, ex['examiner4'], day(12, 10), 60, 4, 'Electronics Lab, Block B')

    conn.commit()
    print("Extra dummy data seeded: 4 examiners, 10+ students, 5 courses, 4 exams in different states.")


if __name__ == '__main__':
    seed = '--seed' in sys.argv
    initialize_database(seed_sample_data=seed)
