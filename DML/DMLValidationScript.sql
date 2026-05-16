-- SECTION 1 — ROW COUNT PER TABLE

USE tutor_matching_db;
SELECT 'Categories'    AS table_name, COUNT(*) AS row_count FROM Categories
UNION ALL
SELECT 'Students',      COUNT(*) FROM Students
UNION ALL
SELECT 'Tutors',        COUNT(*) FROM Tutors
UNION ALL
SELECT 'Subjects',      COUNT(*) FROM Subjects
UNION ALL
SELECT 'Tutor_Subjects',COUNT(*) FROM Tutor_Subjects
UNION ALL
SELECT 'Matches',       COUNT(*) FROM Matches
UNION ALL
SELECT 'Bookings',      COUNT(*) FROM Bookings
UNION ALL
SELECT 'Sessions',      COUNT(*) FROM Sessions
UNION ALL
SELECT 'Payments',      COUNT(*) FROM Payments
UNION ALL
SELECT 'Reviews',       COUNT(*) FROM Reviews;
 
-- SECTION 2 — NULL CHECK 
 
SELECT student_id, full_name, email
FROM   Students
WHERE  full_name IS NULL
   OR  email     IS NULL;
 
SELECT tutor_id, full_name, email, hourly_rate
FROM   Tutors
WHERE  full_name    IS NULL
   OR  email        IS NULL
   OR  hourly_rate  IS NULL;
 
SELECT subject_id
FROM   Subjects
WHERE  subject_name IS NULL
   OR  category_id  IS NULL;
 
SELECT session_id
FROM   Sessions
WHERE  match_id     IS NULL
   OR  session_date IS NULL;
 
SELECT payment_id
FROM   Payments
WHERE  session_id IS NULL
   OR  amount     IS NULL;
 
SELECT review_id
FROM   Reviews
WHERE  student_id IS NULL
   OR  tutor_id   IS NULL
   OR  rating     IS NULL;
 
 
-- SECTION 3 — FOREIGN KEY INTEGRITY CHECKS
 
-- Subjects → Categories
SELECT sub.subject_id, sub.subject_name, sub.category_id
FROM   Subjects sub
LEFT JOIN Categories c ON sub.category_id = c.category_id
WHERE  c.category_id IS NULL;
 
-- Tutor_Subjects → Tutors and Subjects
SELECT ts.tutor_subject_id
FROM   Tutor_Subjects ts
LEFT JOIN Tutors   t ON ts.tutor_id   = t.tutor_id
LEFT JOIN Subjects s ON ts.subject_id = s.subject_id
WHERE  t.tutor_id   IS NULL
   OR  s.subject_id IS NULL;
 
-- Matches → Students and Tutors
SELECT m.match_id
FROM   Matches m
LEFT JOIN Students st ON m.student_id = st.student_id
LEFT JOIN Tutors   t  ON m.tutor_id   = t.tutor_id
WHERE  st.student_id IS NULL
   OR  t.tutor_id    IS NULL;
 
-- Bookings → Students, Tutors, Subjects
SELECT b.booking_id
FROM   Bookings b
LEFT JOIN Students st ON b.student_id = st.student_id
LEFT JOIN Tutors   t  ON b.tutor_id   = t.tutor_id
LEFT JOIN Subjects s  ON b.subject_id = s.subject_id
WHERE  st.student_id IS NULL
   OR  t.tutor_id    IS NULL
   OR  s.subject_id  IS NULL;
 
-- Sessions → Matches
SELECT s.session_id
FROM   Sessions s
LEFT JOIN Matches m ON s.match_id = m.match_id
WHERE  m.match_id IS NULL;
 
-- Payments → Sessions (also checks UNIQUE session_id)
SELECT p.payment_id
FROM   Payments p
LEFT JOIN Sessions s ON p.session_id = s.session_id
WHERE  s.session_id IS NULL;
 
-- Duplicate payment per session
SELECT session_id, COUNT(*) AS cnt
FROM   Payments
GROUP  BY session_id
HAVING cnt > 1;
 
-- Reviews → Students and Tutors
SELECT r.review_id
FROM   Reviews r
LEFT JOIN Students st ON r.student_id = st.student_id
LEFT JOIN Tutors   t  ON r.tutor_id   = t.tutor_id
WHERE  st.student_id IS NULL
   OR  t.tutor_id    IS NULL;
 
-- Duplicate (student_id, tutor_id) in Reviews
SELECT student_id, tutor_id, COUNT(*) AS cnt
FROM   Reviews
GROUP  BY student_id, tutor_id
HAVING cnt > 1;
 
 
-- SECTION 4 — CHECK CONSTRAINT VALIDATION
 
-- Tutors: hourly_rate must be > 0
SELECT tutor_id, hourly_rate
FROM   Tutors
WHERE  hourly_rate <= 0;
 
-- Tutors: is_available must be 0 or 1
SELECT tutor_id, is_available
FROM   Tutors
WHERE  is_available NOT IN (0, 1);
 
-- Matches: status must be 'Active' or 'Closed'
SELECT match_id, status
FROM   Matches
WHERE  status NOT IN ('Active', 'Closed');
 
-- Bookings: status must be 'Pending', 'Confirmed', or 'Cancelled'
SELECT booking_id, status
FROM   Bookings
WHERE  status NOT IN ('Pending', 'Confirmed', 'Cancelled');
 
-- Sessions: duration_mins must be > 0
SELECT session_id, duration_mins
FROM   Sessions
WHERE  duration_mins <= 0;
 
-- Sessions: attendance must be 'Present', 'Absent', or 'Cancelled'
SELECT session_id, attendance
FROM   Sessions
WHERE  attendance NOT IN ('Present', 'Absent', 'Cancelled');
 
-- Payments: amount must be >= 0
SELECT payment_id, amount
FROM   Payments
WHERE  amount < 0;
 
-- Payments: status must be 'Paid', 'Pending', or 'Due'
SELECT payment_id, status
FROM   Payments
WHERE  status NOT IN ('Paid', 'Pending', 'Due');
 
-- Reviews: rating must be between 1 and 5
SELECT review_id, rating
FROM   Reviews
WHERE  rating NOT BETWEEN 1 AND 5;