# Examination Management Portal (EMP) - Project Report
**Course:** Modern Application Development - 1 (MAD-1), September 2026 Term

---

## 1. Student & Project Details
- **Student Name:** Ashish Gupta
- **Roll Number / Student ID:** [Your IITM Student ID]
- **Term:** September 2026
- **Project Title:** Examination Management Portal (EMP)
- **Problem Statement:**  
  Educational institutions require an organized, secure, and role-governed platform to coordinate course examinations. Key logistical challenges include: managing examiner availability, enforcing strict time windows for slot creation and student bookings, preventing slot capacity breaches and duplicate reservations during concurrent attempts, handling cancellation deadlines, conducting multi-criteria rubric evaluations, and controlling the confidentiality of exam marks until official administrative release.

---

## 2. Approach to the Problem
The portal was designed following a modular, server-rendered architectural model using standard Python Flask, Jinja2, Bootstrap 5, and SQLite:

1. **Strict Role-Based Access Control (RBAC):**
   - Three roles exist: **Admin**, **Examiner**, and **Student**.
   - Custom Python decorators (`@login_required`, `@role_required`) protect every backend route.
   - Public registration is allowed only for Students and Examiners. Newly registered examiners are held in an inactive state (`is_approved = 0`) until verified and approved by the Admin.
   - The Admin account is pre-seeded via a secure initialization script without public registration.

2. **Normalized Relational Schema & Database Integrity:**
   - Designed 11 normalized tables in SQLite with explicit foreign keys enabled via `PRAGMA foreign_keys = ON;`.
   - Used SQLite's partial unique index:
     ```sql
     CREATE UNIQUE INDEX idx_active_booking ON bookings(examination_id, student_id) WHERE status = 'booked';
     ```
     This strictly prevents multiple simultaneous bookings by a student for the same examination while preserving cancelled historical records.

3. **Concurrency Safety & Atomic Reservations:**
   - Slot reservations and cancellations use SQLite immediate transactions (`BEGIN IMMEDIATE`) on the backend.
   - The capacity check (`booked_count < capacity`) and seat increment happen inside the transaction, eliminating race conditions.

4. **Multi-Criteria Rubric Evaluations:**
   - Every examination can have an associated rubric with customizable criteria and maximum marks.
   - Examiners evaluate students booked into their own slots with criterion-by-criterion marks and remarks.
   - Results remain confidential until toggled to published by the Administrator.

---

## 3. AI / LLM Usage Declaration
- **Declaration Statement:**  
  In compliance with academic integrity guidelines, AI tools (Google Antigravity / Gemini) were utilized as a pair-programming mentor during development.
- **Nature of AI Assistance:**
  - Structuring the phased milestone development roadmap.
  - Formulating the normalized SQLite relational schema and SQL DDL constraints.
  - Designing comprehensive automated test scenarios (`pytest`) for edge cases.
  - Assisting in debugging Jinja2 template rendering and CSS layouts.
- **Student Understanding & Defense:**  
  All code, database operations, business logic, route handlers, and tests were written, reviewed, tested, and understood by the student. The student is prepared to explain, modify, and defend every component during the viva voce.

---

## 4. Frameworks & Libraries Used
- **Backend Framework:** Flask (v3.1.3)
- **Template Engine:** Jinja2 (v3.1.6)
- **UI & Responsive Layouts:** Bootstrap 5.3 & Custom CSS
- **Database Engine:** SQLite 3 (built-in standard library)
- **Cryptography & Security:** Werkzeug (`generate_password_hash`, `check_password_hash` using PBKDF2 with SHA-256)
- **Test Automation:** Pytest (v9.1.1)

---

## 5. Entity-Relationship (ER) Diagram

```
+---------------------+             +--------------------------+
|        users        |             |         courses          |
+---------------------+             +--------------------------+
| id (PK)             |             | id (PK)                  |
| username (UQ)       |             | course_code (UQ)         |
| password_hash       |             | course_name              |
| full_name           |             | description              |
| email (UQ)          |             +------------+-------------+
| role                |                          | 1
| is_approved         |                          |
| is_active           |                          | M
+----------+----------+             +------------v-------------+
           | 1                      |       examinations       |
           |                        +--------------------------+
           |                        | id (PK)                  |
           |                        | course_id (FK)           |
           +----------+             | title                    |
           |          |             | slot_creation_start      |
           |          |             | slot_creation_end        |
           |          |             | booking_start            |
           |          |             | booking_end              |
           |          |             | cancellation_deadline    |
           |          |             | results_published        |
           |          |             +----+------------------+--+
           |          |                  | 1                | 1
           |          v M                |                  |
           |  +-------+------------+     |                  | M
           |  |examiner_assignments|     |                  |
           |  +--------------------+     |                  |
           |  | exam_id (FK)       |     |                  |
           |  | examiner_id (FK)   |     |                  |
           |  +--------------------+     |                  |
           |                             | 1                |
           |                             v                  |
           |                        +----+----+             |
           |                        | rubrics |             |
           |                        +----+----+             |
           |                             | 1                |
           |                             v M                |
           |                    +--------+---------+        |
           |                    | rubric_criteria  |        |
           |                    +--------+---------+        |
           |                             | 1                |
           | M                           |                  v
+----------v----------+                  |            +-----+-----+
|        slots        |                  |            |  bookings |
+---------------------+                  |            +-----+-----+
| id (PK)             |                  |            | id (PK)   |
| exam_id (FK)        |                  |            | slot_id   |
| examiner_id (FK)    |                  |            | student_id|
| start_time, end_time|                  |            | status    |
| capacity            |                  |            +-----+-----+
| booked_count        |                  |                  | 1
+----------+----------+                  |                  |
           | 1                           |                  v 1
           | M                           |            +-----+-----+
           +-----------------------------+----------->|evaluations|
                                         |            +-----+-----+
                                         |                  | 1
                                         v M                v M
                                  +------+------------------+-----+
                                  |       evaluation_scores       |
                                  +-------------------------------+
                                  | eval_id (FK), criterion_id(FK)|
                                  | marks_awarded, remarks        |
                                  +-------------------------------+
```

---

## 6. Route & Endpoint Catalog

| Endpoint Route | HTTP Method | Role Access | Description |
| :--- | :--- | :--- | :--- |
| `/` | GET | Public | Portal landing page / role redirection |
| `/auth/login` | GET, POST | Public | Authenticates users across all roles |
| `/auth/register/student` | GET, POST | Public | Student self-registration |
| `/auth/register/examiner`| GET, POST | Public | Examiner self-registration (pending approval) |
| `/auth/logout` | GET | Authenticated | Clears session |
| `/admin/dashboard` | GET | Admin | System statistics overview |
| `/admin/courses` | GET, POST | Admin | List and create courses |
| `/admin/courses/<id>/edit`| GET, POST | Admin | Edit course code and details |
| `/admin/courses/<id>/delete`| POST | Admin | Delete course |
| `/admin/examinations` | GET, POST | Admin | List and schedule exams with time windows |
| `/admin/examinations/<id>/edit`| GET, POST | Admin | Update exam dates and windows |
| `/admin/examinations/<id>/assign-examiners`| GET, POST | Admin | Assign/unassign examiners to exams |
| `/admin/examinations/<id>/rubric`| GET, POST | Admin | Configure rubric criteria and max marks |
| `/admin/examinations/<id>/toggle-publish`| POST | Admin | Toggle publication of student results |
| `/admin/users` | GET | Admin | Search users and filter pending examiners |
| `/admin/users/<id>/approve`| POST | Admin | Approve pending examiner |
| `/admin/bookings` | GET | Admin | View/search all student bookings |
| `/admin/bookings/<id>/reschedule`| GET, POST | Admin | Reschedule a booking to an alternative slot |
| `/admin/slots/<id>/reassign-examiner`| GET, POST | Admin | Change assigned examiner for a slot |
| `/examiner/dashboard` | GET | Examiner | Examiner overview and metrics |
| `/examiner/examinations`| GET | Examiner | View assigned examinations |
| `/examiner/slots` | GET, POST | Examiner | Create slots within slot-creation window |
| `/examiner/slots/<id>/delete`| POST | Examiner | Remove slot (only if 0 bookings) |
| `/examiner/slots/<id>/students`| GET | Examiner | View booked students roster for slot |
| `/examiner/bookings/<id>/evaluate`| GET, POST | Examiner | Evaluate student against rubric criteria |
| `/student/dashboard` | GET | Student | Student schedule & results overview |
| `/student/exams` | GET | Student | Browse and filter available exams |
| `/student/exams/<id>/slots`| GET | Student | View slots for exam |
| `/student/slots/<id>/book` | POST | Student | Reserve slot (concurrency-safe) |
| `/student/bookings` | GET | Student | View active schedule and booking history |
| `/student/bookings/<id>/cancel`| POST | Student | Cancel booking before deadline |
| `/student/results` | GET | Student | View published results |
| `/student/results/<id>/scorecard`| GET | Student | Detailed rubric scorecard |
| `/student/profile` | GET, POST | Student | Edit full name and email |

---

## 7. Demonstration Video Link
- **Demo Video URL:** `https://youtu.be/your-video-link-here` *(Record and insert link prior to final submission)*
