from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, uuid, sqlite3, json
from datetime import datetime
from utils.db import init_db, get_db
from utils.predict import predict_image, generate_gradcam
from utils.email_service import send_report_email
from utils.report_generator import generate_pdf_report

from utils.report_generator import generate_pdf_report
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dr-detection-secret-2024')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def setup():
    init_db()

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        return jsonify({'success': False, 'message': 'Invalid email or password'})
    return render_template('auth.html', mode='login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'doctor')
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Email already registered'})
        pw_hash = generate_password_hash(password)
        db.execute(
            'INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)',
            (full_name, email, pw_hash, role)
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    return render_template('auth.html', mode='signup')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── APP ROUTES ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    scans = db.execute(
        'SELECT * FROM scans WHERE doctor_id = ? ORDER BY created_at DESC LIMIT 10',
        (session['user_id'],)
    ).fetchall()
    stats = db.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN severity_level = 0 THEN 1 ELSE 0 END) as no_dr,
            SUM(CASE WHEN severity_level IN (1,2) THEN 1 ELSE 0 END) as mild_moderate,
            SUM(CASE WHEN severity_level IN (3,4) THEN 1 ELSE 0 END) as severe
        FROM scans WHERE doctor_id = ?
    ''', (session['user_id'],)).fetchone()
    return render_template('dashboard.html', scans=scans, stats=stats)

@app.route('/scan', methods=['GET'])
def scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('scan.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    patient_name = request.form.get('patient_name', 'Unknown')
    patient_email = request.form.get('patient_email', '')
    patient_age = request.form.get('patient_age', '')
    patient_gender = request.form.get('patient_gender', '')
    patient_phone = request.form.get('patient_phone', '')
    diabetes_duration = request.form.get('diabetes_duration', '')
    medical_history = request.form.get('medical_history', '')
    eye_side = request.form.get('eye_side', 'Right')
    patient_id = request.form.get('patient_id', str(uuid.uuid4())[:8].upper())

    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)

    try:
        result = predict_image(filepath)
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

    db = get_db()
    db.execute('''
        INSERT INTO scans (
            doctor_id, patient_name, patient_email, patient_age, patient_id,
            patient_gender, patient_phone, diabetes_duration, medical_history, eye_side,
            image_path, severity_level, severity_label, confidence,
            model_predictions, recommendations, gradcam_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session['user_id'], patient_name, patient_email, patient_age, patient_id,
        patient_gender, patient_phone, diabetes_duration, medical_history, eye_side,
        filename, result['severity_level'], result['severity_label'],
        result['confidence'], json.dumps(result['model_predictions']),
        result['recommendations'], None
    ))
    db.commit()
    scan_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    gradcam_rel_path = None
    try:
        if not result.get('demo_mode'):
            gradcam_dir = os.path.join(os.path.dirname(__file__), 'static', 'generated', 'gradcam')
            gradcam_result = generate_gradcam(filepath, target_class=result['severity_level'], output_dir=gradcam_dir, output_name=f'scan_{scan_id}')
            gradcam_rel_path = gradcam_result.get('gradcam_path')
            if gradcam_rel_path:
                db.execute('UPDATE scans SET gradcam_path = ? WHERE id = ?', (gradcam_rel_path, scan_id))
                db.commit()
                result['gradcam_path'] = gradcam_rel_path
    except Exception as e:
        result['gradcam_error'] = str(e)

    if patient_email:
        try:
            send_report_email(patient_email, patient_name, result, scan_id)
            result['email_sent'] = True
        except Exception as e:
            result['email_sent'] = False
            result['email_error'] = str(e)

    result['scan_id'] = scan_id
    result['gradcam_path'] = gradcam_rel_path
    if gradcam_rel_path:
        result['gradcam_url'] = url_for('static', filename=gradcam_rel_path)
    return jsonify(result)

@app.route('/report/<int:scan_id>')
def report(scan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    scan = db.execute('SELECT * FROM scans WHERE id = ? AND doctor_id = ?',
                      (scan_id, session['user_id'])).fetchone()
    if not scan:
        return redirect(url_for('dashboard'))
    scan = dict(scan)
    scan['model_predictions'] = json.loads(scan['model_predictions'] or '{}')
    return render_template('report.html', scan=scan)


@app.route('/report/download/<int:scan_id>')
def download_report(scan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    scan = db.execute('SELECT * FROM scans WHERE id = ? AND doctor_id = ?', (scan_id, session['user_id'])).fetchone()
    if not scan:
        return redirect(url_for('dashboard'))
    scan = dict(scan)
    # Build minimal patient and analysis dicts expected by report_generator
    patient = {
        'patient_name': scan.get('patient_name') or 'Unknown',
        'age': scan.get('patient_age') or '—',
        'patient_id': scan.get('patient_id') or '—',
        'gender': scan.get('patient_gender') if 'patient_gender' in scan else None,
        'phone': scan.get('patient_phone'),
        'email': scan.get('patient_email'),
        'diabetes_duration': scan.get('diabetes_duration'),
        'medical_history': scan.get('medical_history'),
    }
    analysis = {
        'id': scan['id'],
        'analyzed_at': scan.get('created_at'),
        'eye_side': scan.get('eye_side', 'Right'),
        'severity_level': scan.get('severity_level', 0),
        'severity_label': scan.get('severity_label', ''),
        'confidence': float(scan.get('confidence', 0.0)),
        'gradcam_filename': os.path.basename(scan.get('gradcam_path')) if scan.get('gradcam_path') else None,
        'image_filename': scan.get('image_path'),
        'recommendation': scan.get('recommendations') or '',
        'notes': '',
    }
    # doctor info
    doctor = db.execute('SELECT * FROM users WHERE id = ?', (scan['doctor_id'],)).fetchone()
    doctor = dict(doctor) if doctor else {'full_name': session.get('user_name'), 'hospital': '', 'specialization': ''}
    # probabilities: try to build from model_predictions if present
    model_preds = json.loads(scan.get('model_predictions') or '{}')
    probabilities = {}
    if isinstance(model_preds, dict) and model_preds:
        # If model_preds maps class->prob use it, otherwise map predicted label
        # Try to extract class probabilities if available
        for k, v in model_preds.items():
            if isinstance(v, dict) and 'label' in v and 'confidence' in v:
                probabilities[v['label']] = float(v.get('confidence', 0.0))
    if not probabilities:
        probabilities = {analysis['severity_label']: analysis['confidence']}

    out_dir = os.path.join(os.path.dirname(__file__), 'static', 'generated', 'reports')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"report_{scan_id}.pdf")
    generate_pdf_report(out_path, patient, analysis, doctor, probabilities)
    return send_file(out_path, as_attachment=True, download_name=f"report_{scan_id}.pdf")

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    scans = db.execute(
        'SELECT * FROM scans WHERE doctor_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    return render_template('history.html', scans=scans)

@app.route('/api/send-report/<int:scan_id>', methods=['POST'])
def resend_report(scan_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    scan = db.execute('SELECT * FROM scans WHERE id = ? AND doctor_id = ?',
                      (scan_id, session['user_id'])).fetchone()
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404
    scan = dict(scan)
    if not scan['patient_email']:
        return jsonify({'error': 'No patient email on record'}), 400
    result = {
        'severity_label': scan['severity_label'],
        'severity_level': scan['severity_level'],
        'confidence': scan['confidence'],
        'recommendations': scan['recommendations'],
        'model_predictions': json.loads(scan['model_predictions'] or '{}')
    }
    try:
        send_report_email(scan['patient_email'], scan['patient_name'], result, scan_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-scan/<int:scan_id>', methods=['POST'])
def delete_scan(scan_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    db = get_db()
    scan = db.execute('SELECT * FROM scans WHERE id = ? AND doctor_id = ?',
                      (scan_id, session['user_id'])).fetchone()
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404
    
    # Delete the scan record
    db.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Scan deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
