from flask import Flask, render_template, request, send_from_directory, session, send_file, redirect
import json
import qrcode
import os
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
from io import BytesIO
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "zeal10_secret_key_2025"

# ---------------- CLOUDINARY CONFIG ----------------
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# ---------------- CONFIG ----------------
QR_DIR = "static/qr"
os.makedirs(QR_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# ---------------- MYSQL CONFIG ----------------
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'zeal10_db'),
    
}

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
    "Rangoli Competition": 100,
    "Cook without Fire": 100,
    "Ad-Mad Show": 100,
    "Eco-Fashion / Recycled Clothing Show": 100,
    "T-Shirt Painting": 100,
    "Eco-Voice Debate / GreenSpeak Debate": 100,
    "Face Painting Competition": 100,
    "BGMI": 100,
    "Beat Boxing": 100,
    "Band": 500,
    # Category-based events
    "Dance Competition - Solo": 100,
    "Dance Competition - Duet": 200,
    "Dance Competition - Group": 300,
    "Fashion Show Competition - Solo": 100,
    "Fashion Show Competition - Duet": 200,
    "Fashion Show Competition - Group": 300,
    "Singing - Solo": 100,
    "Singing - Duet": 200,
}

# ---------------- DATABASE FUNCTIONS ----------------
def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    """Initialize MySQL database and create tables if they don't exist"""
    try:
        # First, connect without specifying database to create it if needed
        temp_config = DB_CONFIG.copy()
        database_name = temp_config.pop('database')
        
        connection = mysql.connector.connect(**temp_config)
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        print(f"Database '{database_name}' checked/created successfully!")
        
        cursor.close()
        connection.close()
        
        # Now connect to the specific database
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database!")
            return False
            
        cursor = connection.cursor()
        
        # Create registrations table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS registrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            roll_no VARCHAR(100) NOT NULL,
            course VARCHAR(255) NOT NULL,
            college VARCHAR(255) NOT NULL,
            college_id VARCHAR(100),
            other_college VARCHAR(255),
            events TEXT NOT NULL,
            group_members TEXT,
            contact_numbers VARCHAR(255) NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            payment_screenshot_url TEXT NOT NULL,
            payment_status VARCHAR(50) DEFAULT 'Submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_student_name (student_name),
            INDEX idx_roll_no (roll_no),
            INDEX idx_college (college),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        
        print("Table 'registrations' checked/created successfully!")
        print("Database initialization completed!")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"Error during database initialization: {e}")
        traceback.print_exc()
        return False

def add_registration(registration_data):
    """Add a new registration to the database"""
    try:
        connection = get_db_connection()
        if connection is None:
            raise Exception("Database connection failed")
            
        cursor = connection.cursor()
        
        insert_query = """
        INSERT INTO registrations 
        (student_name, roll_no, course, college, college_id, other_college, 
         events, group_members, contact_numbers, total_amount, 
         payment_screenshot_url, payment_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            registration_data['student_name'],
            registration_data['roll_no'],
            registration_data['course'],
            registration_data['college'],
            registration_data.get('college_id', ''),
            registration_data.get('other_college', ''),
            registration_data['events'],
            registration_data.get('group_members', ''),
            registration_data['contact_numbers'],
            registration_data['total_amount'],
            registration_data['payment_screenshot_url'],
            registration_data.get('payment_status', 'Submitted')
        )
        
        cursor.execute(insert_query, values)
        connection.commit()
        
        registration_id = cursor.lastrowid
        
        print(f"Registration added successfully with ID: {registration_id}")
        
        cursor.close()
        connection.close()
        
        return registration_id
        
    except Error as e:
        print(f"Error adding registration: {e}")
        traceback.print_exc()
        raise

def get_all_registrations():
    """Get all registrations sorted by created_at (newest first)"""
    try:
        connection = get_db_connection()
        if connection is None:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT id, student_name, roll_no, course, college, college_id, 
               other_college, events, group_members, contact_numbers, 
               total_amount, payment_screenshot_url, payment_status, 
               created_at
        FROM registrations
        ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        registrations = cursor.fetchall()
        
        print(f"Retrieved {len(registrations)} registrations from database")
        
        cursor.close()
        connection.close()
        
        return registrations
        
    except Error as e:
        print(f"Error retrieving registrations: {e}")
        traceback.print_exc()
        return []

def get_registration_by_id(registration_id):
    """Get a specific registration by ID"""
    try:
        connection = get_db_connection()
        if connection is None:
            return None
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT * FROM registrations WHERE id = %s
        """
        
        cursor.execute(query, (registration_id,))
        registration = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return registration
        
    except Error as e:
        print(f"Error retrieving registration: {e}")
        return None

# Initialize database on startup
print("Initializing database...")
if init_db():
    print("Database ready!")
else:
    print("Database initialization failed!")

# ---------------- HELPERS ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_cloudinary(file, roll_no):
    """Upload file to Cloudinary and return the URL"""
    try:
        public_id = f"zeal10/payments/{roll_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = cloudinary.uploader.upload(
            file,
            public_id=public_id,
            folder="zeal10/payments",
            resource_type="image",
            overwrite=True
        )
        
        print(f"File uploaded to Cloudinary: {result['secure_url']}")
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise

def parse_events_with_categories(form_data):
    """Parse events and their categories from form data"""
    selected_events = form_data.getlist("events")
    events_list = []
    
    print(f"Raw selected events: {selected_events}")
    print(f"All form keys: {list(form_data.keys())}")
    
    category_map = {}
    for key in form_data.keys():
        if key.startswith('category_'):
            event_idx = key.replace('category_', '')
            category_map[event_idx] = form_data.get(key)
            print(f"Found category: {key} = {form_data.get(key)}")
    
    for i, event in enumerate(selected_events):
        category_found = False
        for cat_idx, category in category_map.items():
            checkbox_indices = [j for j, e in enumerate(selected_events) if e == event]
            if str(cat_idx) in [str(idx) for idx in range(len(form_data.getlist("events")))]:
                all_event_checkboxes = [(k, v) for k, v in form_data.items() if k == 'events']
                test_key = f"category_{i}"
                if test_key in category_map:
                    event_with_category = f"{event} - {category_map[test_key]}"
                    events_list.append(event_with_category)
                    print(f"Event with category (matched by index): {event_with_category}")
                    category_found = True
                    break
        
        if not category_found:
            if event in ["Dance Competition", "Fashion Show Competition", "Singing"]:
                for cat_idx, category in category_map.items():
                    if category:
                        event_with_category = f"{event} - {category}"
                        events_list.append(event_with_category)
                        print(f"Event with category (fallback): {event_with_category}")
                        category_found = True
                        del category_map[cat_idx]
                        break
            
            if not category_found:
                events_list.append(event)
                print(f"Event without category: {event}")
    
    print(f"Final parsed events: {events_list}")
    return events_list

def calculate_total_from_events(events_list, college):
    """Calculate total amount from events list"""
    total = 0
    for event in events_list:
        price = EVENT_PRICES.get(event, 0)
        if price == 0:
            print(f"WARNING: No price found for event: {event}")
        if college == "Mangalmay Group of Institutions":
            price = price // 2
        total += price
        print(f"Event: {event}, Price: ₹{price}, Running Total: ₹{total}")
    print(f"Final total calculated: ₹{total} for {len(events_list)} events (College: {college})")
    return total

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        step = request.form.get("step")
        print(f"Processing step: {step}")
        
        name = request.form.get("student_name")
        roll = request.form.get("roll_no")
        course = request.form.get("course")
        college = request.form.get("college")
        college_id = request.form.get("college_id", "")
        other_college = request.form.get("other_college", "")
        group_members = request.form.get("group_members", "")
        contact_numbers = request.form.get("contact_numbers")
        
        events_list = parse_events_with_categories(request.form)

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
        session['selected_events'] = events_list

        if step == "qr":
            if not events_list:
                print("No events selected!")
                return render_template("register.html", 
                                     form_data=session.get('form_data', {}),
                                     selected_events=session.get('selected_events', []),
                                     events=EVENT_PRICES,
                                     error="Please select at least one event",
                                     banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))

            total = calculate_total_from_events(events_list, college)

            upi_link = (
                f"upi://pay?"
                f"pa=9871223900@ptaxis&"
                f"pn=ZEAL10&"
                f"am={total}&"
                f"cu=INR"
            )

            qr_file = f"{roll}_qr.png"
            qr_path = os.path.join(QR_DIR, qr_file)
            
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
            
            print(f"QR code generated: {qr_file} for amount: ₹{total}")

            return render_template(
                "register.html",
                qr=qr_file,
                total=total,
                form_data=session.get('form_data', {}),
                selected_events=session.get('selected_events', []),
                events=EVENT_PRICES,
                banner_exists=os.path.exists('static/images/zeal_banner.jpeg')
            )

        if step == "final":
            screenshot = request.files.get("payment_screenshot")
            
            if not screenshot or screenshot.filename == '':
                print("No screenshot uploaded!")
                return "Payment screenshot required", 400
                
            if not allowed_file(screenshot.filename):
                print(f"Invalid file format: {screenshot.filename}")
                return "Invalid file format. Please upload PNG, JPG, or JPEG", 400

            try:
                cloudinary_url = upload_to_cloudinary(screenshot, roll)
                print(f"Screenshot uploaded to Cloudinary: {cloudinary_url}")
            except Exception as e:
                print(f"Cloudinary upload failed: {e}")
                return f"Failed to upload screenshot: {str(e)}", 500

            total = calculate_total_from_events(events_list, college)

            try:
                registration_data = {
                    "student_name": name,
                    "roll_no": roll,
                    "course": course,
                    "college": college,
                    "college_id": college_id,
                    "other_college": other_college,
                    "events": ", ".join(events_list),
                    "group_members": group_members,
                    "contact_numbers": contact_numbers,
                    "total_amount": total,
                    "payment_screenshot_url": cloudinary_url,
                    "payment_status": "Submitted"
                }
                
                reg_id = add_registration(registration_data)
                print(f"Registration completed with ID: {reg_id}")
                
                session.pop('form_data', None)
                session.pop('selected_events', None)
                
                return render_template("register.html", 
                                     success=True,
                                     registration_id=reg_id,
                                     form_data={},
                                     selected_events=[],
                                     events=EVENT_PRICES,
                                     banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))
            
            except Exception as e:
                print(f"Database error: {e}")
                traceback.print_exc()
                return f"Registration failed: {str(e)}", 500

    return render_template("register.html", 
                         form_data=session.get('form_data', {}),
                         selected_events=session.get('selected_events', []),
                         events=EVENT_PRICES,
                         banner_exists=os.path.exists('static/images/zeal_banner.jpeg'))

# ---------------- ADMIN ----------------
@app.route("/adminmgizeal")
def admin():
    try:
        data = get_all_registrations()
        print(f"Displaying {len(data)} registrations on admin page")
        
        return render_template("admin.html", data=data)
    except Exception as e:
        print(f"Error loading admin page: {e}")
        traceback.print_exc()
        return f"Error loading admin page: {str(e)}", 500

# ---------------- EXPORT TO EXCEL ----------------
@app.route("/adminmgizeal/export")
def export_excel():
    try:
        data = get_all_registrations()
        print(f"Exporting {len(data)} registrations")

        if not data:
            df = pd.DataFrame(columns=[
                'id', 'student_name', 'roll_no', 'course', 'college', 
                'college_id', 'other_college', 'events', 'group_members', 
                'contact_numbers', 'total_amount', 'payment_screenshot_url', 
                'payment_status', 'created_at'
            ])
        else:
            df = pd.DataFrame(data)
            
            column_order = [
                'id', 'student_name', 'roll_no', 'course', 'college', 
                'college_id', 'other_college', 'events', 'group_members', 
                'contact_numbers', 'total_amount', 'payment_status',
                'payment_screenshot_url', 'created_at'
            ]
            
            column_order = [col for col in column_order if col in df.columns]
            df = df[column_order]
        
            if 'created_at' in df.columns and not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d-%m-%Y %H:%M:%S')
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Registrations')
            
            worksheet = writer.sheets['Registrations']
            for idx, col in enumerate(df.columns):
                if not df.empty:
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    ) + 2
                else:
                    max_length = len(str(col)) + 2
                    
                if idx < 26:
                    col_letter = chr(65 + idx)
                else:
                    col_letter = chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
                    
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        
        output.seek(0)
        
        filename = f"ZEAL_10_Registrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        print(f"Excel exported: {filename}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        print(f"Error exporting data: {e}")
        traceback.print_exc()
        return f"Error exporting data: {str(e)}", 500

# ---------------- DEBUG ROUTE ----------------
@app.route("/debug/db")
def debug_db():
    """Debug route to check database status"""
    try:
        connection = get_db_connection()
        if connection is None:
            return {"error": "Cannot connect to database", "config": {k: v for k, v in DB_CONFIG.items() if k != 'password'}}, 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Get table info
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        # Get registration count
        cursor.execute("SELECT COUNT(*) as count FROM registrations")
        count_result = cursor.fetchone()
        
        # Get recent registrations
        cursor.execute("SELECT * FROM registrations ORDER BY created_at DESC LIMIT 5")
        recent = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return {
            "status": "connected",
            "database": DB_CONFIG['database'],
            "tables": tables,
            "total_registrations": count_result['count'],
            "recent_registrations": recent,
            "cloudinary_configured": bool(os.getenv('CLOUDINARY_CLOUD_NAME'))
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}, 500

# ---------------- START ----------------
if __name__ == "__main__":
    print(f"Starting ZEAL 10.0 Registration System")
    print(f"MySQL Host: {DB_CONFIG['host']}")
    print(f"MySQL Database: {DB_CONFIG['database']}")
    print(f"QR directory: {os.path.abspath(QR_DIR)}")
    print(f"Cloudinary configured: {bool(os.getenv('CLOUDINARY_CLOUD_NAME'))}")
    app.run(host="0.0.0.0", port=5000, debug=True)