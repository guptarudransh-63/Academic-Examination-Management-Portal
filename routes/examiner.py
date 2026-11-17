from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from datetime import datetime
from decorators import role_required
from database import get_db

examiner_bp = Blueprint('examiner', __name__, url_prefix='/examiner')

@examiner_bp.route('/dashboard')
@role_required('examiner')
def dashboard():
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS count FROM examiner_assignments
        WHERE examiner_id = ?
    """, (examiner_id,))
    assigned_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT COUNT(*) AS count FROM slots
        WHERE examiner_id = ?
    """, (examiner_id,))
    slots_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT COUNT(b.id) AS count
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        WHERE s.examiner_id = ? AND b.status = 'booked'
    """, (examiner_id,))
    booked_students_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT COUNT(b.id) AS count
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        LEFT JOIN evaluations ev ON b.id = ev.booking_id
        WHERE s.examiner_id = ? AND b.status = 'booked' AND ev.id IS NULL
    """, (examiner_id,))
    pending_evaluations_count = cursor.fetchone()['count']

    cursor.execute("""
        SELECT s.*, e.title AS exam_title, c.course_code
        FROM slots s
        JOIN examinations e ON s.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        WHERE s.examiner_id = ?
        ORDER BY s.start_time ASC
        LIMIT 5
    """, (examiner_id,))
    upcoming_slots = cursor.fetchall()

    return render_template(
        'examiner/dashboard.html',
        assigned_count=assigned_count,
        slots_count=slots_count,
        booked_students_count=booked_students_count,
        pending_evaluations_count=pending_evaluations_count,
        upcoming_slots=upcoming_slots
    )

@examiner_bp.route('/examinations')
@role_required('examiner')
def assigned_exams():
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    now_str = datetime.now().isoformat()

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_name,
               r.total_max_marks,
               (SELECT COUNT(*) FROM slots WHERE examination_id = e.id AND examiner_id = ?) AS my_slots_count,
               (SELECT COUNT(b.id) FROM bookings b JOIN slots s ON b.slot_id = s.id 
                WHERE s.examination_id = e.id AND s.examiner_id = ? AND b.status = 'booked') AS my_booked_count
        FROM examiner_assignments ea
        JOIN examinations e ON ea.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        WHERE ea.examiner_id = ?
        ORDER BY e.created_at DESC
    """, (examiner_id, examiner_id, examiner_id))
    exams = cursor.fetchall()

    return render_template('examiner/examinations.html', exams=exams, now_str=now_str)

@examiner_bp.route('/slots', methods=['GET', 'POST'])
@role_required('examiner')
def slots():
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        exam_id = request.form.get('examination_id')
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        capacity = request.form.get('capacity', '1').strip()
        location_or_link = request.form.get('location_or_link', '').strip()

        if not exam_id or not start_time or not end_time or not capacity:
            flash('Examination, start time, end time, and capacity are required.', 'danger')
            return redirect(url_for('examiner.slots'))

        cursor.execute("""
            SELECT * FROM examiner_assignments
            WHERE examination_id = ? AND examiner_id = ?
        """, (exam_id, examiner_id))
        if not cursor.fetchone():
            flash('You are not assigned to conduct slots for this examination.', 'danger')
            return redirect(url_for('examiner.slots'))

        cursor.execute("SELECT * FROM examinations WHERE id = ?", (exam_id,))
        exam = cursor.fetchone()
        if not exam:
            flash('Examination not found.', 'danger')
            return redirect(url_for('examiner.slots'))

        try:
            slot_start_dt = datetime.fromisoformat(start_time)
            slot_end_dt = datetime.fromisoformat(end_time)
            cap_int = int(capacity)
            if cap_int < 1:
                raise ValueError()
        except ValueError:
            flash('Invalid date or capacity value (must be >= 1).', 'danger')
            return redirect(url_for('examiner.slots'))

        if slot_end_dt <= slot_start_dt:
            flash('Slot end time must be after slot start time.', 'danger')
            return redirect(url_for('examiner.slots'))

        now_dt = datetime.now()
        window_start = datetime.fromisoformat(exam['slot_creation_start'])
        window_end = datetime.fromisoformat(exam['slot_creation_end'])

        if not (window_start <= now_dt <= window_end):
            flash(f"Slot creation is only permitted between {exam['slot_creation_start']} and {exam['slot_creation_end']}.", 'danger')
            return redirect(url_for('examiner.slots'))

        cursor.execute("""
            INSERT INTO slots (examination_id, examiner_id, start_time, end_time, capacity, booked_count, location_or_link)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        """, (exam_id, examiner_id, start_time, end_time, cap_int, location_or_link))
        db.commit()

        flash('Examination slot created successfully.', 'success')
        return redirect(url_for('examiner.slots'))

    cursor.execute("""
        SELECT e.id, e.title, e.slot_creation_start, e.slot_creation_end, c.course_code
        FROM examiner_assignments ea
        JOIN examinations e ON ea.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        WHERE ea.examiner_id = ?
        ORDER BY e.title ASC
    """, (examiner_id,))
    assigned_exams_list = cursor.fetchall()

    cursor.execute("""
        SELECT s.*, e.title AS exam_title, c.course_code,
               e.slot_creation_start, e.slot_creation_end, e.booking_start
        FROM slots s
        JOIN examinations e ON s.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        WHERE s.examiner_id = ?
        ORDER BY s.start_time DESC
    """, (examiner_id,))
    examiner_slots = cursor.fetchall()

    now_iso = datetime.now().isoformat()
    return render_template(
        'examiner/slots.html',
        slots=examiner_slots,
        assigned_exams=assigned_exams_list,
        now_iso=now_iso
    )

@examiner_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
@role_required('examiner')
def delete_slot(slot_id):
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT s.*, e.slot_creation_start, e.slot_creation_end
        FROM slots s
        JOIN examinations e ON s.examination_id = e.id
        WHERE s.id = ? AND s.examiner_id = ?
    """, (slot_id, examiner_id))
    slot = cursor.fetchone()

    if not slot:
        flash('Slot not found or unauthorized.', 'danger')
        return redirect(url_for('examiner.slots'))

    if slot['booked_count'] > 0:
        flash('Cannot delete this slot because students have already booked it.', 'danger')
        return redirect(url_for('examiner.slots'))

    cursor.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    db.commit()

    flash('Examination slot removed successfully.', 'info')
    return redirect(url_for('examiner.slots'))

@examiner_bp.route('/slots/<int:slot_id>/students')
@role_required('examiner')
def slot_students(slot_id):
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT s.*, e.title AS exam_title, e.id AS exam_id, c.course_code, c.course_name
        FROM slots s
        JOIN examinations e ON s.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        WHERE s.id = ? AND s.examiner_id = ?
    """, (slot_id, examiner_id))
    slot = cursor.fetchone()

    if not slot:
        flash('Slot not found or unauthorized access.', 'danger')
        abort(403)

    cursor.execute("""
        SELECT b.id AS booking_id, b.status, b.booked_at,
               u.id AS student_id, u.full_name AS student_name, u.username AS student_username, u.email AS student_email,
               ev.id AS evaluation_id, ev.total_marks_awarded, ev.evaluated_at
        FROM bookings b
        JOIN users u ON b.student_id = u.id
        LEFT JOIN evaluations ev ON b.id = ev.booking_id
        WHERE b.slot_id = ? AND b.status IN ('booked', 'completed')
        ORDER BY u.full_name ASC
    """, (slot_id,))
    roster = cursor.fetchall()

    return render_template('examiner/roster.html', slot=slot, roster=roster)

@examiner_bp.route('/bookings/<int:booking_id>/evaluate', methods=['GET', 'POST'])
@role_required('examiner')
def evaluate_student(booking_id):
    examiner_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.*, u.full_name AS student_name, u.username AS student_username, u.email AS student_email,
               s.start_time, s.end_time, s.examiner_id,
               e.id AS exam_id, e.title AS exam_title, c.course_code, c.course_name,
               r.id AS rubric_id, r.total_max_marks
        FROM bookings b
        JOIN users u ON b.student_id = u.id
        JOIN slots s ON b.slot_id = s.id
        JOIN examinations e ON b.examination_id = e.id
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN rubrics r ON e.id = r.examination_id
        WHERE b.id = ?
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('examiner.dashboard'))

    if booking['examiner_id'] != examiner_id:
        flash('You are not authorized to evaluate this student.', 'danger')
        abort(403)

    if booking['status'] == 'cancelled':
        flash('Cannot evaluate a cancelled booking.', 'danger')
        return redirect(url_for('examiner.slot_students', slot_id=booking['slot_id']))

    cursor.execute("""
        SELECT * FROM rubric_criteria 
        WHERE rubric_id = ? 
        ORDER BY id ASC
    """, (booking['rubric_id'],))
    criteria = cursor.fetchall()

    cursor.execute("SELECT * FROM evaluations WHERE booking_id = ?", (booking_id,))
    existing_evaluation = cursor.fetchone()

    existing_scores = {}
    if existing_evaluation:
        cursor.execute("SELECT * FROM evaluation_scores WHERE evaluation_id = ?", (existing_evaluation['id'],))
        for score in cursor.fetchall():
            existing_scores[score['criterion_id']] = score

    if request.method == 'POST':
        general_remarks = request.form.get('general_remarks', '').strip()
        scores_to_save = []
        computed_total = 0.0
        validation_error = None

        if criteria:
            for crit in criteria:
                crit_id = crit['id']
                crit_max = crit['max_marks']
                val_str = request.form.get(f'crit_{crit_id}', '').strip()
                rem_str = request.form.get(f'rem_{crit_id}', '').strip()

                try:
                    score_val = float(val_str)
                    if score_val < 0 or score_val > crit_max:
                        validation_error = f"Score for '{crit['criterion_name']}' must be between 0 and {crit_max}."
                        break
                except ValueError:
                    validation_error = f"Please enter a valid numeric score for '{crit['criterion_name']}'."
                    break

                computed_total += score_val
                scores_to_save.append((crit_id, score_val, rem_str))
        else:
            total_val_str = request.form.get('total_marks', '0').strip()
            try:
                computed_total = float(total_val_str)
                if computed_total < 0 or computed_total > booking['total_max_marks']:
                    validation_error = f"Total marks must be between 0 and {booking['total_max_marks']}."
            except ValueError:
                validation_error = 'Please enter a valid numeric score.'

        if not validation_error and computed_total > booking['total_max_marks'] and criteria:
            validation_error = f"Total awarded marks ({computed_total}) exceed examination maximum ({booking['total_max_marks']})."

        if validation_error:
            flash(validation_error, 'danger')
            return render_template(
                'examiner/evaluate.html',
                booking=booking,
                criteria=criteria,
                existing_eval=existing_evaluation,
                existing_scores=existing_scores
            )

        try:
            if existing_evaluation:
                cursor.execute("""
                    UPDATE evaluations
                    SET total_marks_awarded = ?, general_remarks = ?, evaluated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (computed_total, general_remarks, existing_evaluation['id']))
                eval_id = existing_evaluation['id']
                cursor.execute("DELETE FROM evaluation_scores WHERE evaluation_id = ?", (eval_id,))
            else:
                cursor.execute("""
                    INSERT INTO evaluations (booking_id, examiner_id, total_marks_awarded, general_remarks)
                    VALUES (?, ?, ?, ?)
                """, (booking_id, examiner_id, computed_total, general_remarks))
                eval_id = cursor.lastrowid

            for crit_id, score_val, rem_str in scores_to_save:
                cursor.execute("""
                    INSERT INTO evaluation_scores (evaluation_id, criterion_id, marks_awarded, remarks)
                    VALUES (?, ?, ?, ?)
                """, (eval_id, crit_id, score_val, rem_str))

            cursor.execute("UPDATE bookings SET status = 'completed' WHERE id = ?", (booking_id,))
            db.commit()

            flash(f"Evaluation for {booking['student_name']} submitted successfully (Total: {computed_total}/{booking['total_max_marks']}).", 'success')
            return redirect(url_for('examiner.slot_students', slot_id=booking['slot_id']))
        except Exception as e:
            db.rollback()
            flash(f"Error saving evaluation: {str(e)}", 'danger')

    return render_template(
        'examiner/evaluate.html',
        booking=booking,
        criteria=criteria,
        existing_eval=existing_evaluation,
        existing_scores=existing_scores
    )
