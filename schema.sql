 PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'examiner', 'student')),
    is_approved INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT UNIQUE NOT NULL,
    course_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS examinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    slot_creation_start TEXT NOT NULL,
    slot_creation_end TEXT NOT NULL,
    booking_start TEXT NOT NULL,
    booking_end TEXT NOT NULL,
    cancellation_deadline TEXT NOT NULL,
    results_published INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS examiner_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    examiner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(examination_id, examiner_id)
);

CREATE TABLE IF NOT EXISTS rubrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    examination_id INTEGER UNIQUE NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    total_max_marks REAL NOT NULL DEFAULT 100.0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rubric_id INTEGER NOT NULL REFERENCES rubrics(id) ON DELETE CASCADE,
    criterion_name TEXT NOT NULL,
    max_marks REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    examiner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 1,
    booked_count INTEGER NOT NULL DEFAULT 0,
    location_or_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_id INTEGER NOT NULL REFERENCES slots(id) ON DELETE RESTRICT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'booked' CHECK(status IN ('booked', 'cancelled', 'completed', 'rescheduled')),
    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMP NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_active_booking 
ON bookings(examination_id, student_id) 
WHERE status = 'booked';

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    examiner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    total_marks_awarded REAL NOT NULL,
    general_remarks TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    criterion_id INTEGER NOT NULL REFERENCES rubric_criteria(id) ON DELETE RESTRICT,
    marks_awarded REAL NOT NULL,
    remarks TEXT,
    UNIQUE(evaluation_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS reschedule_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    old_slot_id INTEGER REFERENCES slots(id),
    new_slot_id INTEGER REFERENCES slots(id),
    changed_by INTEGER NOT NULL REFERENCES users(id),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
