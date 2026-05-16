
-- SECTION 1 — LOAD DATA INFILE
-- Tables are loaded in FK-dependency order:
--   Categories → Students → Tutors → Subjects →
--   Tutor_Subjects → Matches → Bookings →
--   Sessions → Payments → Reviews

-- CREATE TABLE Categories (     category_id   INT AUTO_INCREMENT PRIMARY KEY,     category_name VARCHAR(100) NOT NULL UNIQUE,     description   TEXT );
-- CREATE TABLE Students (     student_id  INT AUTO_INCREMENT PRIMARY KEY,     full_name   VARCHAR(150) NOT NULL,     grade_level VARCHAR(50)  NOT NULL,     area        VARCHAR(100) NOT NULL,     phone       VARCHAR(20)  NOT NULL,     email       VARCHAR(150) NOT NULL UNIQUE,     created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,     INDEX idx_students_area (area) );
-- CREATE TABLE Tutors (     tutor_id      INT AUTO_INCREMENT PRIMARY KEY,     full_name     VARCHAR(150)   NOT NULL,     qualification VARCHAR(200)   NOT NULL,     area          VARCHAR(100)   NOT NULL,     phone         VARCHAR(20)    NOT NULL,     email         VARCHAR(150)   NOT NULL UNIQUE,     hourly_rate   DECIMAL(10, 2) NOT NULL CHECK (hourly_rate > 0),     is_available  TINYINT(1)     NOT NULL DEFAULT 1                       CHECK (is_available IN (0, 1)),     created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,     INDEX idx_tutors_area (area),     INDEX idx_tutors_available (is_available) );
-- CREATE TABLE Subjects (     subject_id   INT AUTO_INCREMENT PRIMARY KEY,     subject_name VARCHAR(150) NOT NULL UNIQUE,     category_id  INT          NOT NULL,     FOREIGN KEY (category_id) REFERENCES Categories(category_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_subjects_category (category_id) );
-- CREATE TABLE Tutor_Subjects (     tutor_subject_id INT AUTO_INCREMENT PRIMARY KEY,     tutor_id         INT NOT NULL,     subject_id       INT NOT NULL,     UNIQUE KEY uq_tutor_subject (tutor_id, subject_id),     FOREIGN KEY (tutor_id)   REFERENCES Tutors(tutor_id)         ON UPDATE CASCADE ON DELETE CASCADE,     FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id)         ON UPDATE CASCADE ON DELETE CASCADE,     INDEX idx_ts_tutor   (tutor_id),     INDEX idx_ts_subject (subject_id) );
-- CREATE TABLE Matches (     match_id   INT AUTO_INCREMENT PRIMARY KEY,     student_id INT         NOT NULL,     tutor_id   INT         NOT NULL,     match_date DATE        NOT NULL,     status     VARCHAR(10) NOT NULL DEFAULT 'Active'                    CHECK (status IN ('Active', 'Closed')),     FOREIGN KEY (student_id) REFERENCES Students(student_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     FOREIGN KEY (tutor_id)   REFERENCES Tutors(tutor_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_matches_student (student_id),     INDEX idx_matches_tutor   (tutor_id),     INDEX idx_matches_status  (status) );
-- CREATE TABLE Bookings (     booking_id     INT AUTO_INCREMENT PRIMARY KEY,     student_id     INT         NOT NULL,     tutor_id       INT         NOT NULL,     subject_id     INT         NOT NULL,     booking_date   DATE        NOT NULL,     preferred_time TIME        NOT NULL,     message        TEXT,     status         VARCHAR(15) NOT NULL DEFAULT 'Pending'                        CHECK (status IN ('Pending', 'Confirmed', 'Cancelled')),     created_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,     FOREIGN KEY (student_id) REFERENCES Students(student_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     FOREIGN KEY (tutor_id)   REFERENCES Tutors(tutor_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_bookings_student (student_id),     INDEX idx_bookings_tutor   (tutor_id),     INDEX idx_bookings_subject (subject_id),     INDEX idx_bookings_status  (status) );
-- CREATE TABLE Sessions (     session_id    INT AUTO_INCREMENT PRIMARY KEY,     match_id      INT         NOT NULL,     session_date  DATE        NOT NULL,     start_time    TIME        NOT NULL,     duration_mins INT         NOT NULL CHECK (duration_mins > 0),     attendance    VARCHAR(15) NOT NULL                       CHECK (attendance IN ('Present', 'Absent', 'Cancelled')),     FOREIGN KEY (match_id) REFERENCES Matches(match_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_sessions_match (match_id),     INDEX idx_sessions_date  (session_date) );
-- CREATE TABLE Payments (     payment_id   INT AUTO_INCREMENT PRIMARY KEY,     session_id   INT            NOT NULL UNIQUE,     amount       DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),     payment_date DATE           NOT NULL,     status       VARCHAR(10)    NOT NULL DEFAULT 'Pending'                      CHECK (status IN ('Paid', 'Pending', 'Due')),     FOREIGN KEY (session_id) REFERENCES Sessions(session_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_payments_status (status) );
-- CREATE TABLE Reviews (     review_id   INT AUTO_INCREMENT PRIMARY KEY,     student_id  INT         NOT NULL,     tutor_id    INT         NOT NULL,     rating      TINYINT     NOT NULL CHECK (rating BETWEEN 1 AND 5),     review_text TEXT,     review_date DATE        NOT NULL,     UNIQUE KEY uq_student_tutor_review (student_id, tutor_id),     FOREIGN KEY (student_id) REFERENCES Students(student_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     FOREIGN KEY (tutor_id)   REFERENCES Tutors(tutor_id)         ON UPDATE CASCADE ON DELETE RESTRICT,     INDEX idx_reviews_student (student_id),     INDEX idx_reviews_tutor   (tutor_id) );
--  1. Categories (6 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/categories.csv'
INTO TABLE Categories
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(category_name, description);

--  2. Students (100 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/students.csv'
INTO TABLE Students
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(full_name, grade_level, area, phone, email, created_at);

--  3. Tutors (80 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/tutors.csv'
INTO TABLE Tutors
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(full_name, qualification, area, phone, email,
 hourly_rate, is_available, created_at);

--  4. Subjects (30 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/subjects.csv'
INTO TABLE Subjects
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(subject_name, category_id);

--  5. Tutor_Subjects (150 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/tutor_subjects.csv'
INTO TABLE Tutor_Subjects
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(tutor_id, subject_id);

--  6. Matches (120 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/matches.csv'
INTO TABLE Matches
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(student_id, tutor_id, match_date, status);

--  7. Bookings (100 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/bookings.csv'
INTO TABLE Bookings
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(student_id, tutor_id, subject_id, booking_date,
 preferred_time, message, status, created_at);

--  8. Sessions (200 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/sessions.csv'
INTO TABLE Sessions
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(match_id, session_date, start_time, duration_mins, attendance);

--  9. Payments (200 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/payments.csv'
INTO TABLE Payments
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(session_id, amount, payment_date, status);

--  10. Reviews (90 rows) 
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/reviews.csv'
INTO TABLE Reviews
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES  TERMINATED BY '\r\n'
IGNORE 1 ROWS
(student_id, tutor_id, rating, review_text, review_date);

-- SECTION 2 — UPDATE DEMONSTRATIONS

-- UPDATE 1: Mark tutor_id = 5 as unavailable
UPDATE Tutors
SET    is_available = 0
WHERE  tutor_id = 5;

-- UPDATE 2: Mark a specific payment as Paid with today's date
UPDATE Payments
SET    status       = 'Paid',
       payment_date = CURDATE()
WHERE  payment_id = 11;

-- UPDATE 3: Bulk-mark all Due payments older than 60 days
--           so the finance team can follow up
UPDATE Payments
SET    status = 'Due'
WHERE  status       = 'Pending'
  AND  payment_date < DATE_SUB(CURDATE(), INTERVAL 60 DAY);

-- UPDATE 4: Confirm a booking after the tutor accepts it
UPDATE Bookings
SET    status = 'Confirmed'
WHERE  booking_id = 1;

-- UPDATE 5: Close all matches where the last session was
--           more than 90 days ago
UPDATE Matches
SET    status = 'Closed'
WHERE  status  = 'Active'
  AND  match_id NOT IN (
           SELECT DISTINCT match_id
           FROM   Sessions
           WHERE  session_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
       );


-- SECTION 3 — DELETE DEMONSTRATIONS

-- DELETE 1: Remove a specific cancelled booking
DELETE FROM Bookings
WHERE  status     = 'Cancelled'
  AND  booking_id = 3;

-- DELETE 2: Remove all cancelled bookings older than 6 months        
DELETE FROM Bookings
WHERE  status       = 'Cancelled'
  AND  booking_date < DATE_SUB(CURDATE(), INTERVAL 6 MONTH);

-- DELETE 3: Remove reviews that have no text and were entered before 2025 

DELETE FROM Reviews
WHERE  (review_text IS NULL OR TRIM(review_text) = '')
  AND  review_date < '2025-01-01';

-- DELETE 4: Remove a specific orphaned tutor_subject assignment

DELETE FROM Tutor_Subjects
WHERE  tutor_id   = 10
  AND  subject_id = 5;