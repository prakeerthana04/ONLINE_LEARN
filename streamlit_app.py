import streamlit as st
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Online Learning Platform", page_icon="📚", layout="wide")

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)

db = get_db()

def init_db():
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            fee INTEGER
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            course_id INTEGER,
            payment_status TEXT,
            completion_status TEXT,
            progress INTEGER
        )
    """)
    db.commit()

def seed_data():
    db.execute("INSERT OR IGNORE INTO admins (username,password) VALUES ('admin','admin123')")

    count = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if count == 0:
        db.executemany("INSERT INTO courses (name, fee) VALUES (?,?)", [
            ("Python Basics", 999),
            ("Machine Learning", 1999),
            ("Web Development", 1499),
        ])
    db.commit()

init_db()
seed_data()

# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None

# ---------------- AUTH ----------------
def login():
    st.subheader("🔐 Login")

    role = st.radio("Login as", ["User", "Admin"])
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if role == "User":
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            if user:
                st.session_state.user_id = user[0]
                st.session_state.username = user[1]
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("Invalid user credentials")
        else:
            admin = db.execute("SELECT * FROM admins WHERE username=? AND password=?", (u, p)).fetchone()
            if admin:
                st.session_state.user_id = admin[0]
                st.session_state.username = admin[1]
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid admin credentials")

def register():
    st.subheader("📝 Register")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Register"):
        try:
            db.execute("INSERT INTO users (username,password) VALUES (?,?)", (u, p))
            db.commit()
            st.success("Registration successful. Please login.")
        except:
            st.error("Username already exists")

# ---------------- COURSES ----------------
def enroll(course_id):
    db.execute("""INSERT INTO enrollments 
        (user_id,course_id,payment_status,completion_status,progress) 
        VALUES (?,?,?,?,?)""",
        (st.session_state.user_id, course_id, "Pending", "Not Completed", 0))
    db.commit()
    st.success("Enrollment successful")

def show_courses():
    st.subheader("📚 Available Courses")
    courses = db.execute("SELECT * FROM courses").fetchall()

    for c in courses:
        st.markdown(f"### {c[1]} — ₹{c[2]}")
        if st.button("Enroll", key=f"enroll_{c[0]}"):
            enroll(c[0])

# ---------------- CERTIFICATE PDF ----------------
def generate_certificate_pdf(username, course):
    file_name = f"certificate_{username}_{course}.pdf"

    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-150, "CERTIFICATE OF COMPLETION")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height-240, "This is to certify that")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height-280, username)

    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height-330, "has successfully completed the course")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height-370, course)

    c.drawCentredString(width/2, height-430, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

    c.showPage()
    c.save()
    return file_name

# ---------------- MY COURSES ----------------
def my_courses():
    st.subheader("🎓 My Courses")

    rows = db.execute("""
        SELECT courses.name,enrollments.payment_status,
               enrollments.completion_status,enrollments.progress,enrollments.id
        FROM enrollments
        JOIN courses ON courses.id=enrollments.course_id
        WHERE enrollments.user_id=?
    """,(st.session_state.user_id,)).fetchall()

    for r in rows:
        st.markdown(f"### {r[0]}")
        st.progress(r[3])

        col1, col2, col3 = st.columns(3)

        if r[1] == "Pending":
            if col1.button("Pay", key=f"pay_{r[4]}"):
                db.execute("UPDATE enrollments SET payment_status='Paid' WHERE id=?", (r[4],))
                db.commit()
                st.rerun()

        if r[2] == "Not Completed":
            if col2.button("Complete Course", key=f"comp_{r[4]}"):
                db.execute("""UPDATE enrollments 
                              SET completion_status='Completed', progress=100 
                              WHERE id=?""", (r[4],))
                db.commit()
                st.rerun()

        if r[1] == "Paid" and r[2] == "Completed":
            if col3.button("Download Certificate", key=f"cert_{r[4]}"):
                pdf = generate_certificate_pdf(st.session_state.username, r[0])
                with open(pdf, "rb") as f:
                    st.download_button("⬇ Download PDF", f, file_name=pdf)

# ---------------- ADMIN PANEL ----------------
def admin_panel():
    st.subheader("🛠 Admin Dashboard")

    users = pd.read_sql("SELECT * FROM users", db)
    courses = pd.read_sql("SELECT * FROM courses", db)
    enrollments = pd.read_sql("""
        SELECT users.username, courses.name, 
               enrollments.payment_status,
               enrollments.completion_status,
               enrollments.progress
        FROM enrollments
        JOIN users ON users.id=enrollments.user_id
        JOIN courses ON courses.id=enrollments.course_id
    """, db)

    st.write("### 👤 Users")
    st.dataframe(users)

    st.write("### 📚 Courses")
    st.dataframe(courses)

    st.write("### 🎓 Enrollments & Progress")
    st.dataframe(enrollments)

# ---------------- LOGOUT ----------------
def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

# ---------------- UI ----------------
st.title("📖 Online Learning Platform")

if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        login()
    with tab2:
        register()

else:
    st.sidebar.success(f"Welcome {st.session_state.username}")
    st.sidebar.info(f"Role: {st.session_state.role.upper()}")

    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "user":
        menu = st.sidebar.radio("Menu", ["Courses", "My Courses"])
        if menu == "Courses":
            show_courses()
        else:
            my_courses()

    elif st.session_state.role == "admin":
        admin_panel()
