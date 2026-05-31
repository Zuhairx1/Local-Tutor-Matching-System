from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import datetime
import decimal

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456789',
    'database': 'tutor_matching_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def serialize(obj):
    if isinstance(obj, list):
        return [serialize(row) for row in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, datetime.timedelta):
        total = int(obj.total_seconds())
        h, rem = divmod(abs(total), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if obj is None:
        return ""
    return obj

def query(sql, params=None, fetch=True):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    if fetch:
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return serialize(result)
    else:
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return last_id

@app.route('/api/stats')
def stats():
    students = query("SELECT COUNT(*) AS n FROM Students")[0]['n']
    tutors = query("SELECT COUNT(*) AS n FROM Tutors")[0]['n']
    available = query("SELECT COUNT(*) AS n FROM Tutors WHERE is_available=1")[0]['n']
    sessions = query("SELECT COUNT(*) AS n FROM Sessions")[0]['n']
    matches = query("SELECT COUNT(*) AS n FROM Matches")[0]['n']
    revenue = query("SELECT COALESCE(SUM(amount),0) AS n FROM Payments WHERE status='Paid'")[0]['n']
    return jsonify({'students': students, 'tutors': tutors, 'available_tutors': available, 'sessions': sessions, 'matches': matches, 'revenue': float(revenue)})

@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'students': [], 'tutors': [], 'bookings': [], 'payments': []})
    students = query("SELECT * FROM Students WHERE full_name LIKE %s OR area LIKE %s OR grade_level LIKE %s OR phone LIKE %s OR email LIKE %s LIMIT 20", (f'%{q}%',)*5)
    tutors = query("SELECT t.*, COALESCE(GROUP_CONCAT(s.subject_name SEPARATOR ', '), '') AS subjects, COALESCE(GROUP_CONCAT(s.subject_id SEPARATOR ','), '') AS subject_ids FROM Tutors t LEFT JOIN Tutor_Subjects ts ON t.tutor_id=ts.tutor_id LEFT JOIN Subjects s ON ts.subject_id=s.subject_id WHERE t.full_name LIKE %s OR t.qualification LIKE %s OR t.area LIKE %s OR t.phone LIKE %s OR t.email LIKE %s GROUP BY t.tutor_id LIMIT 20", (f'%{q}%',)*5)
    bookings = query("SELECT b.*, st.full_name AS student_name, t.full_name AS tutor_name, s.subject_name FROM Bookings b JOIN Students st ON b.student_id=st.student_id JOIN Tutors t ON b.tutor_id=t.tutor_id JOIN Subjects s ON b.subject_id=s.subject_id WHERE st.full_name LIKE %s OR t.full_name LIKE %s OR s.subject_name LIKE %s LIMIT 20", (f'%{q}%',)*3)
    payments = query("SELECT p.*, t.full_name AS tutor_name, st.full_name AS student_name FROM Payments p JOIN Sessions sess ON p.session_id=sess.session_id JOIN Matches m ON sess.match_id=m.match_id JOIN Tutors t ON m.tutor_id=t.tutor_id JOIN Students st ON m.student_id=st.student_id WHERE t.full_name LIKE %s OR st.full_name LIKE %s OR p.status LIKE %s LIMIT 20", (f'%{q}%',)*3)
    return jsonify({'students': students, 'tutors': tutors, 'bookings': bookings, 'payments': payments})

@app.route('/api/students', methods=['GET', 'POST'])
def students():
    if request.method == 'GET':
        search_term = request.args.get('search', '')
        area_filter = request.args.get('area', '')
        sql = "SELECT * FROM Students WHERE 1=1"
        params = []
        if area_filter:
            sql += " AND area = %s"
            params.append(area_filter)
        if search_term:
            sql += " AND (full_name LIKE %s OR area LIKE %s OR grade_level LIKE %s OR phone LIKE %s OR email LIKE %s)"
            params.extend([f'%{search_term}%']*5)
        sql += " ORDER BY created_at DESC"
        return jsonify(query(sql, params))
    d = request.json
    new_id = query("INSERT INTO Students (full_name, grade_level, area, phone, email) VALUES (%s,%s,%s,%s,%s)", (d['full_name'], d['grade_level'], d['area'], d['phone'], d['email']), fetch=False)
    return jsonify({'student_id': new_id, 'message': 'Student registered'}), 201

@app.route('/api/students/<int:sid>', methods=['GET', 'PUT', 'DELETE'])
def student_crud(sid):
    if request.method == 'GET':
        rows = query("SELECT * FROM Students WHERE student_id=%s", (sid,))
        return jsonify(rows[0]) if rows else ('Not found', 404)
    elif request.method == 'PUT':
        d = request.json
        query("UPDATE Students SET full_name=%s, grade_level=%s, area=%s, phone=%s, email=%s WHERE student_id=%s", (d['full_name'], d['grade_level'], d['area'], d['phone'], d['email'], sid), fetch=False)
        return jsonify({'message': 'Student updated'})
    elif request.method == 'DELETE':
        query("DELETE FROM Students WHERE student_id=%s", (sid,), fetch=False)
        return jsonify({'message': 'Student deleted'})

@app.route('/api/students/<int:sid>/dashboard')
def student_dashboard(sid):
    session_count = query("SELECT COUNT(*) AS count FROM Sessions s JOIN Matches m ON s.match_id=m.match_id WHERE m.student_id=%s", (sid,))[0]['count']
    total_spent = query("SELECT COALESCE(SUM(p.amount),0) AS total FROM Payments p JOIN Sessions s ON p.session_id=s.session_id JOIN Matches m ON s.match_id=m.match_id WHERE m.student_id=%s AND p.status='Paid'", (sid,))[0]['total']
    upcoming = query("SELECT COUNT(*) AS count FROM Sessions s JOIN Matches m ON s.match_id=m.match_id WHERE m.student_id=%s AND s.session_date >= CURDATE()", (sid,))[0]['count']
    my_tutor = query("SELECT t.tutor_id, t.full_name, t.qualification, t.hourly_rate, t.area, t.is_available FROM Tutors t JOIN Matches m ON t.tutor_id=m.tutor_id WHERE m.student_id=%s AND m.status='Active' ORDER BY m.match_date DESC LIMIT 1", (sid,))
    upcoming_sessions = query("SELECT s.session_id, s.session_date, s.start_time, t.full_name AS tutor_name, sub.subject_name, COALESCE(b.status,'Confirmed') AS status FROM Sessions s JOIN Matches m ON s.match_id=m.match_id JOIN Tutors t ON m.tutor_id=t.tutor_id LEFT JOIN Bookings b ON b.student_id=m.student_id AND b.tutor_id=m.tutor_id LEFT JOIN Subjects sub ON b.subject_id=sub.subject_id WHERE m.student_id=%s AND s.session_date>=CURDATE() ORDER BY s.session_date LIMIT 5", (sid,))
    return jsonify({'session_count': session_count, 'total_spent': float(total_spent), 'upcoming': upcoming, 'my_tutor': my_tutor[0] if my_tutor else None, 'upcoming_sessions': upcoming_sessions})

@app.route('/api/tutors', methods=['GET', 'POST'])
def tutors():
    if request.method == 'GET':
        avail = request.args.get('available')
        search = request.args.get('search', '')
        sql = "SELECT t.*, COALESCE(GROUP_CONCAT(s.subject_name SEPARATOR ', '), '') AS subjects, COALESCE(GROUP_CONCAT(s.subject_id SEPARATOR ','), '') AS subject_ids FROM Tutors t LEFT JOIN Tutor_Subjects ts ON t.tutor_id=ts.tutor_id LEFT JOIN Subjects s ON ts.subject_id=s.subject_id WHERE 1=1"
        params = []
        if avail == '1':
            sql += " AND t.is_available = 1"
        if search:
            sql += " AND (t.full_name LIKE %s OR t.qualification LIKE %s)"
            params.extend([f'%{search}%']*2)
        sql += " GROUP BY t.tutor_id ORDER BY t.tutor_id"
        return jsonify(query(sql, params))
    d = request.json
    new_id = query("INSERT INTO Tutors (full_name, qualification, area, phone, email, hourly_rate, is_available) VALUES (%s,%s,%s,%s,%s,%s,%s)", (d['full_name'], d['qualification'], d['area'], d['phone'], d['email'], d['hourly_rate'], d.get('is_available', 1)), fetch=False)
    return jsonify({'tutor_id': new_id, 'message': 'Tutor registered'}), 201

@app.route('/api/tutors/<int:tid>', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def tutor_crud(tid):
    if request.method == 'GET':
        rows = query("SELECT t.*, COALESCE(GROUP_CONCAT(s.subject_name SEPARATOR ', '),'') AS subjects, COALESCE(GROUP_CONCAT(s.subject_id SEPARATOR ','),'') AS subject_ids FROM Tutors t LEFT JOIN Tutor_Subjects ts ON t.tutor_id=ts.tutor_id LEFT JOIN Subjects s ON ts.subject_id=s.subject_id WHERE t.tutor_id=%s GROUP BY t.tutor_id", (tid,))
        return jsonify(rows[0]) if rows else ('Not found', 404)
    elif request.method == 'PUT':
        d = request.json
        query("UPDATE Tutors SET full_name=%s, qualification=%s, area=%s, phone=%s, email=%s, hourly_rate=%s, is_available=%s WHERE tutor_id=%s", (d['full_name'], d['qualification'], d['area'], d['phone'], d['email'], d['hourly_rate'], d.get('is_available',1), tid), fetch=False)
        return jsonify({'message': 'Tutor updated'})
    elif request.method == 'DELETE':
        query("DELETE FROM Tutors WHERE tutor_id=%s", (tid,), fetch=False)
        return jsonify({'message': 'Tutor deleted'})
    elif request.method == 'PATCH':
        d = request.json
        if 'is_available' in d:
            query("UPDATE Tutors SET is_available=%s WHERE tutor_id=%s", (d['is_available'], tid), fetch=False)
        return jsonify({'message': 'Tutor updated'})

@app.route('/api/tutors/ratings')
def tutor_ratings():
    return jsonify(query("SELECT tutor_id, ROUND(AVG(rating),1) AS avg_rating, COUNT(*) AS review_count FROM Reviews GROUP BY tutor_id"))

@app.route('/api/tutors/available-for-booking')
def tutors_available_for_booking():
    return jsonify(query("SELECT t.tutor_id, t.full_name, t.hourly_rate, t.qualification, t.area, COALESCE(GROUP_CONCAT(DISTINCT s.subject_name SEPARATOR ', '),'') AS subjects, COALESCE(GROUP_CONCAT(DISTINCT s.subject_id SEPARATOR ','),'') AS subject_ids FROM Tutors t LEFT JOIN Tutor_Subjects ts ON t.tutor_id=ts.tutor_id LEFT JOIN Subjects s ON ts.subject_id=s.subject_id WHERE t.is_available=1 GROUP BY t.tutor_id, t.full_name, t.hourly_rate, t.qualification, t.area ORDER BY t.full_name"))

@app.route('/api/tutors/<int:tid>/dashboard')
def tutor_dashboard(tid):
    student_count = query("SELECT COUNT(DISTINCT m.student_id) AS count FROM Matches m WHERE m.tutor_id=%s", (tid,))[0]['count']
    first_of_month = datetime.date.today().replace(day=1).isoformat()
    session_count = query("SELECT COUNT(*) AS count FROM Sessions s JOIN Matches m ON s.match_id=m.match_id WHERE m.tutor_id=%s AND s.session_date>=%s", (tid, first_of_month))[0]['count']
    earnings = query("SELECT COALESCE(SUM(p.amount),0) AS total FROM Payments p JOIN Sessions s ON p.session_id=s.session_id JOIN Matches m ON s.match_id=m.match_id WHERE m.tutor_id=%s AND p.status='Paid' AND p.payment_date>=%s", (tid, first_of_month))[0]['total']
    today = datetime.date.today().isoformat()
    today_schedule = query("SELECT s.session_id, s.session_date, s.start_time, st.full_name AS student_name, sub.subject_name, COALESCE(b.status,'Confirmed') AS booking_status FROM Sessions s JOIN Matches m ON s.match_id=m.match_id JOIN Students st ON m.student_id=st.student_id LEFT JOIN Bookings b ON b.student_id=m.student_id AND b.tutor_id=m.tutor_id LEFT JOIN Subjects sub ON b.subject_id=sub.subject_id WHERE m.tutor_id=%s AND s.session_date=%s ORDER BY s.start_time", (tid, today))
    pending_requests = query("SELECT b.booking_id, b.booking_date, b.preferred_time, st.full_name AS student_name, sub.subject_name FROM Bookings b JOIN Students st ON b.student_id=st.student_id JOIN Subjects sub ON b.subject_id=sub.subject_id WHERE b.tutor_id=%s AND b.status='Pending' ORDER BY b.booking_date", (tid,))
    return jsonify({'student_count': student_count, 'session_count': session_count, 'earnings': float(earnings), 'today_schedule': today_schedule, 'pending_requests': pending_requests})

@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        return jsonify(query("SELECT c.*, COUNT(s.subject_id) AS subject_count FROM Categories c LEFT JOIN Subjects s ON c.category_id=s.category_id GROUP BY c.category_id"))
    d = request.json
    new_id = query("INSERT INTO Categories (category_name) VALUES (%s)", (d['category_name'],), fetch=False)
    return jsonify({'category_id': new_id, 'message': 'Category added'}), 201

@app.route('/api/categories/<int:cid>', methods=['PUT', 'DELETE'])
def category_crud(cid):
    if request.method == 'PUT':
        d = request.json
        query("UPDATE Categories SET category_name=%s WHERE category_id=%s", (d['category_name'], cid), fetch=False)
        return jsonify({'message': 'Category updated'})
    elif request.method == 'DELETE':
        query("DELETE FROM Categories WHERE category_id=%s", (cid,), fetch=False)
        return jsonify({'message': 'Category deleted'})

@app.route('/api/subjects', methods=['GET', 'POST'])
def subjects():
    if request.method == 'GET':
        return jsonify(query("SELECT s.*, c.category_name, COUNT(ts.tutor_id) AS tutor_count FROM Subjects s JOIN Categories c ON s.category_id=c.category_id LEFT JOIN Tutor_Subjects ts ON s.subject_id=ts.subject_id GROUP BY s.subject_id"))
    d = request.json
    new_id = query("INSERT INTO Subjects (subject_name, category_id) VALUES (%s,%s)", (d['subject_name'], d['category_id']), fetch=False)
    return jsonify({'subject_id': new_id, 'message': 'Subject added'}), 201

@app.route('/api/subjects/<int:sid>', methods=['PUT', 'DELETE'])
def subject_crud(sid):
    if request.method == 'PUT':
        d = request.json
        query("UPDATE Subjects SET subject_name=%s, category_id=%s WHERE subject_id=%s", (d['subject_name'], d['category_id'], sid), fetch=False)
        return jsonify({'message': 'Subject updated'})
    elif request.method == 'DELETE':
        query("DELETE FROM Subjects WHERE subject_id=%s", (sid,), fetch=False)
        return jsonify({'message': 'Subject deleted'})

@app.route('/api/bookings', methods=['GET', 'POST'])
def bookings():
    if request.method == 'GET':
        status = request.args.get('status')
        student_id = request.args.get('student_id')
        tutor_id = request.args.get('tutor_id')
        sql = "SELECT b.*, st.full_name AS student_name, t.full_name AS tutor_name, s.subject_name FROM Bookings b JOIN Students st ON b.student_id=st.student_id JOIN Tutors t ON b.tutor_id=t.tutor_id JOIN Subjects s ON b.subject_id=s.subject_id WHERE 1=1"
        params = []
        if status: sql += " AND b.status=%s"; params.append(status)
        if student_id: sql += " AND b.student_id=%s"; params.append(student_id)
        if tutor_id: sql += " AND b.tutor_id=%s"; params.append(tutor_id)
        sql += " ORDER BY b.created_at DESC"
        return jsonify(query(sql, params))
    d = request.json
    new_id = query("INSERT INTO Bookings (student_id, tutor_id, subject_id, booking_date, preferred_time, message, status) VALUES (%s,%s,%s,%s,%s,%s,'Pending')", (d['student_id'], d['tutor_id'], d['subject_id'], d['booking_date'], d['preferred_time'], d.get('message','')), fetch=False)
    return jsonify({'booking_id': new_id, 'message': 'Booking created', 'status': 'Pending'}), 201

@app.route('/api/bookings/<int:bid>', methods=['PUT', 'DELETE', 'PATCH'])
def booking_crud(bid):
    if request.method == 'PUT':
        d = request.json
        query("UPDATE Bookings SET student_id=%s, tutor_id=%s, subject_id=%s, booking_date=%s, preferred_time=%s, message=%s, status=%s WHERE booking_id=%s", (d['student_id'], d['tutor_id'], d['subject_id'], d['booking_date'], d['preferred_time'], d.get('message',''), d.get('status','Pending'), bid), fetch=False)
        return jsonify({'message': f"Booking {bid} updated"})
    elif request.method == 'DELETE':
        query("DELETE FROM Bookings WHERE booking_id=%s", (bid,), fetch=False)
        return jsonify({'message': f"Booking {bid} deleted"})
    elif request.method == 'PATCH':
        d = request.json
        if 'status' in d:
            query("UPDATE Bookings SET status=%s WHERE booking_id=%s", (d['status'], bid), fetch=False)
        return jsonify({'message': f"Booking {bid} set to {d['status']}"})

@app.route('/api/bookings/<int:bid>/respond', methods=['POST'])
def respond_to_booking(bid):
    d = request.json
    action = d.get('action')
    if action == 'accept':
        query("UPDATE Bookings SET status='Confirmed' WHERE booking_id=%s", (bid,), fetch=False)
        booking = query("SELECT * FROM Bookings WHERE booking_id=%s", (bid,))
        if booking:
            b = booking[0]
            existing = query("SELECT match_id FROM Matches WHERE student_id=%s AND tutor_id=%s", (b['student_id'], b['tutor_id']))
            if not existing:
                query("INSERT INTO Matches (student_id, tutor_id, match_date, status) VALUES (%s,%s,CURDATE(),'Active')", (b['student_id'], b['tutor_id']), fetch=False)
        return jsonify({'message': 'Booking accepted'})
    elif action == 'decline':
        query("UPDATE Bookings SET status='Cancelled' WHERE booking_id=%s", (bid,), fetch=False)
        return jsonify({'message': 'Booking declined'})
    return jsonify({'error': 'Invalid action'}), 400

@app.route('/api/matches', methods=['GET'])
def matches():
    tutor_id = request.args.get('tutor_id')
    student_id = request.args.get('student_id')
    sql = "SELECT m.*, st.full_name AS student_name, t.full_name AS tutor_name, COUNT(sess.session_id) AS session_count FROM Matches m JOIN Students st ON m.student_id=st.student_id JOIN Tutors t ON m.tutor_id=t.tutor_id LEFT JOIN Sessions sess ON m.match_id=sess.match_id WHERE 1=1"
    params = []
    if tutor_id: sql += " AND m.tutor_id=%s"; params.append(tutor_id)
    if student_id: sql += " AND m.student_id=%s"; params.append(student_id)
    sql += " GROUP BY m.match_id ORDER BY m.match_date DESC"
    return jsonify(query(sql, params))

@app.route('/api/matches/<int:mid>', methods=['DELETE'])
def delete_match(mid):
    query("DELETE FROM Matches WHERE match_id=%s", (mid,), fetch=False)
    return jsonify({'message': f"Match {mid} deleted"})

@app.route('/api/sessions', methods=['GET'])
def sessions():
    student_id = request.args.get('student_id')
    tutor_id = request.args.get('tutor_id')
    sql = "SELECT sess.*, st.full_name AS student_name, t.full_name AS tutor_name, p.status AS payment_status, p.amount FROM Sessions sess JOIN Matches m ON sess.match_id=m.match_id JOIN Students st ON m.student_id=st.student_id JOIN Tutors t ON m.tutor_id=t.tutor_id LEFT JOIN Payments p ON sess.session_id=p.session_id WHERE 1=1"
    params = []
    if student_id: sql += " AND m.student_id=%s"; params.append(student_id)
    if tutor_id: sql += " AND m.tutor_id=%s"; params.append(tutor_id)
    sql += " ORDER BY sess.session_date DESC"
    return jsonify(query(sql, params))

@app.route('/api/sessions/<int:sid>', methods=['DELETE'])
def delete_session(sid):
    query("DELETE FROM Sessions WHERE session_id=%s", (sid,), fetch=False)
    return jsonify({'message': f"Session {sid} deleted"})

@app.route('/api/sessions/unpaid')
def unpaid_sessions():
    return jsonify(query("SELECT sess.*, st.full_name AS student_name, t.full_name AS tutor_name, COALESCE(p.status,'Unpaid') AS payment_status, COALESCE(p.amount, t.hourly_rate) AS amount FROM Sessions sess JOIN Matches m ON sess.match_id=m.match_id JOIN Students st ON m.student_id=st.student_id JOIN Tutors t ON m.tutor_id=t.tutor_id LEFT JOIN Payments p ON sess.session_id=p.session_id WHERE p.payment_id IS NULL OR p.status IN ('Pending','Due') ORDER BY sess.session_date DESC"))

@app.route('/api/payments', methods=['GET', 'POST'])
def payments():
    if request.method == 'GET':
        status = request.args.get('status')
        tutor_id = request.args.get('tutor_id')
        student_id = request.args.get('student_id')
        sql = "SELECT p.*, t.full_name AS tutor_name, st.full_name AS student_name, t.hourly_rate, sess.session_date FROM Payments p JOIN Sessions sess ON p.session_id=sess.session_id JOIN Matches m ON sess.match_id=m.match_id JOIN Tutors t ON m.tutor_id=t.tutor_id JOIN Students st ON m.student_id=st.student_id WHERE 1=1"
        params = []
        if status: sql += " AND p.status=%s"; params.append(status)
        if tutor_id: sql += " AND t.tutor_id=%s"; params.append(tutor_id)
        if student_id: sql += " AND m.student_id=%s"; params.append(student_id)
        sql += " ORDER BY p.payment_date DESC, p.payment_id DESC"
        return jsonify(query(sql, params))
    d = request.json
    new_id = query("INSERT INTO Payments (session_id, amount, status, payment_date, payment_method) VALUES (%s,%s,%s,CURDATE(),%s)", (d['session_id'], d['amount'], d.get('status','Paid'), d.get('payment_method','Cash')), fetch=False)
    return jsonify({'payment_id': new_id, 'message': 'Payment recorded'}), 201

@app.route('/api/payments/<int:pid>', methods=['PUT', 'DELETE', 'PATCH'])
def payment_crud(pid):
    if request.method == 'PUT':
        d = request.json
        query("UPDATE Payments SET session_id=%s, amount=%s, status=%s, payment_method=%s, payment_date=%s WHERE payment_id=%s", (d['session_id'], d['amount'], d['status'], d.get('payment_method','Cash'), d.get('payment_date', datetime.date.today().isoformat()), pid), fetch=False)
        return jsonify({'message': f"Payment {pid} updated"})
    elif request.method == 'DELETE':
        query("DELETE FROM Payments WHERE payment_id=%s", (pid,), fetch=False)
        return jsonify({'message': f"Payment {pid} deleted"})
    elif request.method == 'PATCH':
        d = request.json
        if 'status' in d:
            query("UPDATE Payments SET status=%s, payment_date=CURDATE() WHERE payment_id=%s", (d['status'], pid), fetch=False)
        return jsonify({'message': f"Payment {pid} updated to {d['status']}"})

@app.route('/api/payments/stats')
def payment_stats():
    return jsonify(query("SELECT status, COUNT(*) AS count, COALESCE(SUM(amount),0) AS total FROM Payments GROUP BY status"))

@app.route('/api/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'GET':
        tutor_id = request.args.get('tutor_id')
        student_id = request.args.get('student_id')
        sql = "SELECT r.*, st.full_name AS student_name, t.full_name AS tutor_name FROM Reviews r JOIN Students st ON r.student_id=st.student_id JOIN Tutors t ON r.tutor_id=t.tutor_id WHERE 1=1"
        params = []
        if tutor_id: sql += " AND r.tutor_id=%s"; params.append(tutor_id)
        if student_id: sql += " AND r.student_id=%s"; params.append(student_id)
        sql += " ORDER BY r.review_date DESC"
        return jsonify(query(sql, params))
    d = request.json
    new_id = query("INSERT INTO Reviews (student_id, tutor_id, rating, review_text, review_date) VALUES (%s,%s,%s,%s,CURDATE())", (d['student_id'], d['tutor_id'], d['rating'], d.get('review_text','')), fetch=False)
    return jsonify({'review_id': new_id, 'message': 'Review submitted'}), 201

@app.route('/api/reviews/<int:rid>', methods=['DELETE'])
def delete_review(rid):
    query("DELETE FROM Reviews WHERE review_id=%s", (rid,), fetch=False)
    return jsonify({'message': f"Review {rid} deleted"})

@app.route('/api/reviews/stats')
def review_stats():
    tutor_id = request.args.get('tutor_id')
    if tutor_id:
        rows = query("SELECT rating, COUNT(*) AS count FROM Reviews WHERE tutor_id=%s GROUP BY rating ORDER BY rating DESC", (tutor_id,))
        avg = query("SELECT ROUND(AVG(rating),1) AS avg_rating FROM Reviews WHERE tutor_id=%s", (tutor_id,))[0]['avg_rating']
    else:
        rows = query("SELECT rating, COUNT(*) AS count FROM Reviews GROUP BY rating ORDER BY rating DESC")
        avg = query("SELECT ROUND(AVG(rating),1) AS avg_rating FROM Reviews")[0]['avg_rating']
    return jsonify({'distribution': rows, 'average': float(avg or 0)})

@app.route('/api/activity')
def activity():
    bookings = query("SELECT CONCAT(st.full_name,' booked ',s.subject_name,' with ',t.full_name) AS text, b.created_at AS ts FROM Bookings b JOIN Students st ON b.student_id=st.student_id JOIN Tutors t ON b.tutor_id=t.tutor_id JOIN Subjects s ON b.subject_id=s.subject_id ORDER BY b.created_at DESC LIMIT 20")
    payments = query("SELECT CONCAT('Payment PKR ',p.amount,' marked as ',p.status,' for session #',p.session_id) AS text, p.payment_date AS ts FROM Payments p WHERE p.status='Paid' ORDER BY p.payment_date DESC LIMIT 20")
    reviews = query("SELECT CONCAT(st.full_name,' gave ',r.rating,'star to ',t.full_name) AS text, r.review_date AS ts FROM Reviews r JOIN Students st ON r.student_id=st.student_id JOIN Tutors t ON r.tutor_id=t.tutor_id ORDER BY r.review_date DESC LIMIT 20")
    return jsonify(sorted(bookings + payments + reviews, key=lambda x: str(x['ts']), reverse=True)[:15])

if __name__ == '__main__':
    app.run(debug=True, port=5000)