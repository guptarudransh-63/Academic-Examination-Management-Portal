# Examination Management Portal (EMP)
**Course:** Modern Application Development - 1 (MAD-1), September 2026 Term

---

## 1. Project Overview
The Examination Management Portal is an educational web application built with Python Flask, Jinja2, Bootstrap 5, and SQLite. It provides end-to-end management of institutional examinations, slot scheduling, examiner availability, student bookings, rubric-based evaluations, and published marks across three distinct roles:
1. **Admin**: Manages courses, examinations, and rubrics; approves examiner registration requests; controls operational windows; and performs administrative emergency overrides (rescheduling bookings and reassigning examiners).
2. **Examiner**: Schedules exam slots within the permitted slot-creation window; views booked students; and evaluates students against multi-criteria rubrics.
3. **Student**: Searches/filters examinations; reserves available slots; manages bookings and cancellations before deadlines; and reviews official published marks and feedback.

---

## 2. Technology Stack & Constraints Adherence
- **Backend**: Python 3.14 with Flask 3.1
- **Templating**: Jinja2 (server-side rendering)
- **Frontend / Styling**: HTML5, CSS3, Bootstrap 5.3
- **Database**: SQLite 3 with `PRAGMA foreign_keys = ON;`
- **Security**: PBKDF2 password hashing via `werkzeug.security`, HTTPOnly session cookies, server-side authorization guards.
- **Testing**: `pytest`

---

## 3. Local Setup & Execution Guide

### Prerequisites
- Python 3.10+ installed

### Step 1: Set Up Virtual Environment & Dependencies
```bash
# In the project directory:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Initialize Database and Seed Test Accounts
The database is created programmatically using `schema.sql` and `init_db.py`. To create all tables and populate realistic demonstration data:
```bash
python3 init_db.py --seed
```

### Step 3: Run the Application
```bash
python3 app.py
```
Open your web browser and navigate to: **`http://127.0.0.1:5001`**

### Step 4: Run the Automated Test Suite
To run all 14 unit and integration tests:
```bash
python3 -m pytest tests/ -v
```

---

## 4. Demonstration Accounts Seeded

| Role | Username | Password | Full Name | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@12345` | Portal Administrator | Pre-seeded superuser (no public registration) |
| **Examiner (Approved)** | `examiner1` | `Examiner@123` | Dr. Ramesh Sharma | Assigned to CS101 Viva; has created slots |
| **Examiner (Approved)** | `examiner2` | `Examiner@123` | Dr. Anita Rao | Assigned to CS101 Viva |
| **Examiner (Pending)** | `examiner_pending`| `Examiner@123` | Dr. Priya Patel | Awaiting Admin approval (tests approval queue) |
| **Student** | `student1` | `Student@123` | Aarav Mehta | Has booked & evaluated viva slot |
| **Student** | `student2` | `Student@123` | Sanya Verma | Has active upcoming booking |

---


## 5. Project Directory Structure

iitm project/
├── app.py                      # Flask Application factory & error handlers
├── config.py                   # Configuration & paths
├── database.py                 # SQLite helper with foreign keys & row factory
├── init_db.py                  # CLI script to programmatically create schema & seed accounts
├── schema.sql                  # Normalized SQLite DDL (11 tables)
├── decorators.py               # RBAC decorators (@login_required, @role_required)
├── routes/
│   ├── auth.py                 # Login, student/examiner registration, logout
│   ├── admin.py                # Courses, exams, rubrics, approvals, overrides
│   ├── examiner.py             # Assigned exams, slots, rosters, rubric evaluations
│   └── student.py              # Exam search, slot booking, cancellations, scorecards
├── templates/
│   ├── base.html               # Master layout with responsive navbar & alerts
│   ├── index.html              # Portal homepage
│   ├── auth/                   # Login and registration templates
│   ├── admin/                  # Admin management templates
│   ├── examiner/               # Examiner slot and grading templates
│   ├── student/                # Student discovery, booking, and scorecard templates
│   └── errors/                 # 403, 404, 500 error pages
├── static/
│   ├── css/custom.css          # Custom styling complementing Bootstrap
│   └── js/main.js              # Minimal UI enhancement scripts
├── tests/
│   ├── test_auth.py            # Auth & RBAC test suite (8 tests)
│   └── test_workflows.py       # Full business rules integration suite (6 tests)
├── requirements.txt            # Minimal dependencies
├── PROJECT_REPORT.md           # Formal 5-page submission project report
├── DEMO_OUTLINE.md             # 5-10 minute presentation video guide
└── VIVA_PREPARATION.md         # Viva Voce questions, explanations, and coding challenges

