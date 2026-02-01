import streamlit as st
import sqlite3

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)

db = get_db()

# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

# ---------------- AUTH ----------------
def login():
    st.subheader("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u, p)
        ).fetchone()

        if user:
            st.session_state.user_id = user[0]
            st.session_state.username = user[1]
            st.success("Logged in successfully")
            st.rerun()
        else:
            st.error("Invalid credentials")

def register():
    st.subheader("Register")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Register"):
        db.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (u, p)
        )
        db.commit()
        st.success("Registered successfully. Please login.")

# ---------------- COURSES ----------------
def show_courses():
    st.subheader("Available Courses")

    courses = db.execute("SELECT * FROM courses").fetchall()

    for c in courses:
        st.markdown(f"### {c[1]} — ₹{c[2]}")
        if st.button("Enroll", key=f"enroll_{c[0]}"):
            enroll(c[0])

def enroll(course_id):
    existing = db.execute(
        "SELECT * FROM enrollments WHERE user_id=? AND course_id=?",
        (st.session_state.user_id, course_id)
    ).fetchone()

    if existing:
        st.warning("Already enrolled")
        return

    db.execute(
        """INSERT INTO enrollments 
        (user_id, course_id, payment_status, completion_status)
        VALUES (?,?,?,?)""",
        (st.session_state.user_id, course_id, "Pending", "Not Completed")
    )
    db.commit()
    st.success("Enrollment successful")

# ---------------- MY COURSES ----------------
def my_courses():
    st.subheader("My Courses")

    rows = db.execute("""
        SELECT courses.name, enrollments.payment_status,
               enrollments.completion_status,
               courses.fee, enrollments.id
        FROM enrollments
        JOIN courses ON courses.id = enrollments.course_id
        WHERE enrollments.user_id=?
    """, (st.session_state.user_id,)).fetchall()

    for r in rows:
        st.markdown(f"""
        **{r[0]}**  
        💰 Payment: {r[1]}  
        🎓 Status: {r[2]}  
        """)

        col1, col2, col3 = st.columns(3)

        if r[1] == "Pending":
            if col1.button("Pay", key=f"pay_{r[4]}"):
                db.execute(
                    "UPDATE enrollments SET payment_status='Paid' WHERE id=?",
                    (r[4],)
                )
                db.commit()
                st.rerun()

        if r[2] == "Not Completed":
            if col2.button("Complete", key=f"complete_{r[4]}"):
                db.execute(
                    "UPDATE enrollments SET completion_status='Completed' WHERE id=?",
                    (r[4],)
                )
                db.commit()
                st.rerun()

        if r[1] == "Paid" and r[2] == "Completed":
            if col3.button("Certificate", key=f"cert_{r[4]}"):
                certificate(r[0])

# ---------------- CERTIFICATE ----------------
def certificate(course_name):
    st.success("🎉 Certificate Generated")
    st.markdown(
        f"""
        ---
        ## Certificate of Completion  

        This certifies that  
        **{st.session_state.username}**  
        has successfully completed the course  
        **{course_name}**  

        ---
        """
    )

# ---------------- LOGOUT ----------------
def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()

# ---------------- UI ----------------
st.title("📚 Course Enrollment System")

if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        login()
    with tab2:
        register()
else:
    st.sidebar.success(f"Welcome {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout()

    menu = st.sidebar.radio("Menu", ["Courses", "My Courses"])

    if menu == "Courses":
        show_courses()
    else:
        my_courses()
