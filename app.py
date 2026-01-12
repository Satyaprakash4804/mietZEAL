from flask import Flask, render_template, request, send_from_directory, session
import mysql.connector
import qrcode
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "zeal10_secret_key_2025"  # Required for session

# ---------------- CONFIG ----------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Mysql@123"
DB_NAME = "zeal10"

QR_DIR = "static/qr"
UPLOAD_DIR = "uploads/payments"

os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# ---------------- EVENTS & PRICES ----------------
EVENT_PRICES = {
    "Business Idea Pitching Contest (Case Cracker)": 100,
    "Caselet Solving Competition": 100,
    "Paper / Balloon Tower Making (Paper Peaks)": 100,
    "Corporate Collage (Bizmosaic)": 100,
    "Sales Pitching Contest (DealQuest)": 100,
    "Turbo AI Challenge": 100,
    "INNO Quest": 100,
    "Robo Race": 100,
    "CODING": 100,
    "Clip Clash – REEL": 100,
    "Quiz Competition": 100,
    "Poster Making (Tech Theme)": 100,
    "Dance Competition": 100,
    "Rangoli Competition": 100,
    "Cook without Fire": 100,
    "Ad-Mad Show": 100,
    "Eco-Fashion / Recycled Clothing Show": 100,
    "T-Shirt Painting": 100,
    "Eco-Voice Debate / GreenSpeak Debate": 100,
    "Face Painting Competition": 100,
    "Fashion Show (Competition)": 600,
    "Dance Competition (Group / Duet / Solo)": 300
}

# ---------------- INIT DB ----------------
def init_db():
    try:
        # Create DB
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.commit()
        cur.close()
        conn.close()

        # Connect DB
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_name VARCHAR(100),
                roll_no VARCHAR(50),
                course VARCHAR(100),
                college VARCHAR(150),
                college_id VARCHAR(50),
                other_college VARCHAR(150),
                events TEXT,
                group_members TEXT,
                contact_numbers TEXT,
                total_amount INT,
                payment_screenshot VARCHAR(255),
                payment_status VARCHAR(20) DEFAULT 'Submitted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

init_db()

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# ---------------- HELPERS ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_total(selected_events, college):
    total = 0
    for event in selected_events:
        price = EVENT_PRICES.get(event, 0)
        if college == "Mangalmay Group of Institutions":
            price = price // 2
        total += price
    return total

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        step = request.form.get("step")
        
        # Collect form data
        name = request.form.get("student_name")
        roll = request.form.get("roll_no")
        course = request.form.get("course")
        college = request.form.get("college")
        college_id = request.form.get("college_id", "")
        other_college = request.form.get("other_college", "")
        selected_events = request.form.getlist("events")
        group_members = request.form.get("group_members", "")
        contact_numbers = request.form.get("contact_numbers")

        # Store form data in session
        session['form_data'] = {
            'student_name': name,
            'roll_no': roll,
            'course': course,
            'college': college,
            'college_id': college_id,
            'other_college': other_college,
            'group_members': group_members,
            'contact_numbers': contact_numbers
        }
        session['selected_events'] = selected_events

        # -------- STEP 1: GENERATE QR --------
        if step == "qr":
            if not selected_events:
                return render_template("register.html", 
                                     form_data=session.get('form_data', {}),
                                     banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))

            total = calculate_total(selected_events, college)

            upi_link = (
                f"upi://pay?"
                f"pa=6393444944@upi&"
                f"pn=ZEAL10&"
                f"am={total}&"
                f"cu=INR"
            )

            qr_file = f"{roll}_qr.png"
            qr_path = os.path.join(QR_DIR, qr_file)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(upi_link)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(qr_path)

            return render_template(
                "register.html",
                qr=qr_file,
                total=total,
                form_data=session.get('form_data', {}),
                selected_events=session.get('selected_events', []),
                banner_exists=os.path.exists('static/images/zeal_banner.jpeg')
            )

        # -------- STEP 2: FINAL SUBMIT --------
        if step == "final":
            screenshot = request.files.get("payment_screenshot")
            
            if not screenshot or not allowed_file(screenshot.filename):
                return "Payment screenshot required with valid format (PNG, JPG, JPEG)", 400

            screenshot_name = secure_filename(f"{roll}_{screenshot.filename}")
            screenshot.save(os.path.join(UPLOAD_DIR, screenshot_name))

            total = calculate_total(selected_events, college)

            try:
                db = get_db_connection()
                cursor = db.cursor()
                
                cursor.execute("""
                    INSERT INTO registrations
                    (student_name, roll_no, course, college, college_id,
                     other_college, events, group_members, contact_numbers,
                     total_amount, payment_screenshot)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    name,
                    roll,
                    course,
                    college,
                    college_id,
                    other_college,
                    ", ".join(selected_events),
                    group_members,
                    contact_numbers,
                    total,
                    screenshot_name
                ))
                
                db.commit()
                cursor.close()
                db.close()
                
                # Clear session
                session.pop('form_data', None)
                session.pop('selected_events', None)
                
                return render_template("register.html", 
                                     success=True,
                                     banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))
            
            except Exception as e:
                print(f"Database error: {e}")
                return f"Registration failed: {str(e)}", 500

    # GET request - show form
    return render_template("register.html", 
                         form_data=session.get('form_data', {}),
                         selected_events=session.get('selected_events', []),
                         banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM registrations ORDER BY created_at DESC")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template("admin.html", data=data)
    except Exception as e:
        return f"Error loading admin page: {str(e)}", 500

# ---------------- VIEW PAYMENT SCREENSHOT ----------------
@app.route("/uploads/payments/<filename>")
def view_payment(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------------- START ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)