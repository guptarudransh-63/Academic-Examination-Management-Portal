from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from datetime import datetime
from decorators import role_required
from database import get_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM courses")
    total_courses = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM examinations")
    total_exams = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'examiner' AND is_approved = 1")
    total_examiners = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'examiner' AND is_approved = 0")
    pending_examiners = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'student'")
    total_students = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM slots")
    total_slots = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE status = 'booked'")
    total_bookings = cursor.fetchone()['count']

    cursor.execute("""
        SELECT b.id, b.status, b.booked_at, 
               u.full_name AS student_name, u.username AS student_username,
               e.title AS exam_title, s.start_time, s.end_time,
               ex.full_name AS examiner_name
        FROM bookings b
        JOIN users u ON b.student_id = u.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN slots s ON b.slot_id = s.id
        JOIN users ex ON s.examiner_id = ex.id
        ORDER BY b.booked_at DESC
        LIMIT 5
    """)
    recent_bookings = cursor.fetchall()

    return render_template(
        'admin/dashboard.html',
        total_courses=total_courses,
        total_exams=total_exams,
        total_examiners=total_examiners,
        pending_examiners=pending_examiners,
        total_students=total_students,
        total_slots=total_slots,
        total_bookings=total_bookings,
        recent_bookings=recent_bookings
    )

@admin_bp.route('/courses', methods=['GET', 'POST'])
@role_required('admin')
def courses():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'danger')
            return redirect(url_for('admin.courses'))

        cursor.execute("SELECT id FROM courses WHERE course_code = ?", (course_code,))
        if cursor.fetchone():
            flash(f"A course with code '{course_code}' already exists.", 'danger')
            return redirect(url_for('admin.courses'))

        cursor.execute("""
            INSERT INTO courses (course_code, course_name, description)
            VALUES (?, ?, ?)
        """, (course_code, course_name, description))
        db.commit()

        flash(f"Course '{course_code} - {course_name}' created successfully.", 'success')
        return redirect(url_for('admin.courses'))

    cursor.execute("""
        SELECT c.*, COUNT(e.id) AS exam_count
        FROM courses c
        LEFT JOIN examinations e ON c.id = e.course_id
        GROUP BY c.id
        ORDER BY c.course_code ASC
    """)
    course_list = cursor.fetchall()
    return render_template('admin/courses.html', courses=course_list)

@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_course(course_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('admin.courses'))

    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        description = request.form.get('description', '').strip()

        if not course_code or not course_name:
            flash('Course Code and Course Name are required.', 'danger')
            return render_template('admin/edit_course.html', course=course)

        cursor.execute("SELECT id FROM courses WHERE course_code = ? AND id != ?", (course_code, course_id))
        if cursor.fetchone():
            flash(f"Course code '{course_code}' is already used by another course.", 'danger')
            return render_template('admin/edit_course.html', course=course)

        cursor.execute("""
            UPDATE courses 
            SET course_code = ?, course_name = ?, description = ?
            WHERE id = ?
        """, (course_code, course_name, description, course_id))
        db.commit()

        flash('Course updated successfully.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/edit_course.html', course=course)

@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@role_required('admin')
def delete_course(course_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT course_name FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('admin.courses'))

    cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    flash(f"Course '{course['course_name']}' and its related examinations have been deleted.", 'info')
    return redirect(url_for('admin.courses'))

@admin_bp.route('/examinations', methods=['GET', 'POST'])
@role_required('admin')
def examinations():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        slot_creation_start = request.form.get('slot_creation_start', '').strip()
        slot_creation_end = request.form.get('slot_creation_end', '').strip()
        booking_start = request.form.get('booking_start', '').strip()
        booking_end = request.form.get('booking_end', '').strip()
        cancellation_deadline = request.form.get('cancellation_deadline', '').strip()

        if not (course_id and title and slot_creation_start and slot_creation_end and 
                booking_start and booking_end and cancellation_deadline):
            flash('All examination fields and timeline dates are required.', 'danger')
            return redirect(url_for('admin.examinations'))

        try:
            sc_start = datetime.fromisoformat(slot_creation_start)
            sc_end = datetime.fromisoformat(slot_creation_end)
            bk_start = datetime.fromisoformat(booking_start)
            bk_end = datetime.fromisoformat(booking_end)
            cn_dead = datetime.fromisoformat(cancellation_deadline)
        except ValueError:
            flash('Invalid datetime format provided.', 'danger')
            return redirect(url_for('admin.examinations'))

        if sc_end <= sc_start:
            flash('Slot creation end must be after slot creation start.', 'danger')
            return redirect(url_for('admin.examinations'))

        if bk_end <= bk_start:
            flash('Booking end must be after booking start.', 'danger')
            return redirect(url_for('admin.examinations'))

        if cn_dead > bk_end:
            flash('Cancellation deadline cannot be after the booking window closes.', 'danger')
            return redirect(url_for('admin.examinations'))

        cursor.execute("""
            INSERT INTO examinations (
                course_id, title, description,
                slot_creation_start, slot_creation_end,
                booking_start, booking_end, cancellation_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (course_id, title, description, slot_creation_start, slot_creation_end,
              booking_start, booking_end, cancellation_deadline))
        exam_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO rubrics (examination_id, total_max_marks, description)
            VALUES (?, 100.0, 'Standard Rubric')
        """, (exam_id,))
        db.commit()

        flash(f"Examination '{title}' created successfully with default 100-mark rubric.", 'success')
        return redirect(url_for('admin.examinations'))

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_name,
               r.id AS rubric_id, r.total_max_marks,
               (SELECT COUNT(*) FROM slots WHERE examination_id = e.id) AS slot_count,
               (SELECT COUNT(*) FROM bookings WHERE examination_id = e.id AND status = 'booked') AS booked_count,
               (SELECT COUNT(*) FROM examiner_assignments WHERE examination_id = e.id) AS assigned_examiners_count
        FROM examinations e
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        ORDER BY e.created_at DESC
    """)
    exam_list = cursor.fetchall()

    cursor.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code ASC")
    course_options = cursor.fetchall()

    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")

    return render_template(
        'admin/examinations.html',
        examinations=exam_list,
        courses=course_options,
        now_iso=now_iso
    )

@admin_bp.route('/examinations/<int:exam_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_examination(exam_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM examinations WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        flash('Examination not found.', 'danger')
        return redirect(url_for('admin.examinations'))

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        slot_creation_start = request.form.get('slot_creation_start', '').strip()
        slot_creation_end = request.form.get('slot_creation_end', '').strip()
        booking_start = request.form.get('booking_start', '').strip()
        booking_end = request.form.get('booking_end', '').strip()
        cancellation_deadline = request.form.get('cancellation_deadline', '').strip()

        if not (course_id and title and slot_creation_start and slot_creation_end and 
                booking_start and booking_end and cancellation_deadline):
            flash('All examination fields and dates are required.', 'danger')
            return redirect(url_for('admin.edit_examination', exam_id=exam_id))

        cursor.execute("""
            UPDATE examinations
            SET course_id = ?, title = ?, description = ?,
                slot_creation_start = ?, slot_creation_end = ?,
                booking_start = ?, booking_end = ?, cancellation_deadline = ?
            WHERE id = ?
        """, (course_id, title, description, slot_creation_start, slot_creation_end,
              booking_start, booking_end, cancellation_deadline, exam_id))
        db.commit()

        flash('Examination details and timelines updated.', 'success')
        return redirect(url_for('admin.examinations'))

    cursor.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code ASC")
    course_options = cursor.fetchall()
    return render_template('admin/edit_examination.html', exam=exam, courses=course_options)

@admin_bp.route('/examinations/<int:exam_id>/delete', methods=['POST'])
@role_required('admin')
def delete_examination(exam_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM examinations WHERE id = ?", (exam_id,))
    db.commit()
    flash('Examination deleted successfully.', 'info')
    return redirect(url_for('admin.examinations'))

@admin_bp.route('/examinations/<int:exam_id>/toggle-publish', methods=['POST'])
@role_required('admin')
def toggle_publish_results(exam_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT results_published, title FROM examinations WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        flash('Examination not found.', 'danger')
        return redirect(url_for('admin.examinations'))

    new_status = 0 if exam['results_published'] else 1
    cursor.execute("UPDATE examinations SET results_published = ? WHERE id = ?", (new_status, exam_id))
    db.commit()

    status_str = "published (visible to students)" if new_status else "unpublished (hidden from students)"
    flash(f"Results for '{exam['title']}' are now {status_str}.", 'success')
    return redirect(url_for('admin.examinations'))

@admin_bp.route('/examinations/<int:exam_id>/examiners', methods=['GET', 'POST'])
@role_required('admin')
def assign_examiners(exam_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_name
        FROM examinations e
        JOIN courses c ON e.course_id = c.id
        WHERE e.id = ?
    """, (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        flash('Examination not found.', 'danger')
        return redirect(url_for('admin.examinations'))

    if request.method == 'POST':
        action = request.form.get('action')
        examiner_id = request.form.get('examiner_id')

        if action == 'assign' and examiner_id:
            cursor.execute("""
                INSERT OR IGNORE INTO examiner_assignments (examination_id, examiner_id)
                VALUES (?, ?)
            """, (exam_id, examiner_id))
            db.commit()
            flash('Examiner successfully assigned.', 'success')

        elif action == 'remove' and examiner_id:
            cursor.execute("""
                SELECT COUNT(*) AS count FROM slots 
                WHERE examination_id = ? AND examiner_id = ?
            """, (exam_id, examiner_id))
            slots_count = cursor.fetchone()['count']
            if slots_count > 0:
                flash('Cannot unassign this examiner because they have created slots for this exam. Reassign or delete their slots first.', 'danger')
            else:
                cursor.execute("""
                    DELETE FROM examiner_assignments
                    WHERE examination_id = ? AND examiner_id = ?
                """, (exam_id, examiner_id))
                db.commit()
                flash('Examiner assignment removed.', 'info')

        return redirect(url_for('admin.assign_examiners', exam_id=exam_id))

    cursor.execute("""
        SELECT u.id, u.full_name, u.username, u.email, ea.assigned_at,
               (SELECT COUNT(*) FROM slots WHERE examination_id = ? AND examiner_id = u.id) AS slot_count
        FROM examiner_assignments ea
        JOIN users u ON ea.examiner_id = u.id
        WHERE ea.examination_id = ?
        ORDER BY u.full_name ASC
    """, (exam_id, exam_id))
    assigned_examiners = cursor.fetchall()

    cursor.execute("""
        SELECT id, full_name, username, email
        FROM users
        WHERE role = 'examiner' AND is_approved = 1 AND is_active = 1
          AND id NOT IN (SELECT examiner_id FROM examiner_assignments WHERE examination_id = ?)
        ORDER BY full_name ASC
    """, (exam_id,))
    available_examiners = cursor.fetchall()

    return render_template(
        'admin/assign_examiners.html',
        exam=exam,
        assigned_examiners=assigned_examiners,
        available_examiners=available_examiners
    )

@admin_bp.route('/examinations/<int:exam_id>/rubric', methods=['GET', 'POST'])
@role_required('admin')
def manage_rubric(exam_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_name
        FROM examinations e
        JOIN courses c ON e.course_id = c.id
        WHERE e.id = ?
    """, (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        flash('Examination not found.', 'danger')
        return redirect(url_for('admin.examinations'))

    cursor.execute("SELECT * FROM rubrics WHERE examination_id = ?", (exam_id,))
    rubric = cursor.fetchone()
    if not rubric:
        cursor.execute("INSERT INTO rubrics (examination_id, total_max_marks) VALUES (?, 100.0)", (exam_id,))
        db.commit()
        cursor.execute("SELECT * FROM rubrics WHERE examination_id = ?", (exam_id,))
        rubric = cursor.fetchone()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_criterion':
            criterion_name = request.form.get('criterion_name', '').strip()
            max_marks = request.form.get('max_marks', '0').strip()
            description = request.form.get('description', '').strip()

            try:
                max_marks_float = float(max_marks)
                if max_marks_float <= 0:
                    raise ValueError()
            except ValueError:
                flash('Criterion maximum marks must be a positive number.', 'danger')
                return redirect(url_for('admin.manage_rubric', exam_id=exam_id))

            if not criterion_name:
                flash('Criterion name is required.', 'danger')
                return redirect(url_for('admin.manage_rubric', exam_id=exam_id))

            cursor.execute("""
                INSERT INTO rubric_criteria (rubric_id, criterion_name, max_marks, description)
                VALUES (?, ?, ?, ?)
            """, (rubric['id'], criterion_name, max_marks_float, description))
            db.commit()
            flash(f"Criterion '{criterion_name}' ({max_marks_float} marks) added to rubric.", 'success')

        elif action == 'update_total':
            total_max = request.form.get('total_max_marks', '100').strip()
            try:
                total_float = float(total_max)
                if total_float <= 0:
                    raise ValueError()
                cursor.execute("UPDATE rubrics SET total_max_marks = ? WHERE id = ?", (total_float, rubric['id']))
                db.commit()
                flash('Rubric total marks updated.', 'success')
            except ValueError:
                flash('Total marks must be a positive number.', 'danger')

        return redirect(url_for('admin.manage_rubric', exam_id=exam_id))

    cursor.execute("SELECT * FROM rubric_criteria WHERE rubric_id = ? ORDER BY id ASC", (rubric['id'],))
    criteria = cursor.fetchall()
    sum_criteria_marks = sum(c['max_marks'] for c in criteria)

    return render_template(
        'admin/rubric.html',
        exam=exam,
        rubric=rubric,
        criteria=criteria,
        sum_criteria_marks=sum_criteria_marks
    )

@admin_bp.route('/rubric/criteria/<int:criterion_id>/delete', methods=['POST'])
@role_required('admin')
def delete_criterion(criterion_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT rc.*, r.examination_id 
        FROM rubric_criteria rc
        JOIN rubrics r ON rc.rubric_id = r.id
        WHERE rc.id = ?
    """, (criterion_id,))
    crit = cursor.fetchone()
    if not crit:
        flash('Criterion not found.', 'danger')
        return redirect(url_for('admin.examinations'))

    exam_id = crit['examination_id']
    cursor.execute("DELETE FROM rubric_criteria WHERE id = ?", (criterion_id,))
    db.commit()

    flash('Criterion removed.', 'info')
    return redirect(url_for('admin.manage_rubric', exam_id=exam_id))

@admin_bp.route('/users')
@role_required('admin')
def users_list():
    db = get_db()
    cursor = db.cursor()

    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()

    sql = "SELECT * FROM users WHERE role != 'admin'"
    params = []

    if role_filter:
        sql += " AND role = ?"
        params.append(role_filter)

    if status_filter == 'pending':
        sql += " AND role = 'examiner' AND is_approved = 0"
    elif status_filter == 'approved':
        sql += " AND is_approved = 1"

    if search_query:
        sql += " AND (username LIKE ? OR full_name LIKE ? OR email LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    sql += " ORDER BY role ASC, is_approved ASC, created_at DESC"
    cursor.execute(sql, tuple(params))
    users = cursor.fetchall()

    return render_template(
        'admin/users.html',
        users=users,
        role_filter=role_filter,
        status_filter=status_filter,
        search_query=search_query
    )

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@role_required('admin')
def approve_examiner(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'examiner'", (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('Examiner not found.', 'danger')
        return redirect(url_for('admin.users_list'))

    cursor.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
    db.commit()

    flash(f"Examiner '{user['full_name']}' has been approved and can now log in.", 'success')
    return redirect(url_for('admin.users_list', status='pending'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@role_required('admin')
def reject_examiner(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'examiner'", (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('Examiner not found.', 'danger')
        return redirect(url_for('admin.users_list'))

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    flash(f"Examiner registration for '{user['full_name']}' rejected and removed.", 'info')
    return redirect(url_for('admin.users_list', status='pending'))

@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@role_required('admin')
def toggle_user_active(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user or user['role'] == 'admin':
        flash('Invalid user operation.', 'danger')
        return redirect(url_for('admin.users_list'))

    new_active = 0 if user['is_active'] else 1
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_active, user_id))
    db.commit()

    action_word = "activated" if new_active else "deactivated"
    flash(f"User '{user['full_name']}' account {action_word}.", 'success')
    return redirect(url_for('admin.users_list'))

@admin_bp.route('/bookings')
@role_required('admin')
def bookings_list():
    db = get_db()
    cursor = db.cursor()

    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    exam_filter = request.args.get('exam_id', '').strip()

    sql = """
        SELECT b.id, b.status, b.booked_at, b.cancelled_at,
               u.id AS student_id, u.full_name AS student_name, u.username AS student_username, u.email AS student_email,
               e.id AS exam_id, e.title AS exam_title, c.course_code,
               s.id AS slot_id, s.start_time, s.end_time, s.capacity, s.booked_count,
               ex.id AS examiner_id, ex.full_name AS examiner_name
        FROM bookings b
        JOIN users u ON b.student_id = u.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        JOIN slots s ON b.slot_id = s.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        sql += " AND b.status = ?"
        params.append(status_filter)

    if exam_filter:
        sql += " AND b.examination_id = ?"
        params.append(exam_filter)

    if search_query:
        sql += """ AND (
            u.full_name LIKE ? OR u.username LIKE ? OR u.email LIKE ? 
            OR ex.full_name LIKE ? OR e.title LIKE ? OR CAST(b.id AS TEXT) LIKE ?
        )"""
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard, wildcard, wildcard])

    sql += " ORDER BY b.booked_at DESC"
    cursor.execute(sql, tuple(params))
    bookings = cursor.fetchall()

    cursor.execute("SELECT id, title FROM examinations ORDER BY title ASC")
    all_exams = cursor.fetchall()

    return render_template(
        'admin/bookings.html',
        bookings=bookings,
        exams=all_exams,
        search_query=search_query,
        status_filter=status_filter,
        exam_filter=exam_filter
    )

@admin_bp.route('/bookings/<int:booking_id>/reschedule', methods=['GET', 'POST'])
@role_required('admin')
def reschedule_booking(booking_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.*, u.full_name AS student_name, e.title AS exam_title,
               s.start_time, s.end_time, ex.full_name AS current_examiner
        FROM bookings b
        JOIN users u ON b.student_id = u.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN slots s ON b.slot_id = s.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE b.id = ?
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('admin.bookings_list'))

    if booking['status'] != 'booked':
        flash('Only active bookings can be rescheduled.', 'warning')
        return redirect(url_for('admin.bookings_list'))

    if request.method == 'POST':
        new_slot_id = request.form.get('new_slot_id')
        reason = request.form.get('reason', '').strip()

        if not new_slot_id:
            flash('Please select a new slot.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking_id))

        cursor.execute("SELECT * FROM slots WHERE id = ? AND examination_id = ?", (new_slot_id, booking['examination_id']))
        new_slot = cursor.fetchone()

        if not new_slot:
            flash('Selected slot is invalid.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking_id))

        if int(new_slot['id']) == int(booking['slot_id']):
            flash('The new slot cannot be the current slot.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking_id))

        if new_slot['booked_count'] >= new_slot['capacity']:
            flash('The target slot is already at full capacity.', 'danger')
            return redirect(url_for('admin.reschedule_booking', booking_id=booking_id))

        try:
            old_slot_id = booking['slot_id']
            cursor.execute("UPDATE bookings SET slot_id = ? WHERE id = ?", (new_slot_id, booking_id))
            cursor.execute("UPDATE slots SET booked_count = booked_count - 1 WHERE id = ?", (old_slot_id,))
            cursor.execute("UPDATE slots SET booked_count = booked_count + 1 WHERE id = ?", (new_slot_id,))

            cursor.execute("""
                INSERT INTO reschedule_logs (booking_id, old_slot_id, new_slot_id, changed_by, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (booking_id, old_slot_id, new_slot_id, session.get('user_id'), reason or 'Administrative reschedule'))

            db.commit()
            flash(f"Booking #{booking_id} successfully rescheduled.", 'success')
            return redirect(url_for('admin.bookings_list'))

        except Exception as e:
            db.rollback()
            flash(f"Error rescheduling booking: {str(e)}", 'danger')

    cursor.execute("""
        SELECT s.*, ex.full_name AS examiner_name
        FROM slots s
        JOIN users ex ON s.examiner_id = ex.id
        WHERE s.examination_id = ? AND s.id != ? AND s.booked_count < s.capacity
        ORDER BY s.start_time ASC
    """, (booking['examination_id'], booking['slot_id']))
    available_slots = cursor.fetchall()

    return render_template('admin/reschedule.html', booking=booking, available_slots=available_slots)

@admin_bp.route('/slots/<int:slot_id>/reassign', methods=['GET', 'POST'])
@role_required('admin')
def reassign_slot_examiner(slot_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT s.*, e.title AS exam_title, ex.full_name AS current_examiner_name
        FROM slots s
        JOIN examinations e ON s.examination_id = e.id
        JOIN users ex ON s.examiner_id = ex.id
        WHERE s.id = ?
    """, (slot_id,))
    slot = cursor.fetchone()

    if not slot:
        flash('Slot not found.', 'danger')
        return redirect(url_for('admin.bookings_list'))

    if request.method == 'POST':
        new_examiner_id = request.form.get('new_examiner_id')
        reason = request.form.get('reason', '').strip()

        if not new_examiner_id or int(new_examiner_id) == int(slot['examiner_id']):
            flash('Please select a different examiner.', 'danger')
            return redirect(url_for('admin.reassign_slot_examiner', slot_id=slot_id))

        cursor.execute("SELECT * FROM users WHERE id = ? AND role = 'examiner' AND is_approved = 1", (new_examiner_id,))
        new_examiner = cursor.fetchone()
        if not new_examiner:
            flash('Selected examiner is not eligible.', 'danger')
            return redirect(url_for('admin.reassign_slot_examiner', slot_id=slot_id))

        cursor.execute("UPDATE slots SET examiner_id = ? WHERE id = ?", (new_examiner_id, slot_id))
        cursor.execute("""
            INSERT OR IGNORE INTO examiner_assignments (examination_id, examiner_id)
            VALUES (?, ?)
        """, (slot['examination_id'], new_examiner_id))
        db.commit()

        flash(f"Slot #{slot_id} reassigned to {new_examiner['full_name']}.", 'success')
        return redirect(url_for('admin.bookings_list'))

    cursor.execute("""
        SELECT id, full_name, email
        FROM users
        WHERE role = 'examiner' AND is_approved = 1 AND is_active = 1 AND id != ?
        ORDER BY full_name ASC
    """, (slot['examiner_id'],))
    eligible_examiners = cursor.fetchall()

    return render_template('admin/reassign_examiner.html', slot=slot, examiners=eligible_examiners)
