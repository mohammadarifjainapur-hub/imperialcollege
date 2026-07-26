from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
CORS(app) 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college_final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    register_no = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default='student') 
    total_fees = db.Column(db.Float, default=50000.0)
    paid_fees = db.Column(db.Float, default=0.0)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100))
    file_link = db.Column(db.String(500))
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    date = db.Column(db.String(20)) 
    status = db.Column(db.String(10)) 

class Achiever(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    score_details = db.Column(db.String(200))
    photo_link = db.Column(db.String(500))

class Poster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    image_link = db.Column(db.String(500))

@app.route('/student/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(register_no=data['register_no'], password=data['password']).first()
    if not user:
        return jsonify({"status": "error", "message": "Invalid ID or Password!"}), 401
    return jsonify({"status": "success", "user_id": user.id, "name": user.name, "role": user.role})

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    data = request.json
    existing = User.query.filter_by(register_no=data['register_no']).first()
    if existing:
        return jsonify({"error": "ID already exists!"}), 400
    
    role = data.get('role', 'student')
    fees = 0 if role == 'teacher' else float(data.get('total_fees', 50000.0))
    
    new_user = User(name=data['name'], register_no=data['register_no'], password=data['password'], role=role, total_fees=fees)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "message": f"{role.capitalize()} {new_user.name} added successfully!",
        "register_no": new_user.register_no,
        "password": new_user.password
    })

@app.route('/admin/delete_user/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({"error": "User not found!"}), 404
    
    if user.role == 'student':
        Attendance.query.filter_by(student_id=id).delete()
        Message.query.filter_by(student_id=id).delete()
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"{user.role.capitalize()} deleted permanently!"})

@app.route('/admin/dashboard_stats', methods=['GET'])
def get_dashboard_stats():
    students = User.query.filter_by(role='student').all()
    total_expected = sum(s.total_fees for s in students)
    total_collected = sum(s.paid_fees for s in students)
    return jsonify({"total_expected": total_expected, "total_collected": total_collected, "total_pending": total_expected - total_collected})

@app.route('/admin/students', methods=['GET'])
def get_all_students():
    students = User.query.filter_by(role='student').all()
    return jsonify([{
        "id": s.id, "name": s.name, "register_no": s.register_no, 
        "password": s.password, "total_fees": s.total_fees, 
        "paid_fees": s.paid_fees, "remaining_fees": s.total_fees - s.paid_fees
    } for s in students])

@app.route('/admin/teachers', methods=['GET'])
def get_all_teachers():
    teachers = User.query.filter_by(role='teacher').all()
    return jsonify([{
        "id": t.id, "name": t.name, "register_no": t.register_no, "password": t.password
    } for t in teachers])

@app.route('/admin/update_fees/<int:id>', methods=['PUT'])
def update_fees(id):
    data = request.json
    student = User.query.get(id)
    student.paid_fees += data.get('amount_paid', 0)
    db.session.commit()
    return jsonify({"message": f"Fees updated for {student.name}"})

@app.route('/admin/send_reminders', methods=['POST'])
def send_reminders():
    students = User.query.filter_by(role='student').all()
    for student in students:
        remaining = student.total_fees - student.paid_fees
        if remaining > 0:
            db.session.add(Message(student_id=student.id, text=f"Hello {student.name}, reminder: pending fee ₹{remaining}."))
    db.session.commit()
    return jsonify({"message": "Reminders sent!"})

@app.route('/admin/export_excel', methods=['GET'])
def export_excel():
    students = User.query.filter_by(role='student').all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Student ID (Reg No)', 'Full Name', 'Password', 'Total Fees', 'Paid Fees', 'Remaining Fees'])
    for s in students:
        cw.writerow([s.register_no, s.name, s.password, s.total_fees, s.paid_fees, s.total_fees - s.paid_fees])
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=Imperial_College_Students.csv"})

@app.route('/admin/add_achiever', methods=['POST'])
def add_achiever():
    data = request.json
    db.session.add(Achiever(name=data['name'], score_details=data['score_details'], photo_link=data['photo_link']))
    db.session.commit()
    return jsonify({"message": "Individual Achiever added!"})

@app.route('/achievers', methods=['GET'])
def get_achievers():
    achievers = Achiever.query.order_by(Achiever.id.desc()).all()
    return jsonify([{"name": a.name, "score_details": a.score_details, "photo_link": a.photo_link} for a in achievers])

@app.route('/admin/add_poster', methods=['POST'])
def add_poster():
    data = request.json
    db.session.add(Poster(title=data['title'], image_link=data['image_link']))
    db.session.commit()
    return jsonify({"message": "Poster added successfully!"})

@app.route('/posters', methods=['GET'])
def get_posters():
    posters = Poster.query.order_by(Poster.id.desc()).all()
    return jsonify([{"title": p.title, "image_link": p.image_link} for p in posters])

@app.route('/teacher/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    date = data.get('date')
    for rec in data.get('records'):
        existing = Attendance.query.filter_by(student_id=rec['student_id'], date=date).first()
        if existing:
            existing.status = rec['status']
        else:
            db.session.add(Attendance(student_id=rec['student_id'], date=date, status=rec['status']))
    db.session.commit()
    return jsonify({"message": f"Attendance marked for {date}!"})

@app.route('/admin/upload_note', methods=['POST'])
def upload_note():
    data = request.json
    db.session.add(Note(subject=data['subject'], file_link=data['file_link']))
    db.session.commit()
    return jsonify({"message": "Notes uploaded!"})

@app.route('/student/<int:id>/attendance', methods=['GET'])
def get_attendance(id):
    records = Attendance.query.filter_by(student_id=id).order_by(Attendance.date.desc()).all()
    now = datetime.now()
    current_month_str = now.strftime("%Y-%m") 
    
    yearly_total = len(records)
    yearly_present = len([r for r in records if r.status == 'Present'])
    monthly_records = [r for r in records if r.date.startswith(current_month_str)]
    monthly_present = len([r for r in monthly_records if r.status == 'Present'])
    
    return jsonify({
        "yearly_pct": round((yearly_present / yearly_total * 100) if yearly_total > 0 else 0, 1),
        "monthly_pct": round((monthly_present / len(monthly_records) * 100) if len(monthly_records) > 0 else 0, 1),
        "details": [{"date": r.date, "status": r.status} for r in records] 
    })

@app.route('/student/<int:id>/data', methods=['GET'])
def get_student_data(id):
    student = User.query.get(id)
    if not student:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"name": student.name, "register_no": student.register_no})

@app.route('/student/notes', methods=['GET'])
def get_notes():
    notes = Note.query.order_by(Note.date_uploaded.desc()).all()
    return jsonify([{"id": n.id, "subject": n.subject, "file_link": n.file_link} for n in notes])

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            db.session.add(User(name="Main Admin", register_no="ADMIN123", password="adminpass", role="admin"))
            db.session.add(User(name="Amit Sir", register_no="TEACHER01", password="pass", role="teacher"))
            db.session.add(User(name="Rahul Kumar", register_no="IMPERIAL01", password="pass", role="student", total_fees=50000, paid_fees=20000))
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)