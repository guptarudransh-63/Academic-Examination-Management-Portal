# Video Demonstration Outline (5–10 Minutes)
**Project:** Examination Management Portal (MAD-1, September 2026)

---

## Time Allocation Summary (Target: ~7 to 8 minutes)
1. **Introduction & Architecture Overview:** ~1.0 minute
2. **Administrator Role Demonstration:** ~2.5 minutes
3. **Examiner Role Demonstration:** ~2.0 minutes
4. **Student Role Demonstration:** ~2.0 minutes
5. **Automated Testing & Conclusion:** ~0.5 minute

---

## Scene-by-Scene Script

### Scene 1: Introduction (0:00 - 1:00)
- **What to show:** Terminal and project folder.
- **What to say:**
  > "Hello everyone. My name is Ashish Gupta. In this video, I will demonstrate my MAD-1 project: the Examination Management Portal. The project is built entirely using Python Flask, Jinja2 templates, Bootstrap 5, and SQLite with programmatic initialization. It enforces strict role-based access control across three user roles: Admin, Examiner, and Student."
- **Action:** Show `python3 init_db.py --seed` executing in terminal, then start `python3 app.py` and open `http://127.0.0.1:5001` in the browser.

### Scene 2: Administrator Workflow (1:00 - 3:30)
- **What to show:** Login as `admin` (`Admin@12345`).
- **Key Points to demonstrate:**
  1. **Dashboard Metrics:** Show total courses, examinations, examiners, students, slots, and bookings.
  2. **Examiner Approval Queue:** Navigate to *Users & Approvals*. Point out `examiner_pending` (Dr. Priya Patel). Click **Approve**. Explain that new examiners cannot log in until approved here.
  3. **Course & Examination Management:** Show `CS101` and create a new course or exam. Show how operational windows (Slot Creation Window, Student Booking Window, Cancellation Deadline) are configured.
  4. **Rubric Management:** Show the rubric for `CS101 End-Term Project Viva Voce` with its 3 criteria summing to 100 marks.
  5. **Administrative Search & Emergency Overrides:** Go to *All Bookings*. Search for student `Aarav Mehta`. Show the **Reschedule** feature where an admin can move a student to another available slot. Show the **Reassign Examiner** button.
  6. **Results Publication:** Show the toggle button to publish/hide exam results.

### Scene 3: Examiner Workflow (3:30 - 5:30)
- **What to show:** Logout and log in as `examiner1` (`Examiner@123`).
- **Key Points to demonstrate:**
  1. **Examiner Dashboard:** View assigned exams, total slots, booked students, and pending evaluations.
  2. **My Examinations & Slot Scheduling:** Show that slot creation is enabled only because the current time is within the exam's slot creation window. Create a new slot. Show that slots with 0 bookings can be deleted, while booked slots cannot be deleted.
  3. **Student Roster & Rubric Evaluation:** Click on *Roster* for a slot. View the booked student. Click **Evaluate Student**.
  4. **Evaluation Screen:** Demonstrate criterion-by-criterion grading. Explain that marks are validated so no criterion score can exceed its maximum and total marks cannot exceed the rubric maximum. Submit evaluation with remarks.
  5. **Authorization Security:** Explain that an examiner cannot access or evaluate students in another examiner's slots.

### Scene 4: Student Workflow (5:30 - 7:30)
- **What to show:** Logout and log in as `student1` (`Student@123`) or `student2` (`Student@123`).
- **Key Points to demonstrate:**
  1. **Student Dashboard:** View upcoming booked examination appointment banner.
  2. **Browse Examinations:** Search and filter exams by course code. Show status badges (Booking Open, Already Booked, Closed).
  3. **Slot Booking & Capacity Enforcement:** Click *View Slots & Book*. Show remaining seat counts. Explain that duplicate booking for the same exam is blocked and slot capacity is strictly enforced.
  4. **My Bookings & Cancellation:** Go to *My Bookings*. Show confirmed reservations. Click **Cancel Booking** on an upcoming slot. Explain that cancellation is permitted before the deadline and frees the seat immediately while preserving the historical cancelled record.
  5. **Published Results & Scorecard:** Go to *My Results*. Click **View Scorecard**. Show the detailed rubric breakdown with examiner comments and the print option. Explain that unpublished results remain hidden.

### Scene 5: Automated Test Suite & Conclusion (7:30 - 8:00)
- **What to show:** Terminal running `python3 -m pytest tests/ -v`.
- **What to say:**
  > "All 14 unit and integration tests pass cleanly, covering authentication, role-based authorization, timeline windows, booking capacity, duplicate booking prevention, cancellation deadlines, and rubric evaluations. Thank you."
