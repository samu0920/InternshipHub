from flask import Blueprint, render_template, request, redirect, url_for, session
from database import get_db_cursor

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
# ==================== ADMIN LOGOUT ====================

@admin_bp.route("/logout")
def logout():

    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)

    return redirect(url_for("admin.login"))


# ==================== ADMIN LOGIN ====================

@admin_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        cursor = get_db_cursor()

        cursor.execute(
            "SELECT * FROM admins WHERE username = ? AND password = ?",
            (username, password)
        )

        admin = cursor.fetchone()
        cursor.close()

        if admin:
            session["admin_logged_in"] = True
            session["admin_username"] = username

            return redirect(url_for("admin.dashboard"))

        return "Invalid username or password"

    return render_template("admin_login.html")


# ==================== ADMIN DASHBOARD ====================

@admin_bp.route("/dashboard")
def dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM candidates")
    students = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM companies")
    companies = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM internships")
    internships = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM apply_internships")
    applications = cursor.fetchone()["count"]

    cursor.close()

    return render_template(
        "admin_dashboard.html",
        students=students,
        companies=companies,
        internships=internships,
        applications=applications
    )


# ==================== MANAGE STUDENTS ====================

@admin_bp.route("/students")
def students():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute("""
        SELECT candidate_id,
               first_name,
               last_name,
               email,
               created_at
        FROM candidates
        ORDER BY candidate_id DESC
    """)

    students = cursor.fetchall()
    cursor.close()

    return render_template(
        "admin_students.html",
        students=students
    )


# ==================== DELETE STUDENT ====================

@admin_bp.route("/students/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute(
        "DELETE FROM candidates WHERE candidate_id = ?",
        (student_id,)
    )

    cursor.connection.commit()
    cursor.close()

    return redirect(url_for("admin.students"))


# ==================== MANAGE COMPANIES ====================

@admin_bp.route("/companies")
def companies():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute("""
        SELECT company_id,
               company_name,
               contact_email,
               contact_number,
               industry_type,
               created_at
        FROM companies
        ORDER BY company_id DESC
    """)

    companies = cursor.fetchall()
    cursor.close()

    return render_template(
        "admin_companies.html",
        companies=companies
    )


# ==================== DELETE COMPANY ====================

@admin_bp.route("/companies/delete/<int:company_id>", methods=["POST"])
def delete_company(company_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute(
        "DELETE FROM companies WHERE company_id = ?",
        (company_id,)
    )

    cursor.connection.commit()
    cursor.close()

    return redirect(url_for("admin.companies"))


# ==================== MANAGE INTERNSHIPS ====================

@admin_bp.route("/internships")
def internships():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute("""
        SELECT internship_id,
               title,
               company,
               department,
               location,
               internship_type,
               stipend,
               openings,
               deadline
        FROM internships
        ORDER BY internship_id DESC
    """)

    internships = cursor.fetchall()
    cursor.close()

    return render_template(
        "admin_internships.html",
        internships=internships
    )


# ==================== DELETE INTERNSHIP ====================

@admin_bp.route("/internships/delete/<int:internship_id>", methods=["POST"])
def delete_internship(internship_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute(
        "DELETE FROM internships WHERE internship_id = ?",
        (internship_id,)
    )

    cursor.connection.commit()
    cursor.close()

    return redirect(url_for("admin.internships"))


# ==================== APPLICATIONS ====================

@admin_bp.route("/applications")
def applications():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    cursor.execute("""
        SELECT
            application_id,
            first_name,
            last_name,
            email,
            phone,
            university,
            degree,
            major,
            grad_year,
            cgpa,
            skills,
            internship_type,
            preferred_duration,
            created_at
        FROM apply_internships
        ORDER BY application_id DESC
    """)

    applications = cursor.fetchall()
    cursor.close()

    return render_template(
        "admin_applications.html",
        applications=applications
    )


# ==================== REPORTS ====================

@admin_bp.route("/reports")
def reports():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.login"))

    cursor = get_db_cursor()

    # Total students
    cursor.execute("SELECT COUNT(*) AS count FROM candidates")
    total_students = cursor.fetchone()["count"]

    # Total companies
    cursor.execute("SELECT COUNT(*) AS count FROM companies")
    total_companies = cursor.fetchone()["count"]

    # Total internships
    cursor.execute("SELECT COUNT(*) AS count FROM internships")
    total_internships = cursor.fetchone()["count"]

    # Total applications
    cursor.execute("SELECT COUNT(*) AS count FROM apply_internships")
    total_applications = cursor.fetchone()["count"]

    # Internship type report
    cursor.execute("""
        SELECT internship_type, COUNT(*) AS count
        FROM internships
        GROUP BY internship_type
    """)
    internship_types = cursor.fetchall()

    # Application type report
    cursor.execute("""
        SELECT internship_type, COUNT(*) AS count
        FROM apply_internships
        GROUP BY internship_type
    """)
    application_types = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin_reports.html",
        total_students=total_students,
        total_companies=total_companies,
        total_internships=total_internships,
        total_applications=total_applications,
        internship_types=internship_types,
        application_types=application_types
    )