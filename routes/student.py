from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from datetime import datetime
from decorators import role_required
from database import get_db

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM bookings
        WHERE student_id = ? AND status = 'booked'
    """, (student_id,))
    active_bookings_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT COUNT(ev.id) AS count
        FROM evaluations ev
        JOIN bookings b ON ev.booking_id = b.id
        JOIN examinations e ON b.examination_id = e.id
        WHERE b.student_id = ? AND e.results_published = 1
    """, (student_id,))
    published_results_count = cursor.fetchone()['count']

    now_str = datetime.now().isoformat()
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM examinations
        WHERE ? BETWEEN booking_start AND booking_end
    """, (now_str,))
    open_exams_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT b.id, s.start_time, s.end_time, s.location_or_link,
               e.title AS exam_title, c.course_code, ex.full_name AS examiner_name
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE b.student_id = ? AND b.status = 'booked'
        ORDER BY s.start_time ASC
        LIMIT 1
    """, (student_id,))
    next_booking = cursor.fetchone()

    return render_template(
        'student/dashboard.html',
        active_bookings_count=active_bookings_count,
        published_results_count=published_results_count,
        open_exams_count=open_exams_count,
        next_booking=next_booking
    )

@student_bp.route('/exams')
@role_required('student')
def browse_exams():
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    search_query = request.args.get('q', '').strip()
    course_filter = request.args.get('course', '').strip()

    sql = """
        SELECT e.*, c.course_code, c.course_name,
               (SELECT COUNT(*) FROM slots WHERE examination_id = e.id AND booked_count < capacity) AS open_slots_count,
               (SELECT id FROM bookings WHERE examination_id = e.id AND student_id = ? AND status = 'booked') AS my_active_booking_id
        FROM examinations e
        JOIN courses c ON e.course_id = c.id
        WHERE 1=1
    """
    params = [student_id]

    if course_filter:
        sql += " AND c.course_code = ?"
        params.append(course_filter)

    if search_query:
        sql += " AND (e.title LIKE ? OR c.course_name LIKE ? OR c.course_code LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])

    sql += " ORDER BY e.booking_start ASC"
    cursor.execute(sql, tuple(params))
    exams = cursor.fetchall()

    cursor.execute("SELECT DISTINCT course_code, course_name FROM courses ORDER BY course_code ASC")
    course_options = cursor.fetchall()

    now_iso = datetime.now().isoformat()
    return render_template(
        'student/exams.html',
        exams=exams,
        course_options=course_options,
        search_query=search_query,
        course_filter=course_filter,
        now_iso=now_iso
    )

@student_bp.route('/exams/<int:exam_id>/slots')
@role_required('student')
def exam_slots(exam_id):
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_name, r.total_max_marks
        FROM examinations e
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        WHERE e.id = ?
    """, (exam_id,))
    exam = cursor.fetchone()

    if not exam:
        flash('Examination not found.', 'danger')
        return redirect(url_for('student.browse_exams'))

    cursor.execute("""
        SELECT b.*, s.start_time, s.end_time, ex.full_name AS examiner_name
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE b.examination_id = ? AND b.student_id = ? AND b.status = 'booked'
    """, (exam_id, student_id))
    existing_booking = cursor.fetchone()

    cursor.execute("""
        SELECT s.*, ex.full_name AS examiner_name,
               (s.capacity - s.booked_count) AS seats_remaining
        FROM slots s
        JOIN users ex ON s.examiner_id = ex.id
        WHERE s.examination_id = ?
        ORDER BY s.start_time ASC
    """, (exam_id,))
    available_slots = cursor.fetchall()

    now_iso = datetime.now().isoformat()
    is_window_open = (exam['booking_start'] <= now_iso <= exam['booking_end'])

    return render_template(
        'student/slots.html',
        exam=exam,
        existing_booking=existing_booking,
        slots=available_slots,
        is_window_open=is_window_open,
        now_iso=now_iso
    )

@student_bp.route('/slots/<int:slot_id>/book', methods=['POST'])
@role_required('student')
def book_slot(slot_id):
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            SELECT s.*, e.id AS exam_id, e.title AS exam_title,
                   e.booking_start, e.booking_end, e.cancellation_deadline
            FROM slots s
            JOIN examinations e ON s.examination_id = e.id
            WHERE s.id = ?
        """, (slot_id,))
        slot = cursor.fetchone()

        if not slot:
            flash('The requested slot does not exist.', 'danger')
            return redirect(url_for('student.browse_exams'))

        exam_id = slot['exam_id']
        now_dt = datetime.now()
        bk_start = datetime.fromisoformat(slot['booking_start'])
        bk_end = datetime.fromisoformat(slot['booking_end'])

        if not (bk_start <= now_dt <= bk_end):
            flash(f"Booking is only allowed between {slot['booking_start']} and {slot['booking_end']}.", 'danger')
            return redirect(url_for('student.exam_slots', exam_id=exam_id))

        cursor.execute("""
            SELECT id FROM bookings
            WHERE examination_id = ? AND student_id = ? AND status = 'booked'
        """, (exam_id, student_id))
        if cursor.fetchone():
            flash('You already have an active booking for this examination.', 'danger')
            return redirect(url_for('student.exam_slots', exam_id=exam_id))

        if slot['booked_count'] >= slot['capacity']:
            flash('Sorry, this slot has reached its maximum student capacity and is now full.', 'danger')
            return redirect(url_for('student.exam_slots', exam_id=exam_id))

        cursor.execute("""
            INSERT INTO bookings (slot_id, student_id, examination_id, status)
            VALUES (?, ?, ?, 'booked')
        """, (slot_id, student_id, exam_id))

        cursor.execute("""
            UPDATE slots SET booked_count = booked_count + 1 WHERE id = ?
        """, (slot_id,))

        db.commit()
        flash(f"Slot successfully booked for '{slot['exam_title']}'!", 'success')
        return redirect(url_for('student.my_bookings'))

    except Exception as e:
        db.rollback()
        flash(f"Booking could not be completed: {str(e)}", 'danger')
        return redirect(url_for('student.browse_exams'))

@student_bp.route('/bookings')
@role_required('student')
def my_bookings():
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.id AS booking_id, b.status, b.booked_at, b.cancelled_at,
               s.id AS slot_id, s.start_time, s.end_time, s.location_or_link,
               e.id AS exam_id, e.title AS exam_title, e.cancellation_deadline,
               c.course_code, c.course_name,
               ex.full_name AS examiner_name, ex.email AS examiner_email
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE b.student_id = ?
        ORDER BY s.start_time DESC
    """, (student_id,))
    all_bookings = cursor.fetchall()

    now_iso = datetime.now().isoformat()
    return render_template('student/my_bookings.html', bookings=all_bookings, now_iso=now_iso)

@student_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@role_required('student')
def cancel_booking(booking_id):
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
            SELECT b.*, e.cancellation_deadline, e.title AS exam_title, s.id AS slot_id
            FROM bookings b
            JOIN examinations e ON b.examination_id = e.id
            JOIN slots s ON b.slot_id = s.id
            WHERE b.id = ? AND b.student_id = ?
        """, (booking_id, student_id))
        booking = cursor.fetchone()

        if not booking:
            flash('Booking record not found or unauthorized.', 'danger')
            return redirect(url_for('student.my_bookings'))

        if booking['status'] != 'booked':
            flash('Only active bookings can be cancelled.', 'warning')
            return redirect(url_for('student.my_bookings'))

        now_dt = datetime.now()
        deadline_dt = datetime.fromisoformat(booking['cancellation_deadline'])

        if now_dt > deadline_dt:
            flash(f"Cancellation deadline ({booking['cancellation_deadline']}) has passed. You cannot cancel this booking.", 'danger')
            return redirect(url_for('student.my_bookings'))

        cursor.execute("""
            UPDATE bookings
            SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (booking_id,))

        cursor.execute("""
            UPDATE slots SET booked_count = booked_count - 1 WHERE id = ?
        """, (booking['slot_id'],))

        db.commit()
        flash(f"Booking for '{booking['exam_title']}' has been cancelled. Your slot seat is released.", 'info')
        return redirect(url_for('student.my_bookings'))

    except Exception as e:
        db.rollback()
        flash(f"Error cancelling booking: {str(e)}", 'danger')
        return redirect(url_for('student.my_bookings'))

@student_bp.route('/results')
@role_required('student')
def my_results():
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.id AS booking_id, b.status AS booking_status,
               e.id AS exam_id, e.title AS exam_title, e.results_published,
               c.course_code, c.course_name,
               r.total_max_marks,
               ev.id AS evaluation_id, ev.total_marks_awarded, ev.general_remarks, ev.evaluated_at,
               ex.full_name AS examiner_name
        FROM bookings b
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN slots s ON b.slot_id = s.id
        JOIN users ex ON s.examiner_id = ex.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        LEFT JOIN evaluations ev ON b.id = ev.booking_id
        WHERE b.student_id = ? AND b.status IN ('booked', 'completed')
        ORDER BY b.booked_at DESC
    """, (student_id,))
    exam_results = cursor.fetchall()

    return render_template('student/results.html', results=exam_results)

@student_bp.route('/evaluations/<int:evaluation_id>/scorecard')
@role_required('student')
def view_scorecard(evaluation_id):
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT ev.*, b.student_id,
               e.id AS exam_id, e.title AS exam_title, e.results_published,
               c.course_code, c.course_name,
               r.total_max_marks,
               ex.full_name AS examiner_name
        FROM evaluations ev
        JOIN bookings b ON ev.booking_id = b.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN users ex ON ev.examiner_id = ex.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        WHERE ev.id = ?
    """, (evaluation_id,))
    eval_row = cursor.fetchone()

    if not eval_row or eval_row['student_id'] != student_id:
        flash('Scorecard not found or unauthorized.', 'danger')
        abort(403)

    if not eval_row['results_published']:
        flash('The examination results have not been published yet.', 'warning')
        return redirect(url_for('student.my_results'))

    cursor.execute("""
        SELECT es.*, rc.criterion_name, rc.max_marks, rc.description AS criterion_desc
        FROM evaluation_scores es
        JOIN rubric_criteria rc ON es.criterion_id = rc.id
        WHERE es.evaluation_id = ?
        ORDER BY rc.id ASC
    """, (evaluation_id,))
    criterion_scores = cursor.fetchall()

    return render_template('student/scorecard.html', eval_row=eval_row, criteria=criterion_scores)

@student_bp.route('/profile', methods=['GET', 'POST'])
@role_required('student')
def edit_profile():
    student_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()

        if not full_name or not email:
            flash('All fields are required.', 'danger')
            return redirect(url_for('student.edit_profile'))

        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, student_id))
        if cursor.fetchone():
            flash('That email address is already in use by another account.', 'danger')
            return redirect(url_for('student.edit_profile'))

        cursor.execute("""
            UPDATE users SET full_name = ?, email = ?
            WHERE id = ?
        """, (full_name, email, student_id))
        db.commit()

        session['full_name'] = full_name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.dashboard'))

    cursor.execute("SELECT * FROM users WHERE id = ?", (student_id,))
    user = cursor.fetchone()
    return render_template('student/profile.html', user=user)
