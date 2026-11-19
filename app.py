from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    jsonify,
    current_app
)

from config import BASE_DIR, Config
from database import db, init_tables, get_db, get_db_cursor

from routes.main import main_bp
from routes.internship_routes import internship_bp
from routes.auth_routes import auth_bp
from routes.apply_routes import apply_bp
from routes.recruiter_routes import recruiter_bp
from routes.admin_routes import admin_bp

from extensions import mail

import os
import logging
from werkzeug.utils import secure_filename


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.config.from_object(Config)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)


# ============================================================
# MAIL CONFIGURATION
# ============================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True

app.config["MAIL_USERNAME"] = os.environ.get(
    "MAIL_USERNAME",
    ""
)

app.config["MAIL_PASSWORD"] = os.environ.get(
    "MAIL_PASSWORD",
    ""
)

app.config["MAIL_DEFAULT_SENDER"] = (
    app.config["MAIL_USERNAME"]
)

mail.init_app(app)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

app.config["UPLOAD_FOLDER"] = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

app.config["APPLICATION_UPLOAD_FOLDER"] = os.path.join(
    BASE_DIR,
    "static",
    "applications"
)

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)

os.makedirs(
    app.config["APPLICATION_UPLOAD_FOLDER"],
    exist_ok=True
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO
)


# ============================================================
# REQUEST LOGGER
# ============================================================

@app.before_request
def log_request():
    app.logger.info(
        "Page accessed: %s",
        request.path
    )


# ============================================================
# DATABASE DEBUG
# ============================================================

@app.route("/debug/db-path")
def debug_db_path():

    return (
        f"Current DB path: "
        f"{current_app.config['DATABASE']}"
    )


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(e):

    app.logger.warning(
        "404 Error: %s",
        e
    )

    return "Page not found", 404


# ============================================================
# STATIC FILES
# ============================================================

@app.route("/static/<path:filename>")
def static_files(filename):

    return send_from_directory(
        os.path.join(
            app.root_path,
            "static"
        ),
        filename
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

db.init_app(app)


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(main_bp)

app.register_blueprint(
    internship_bp,
    url_prefix="/internship_bp"
)

app.register_blueprint(
    auth_bp,
    url_prefix="/auth"
)

app.register_blueprint(apply_bp)

app.register_blueprint(recruiter_bp)

app.register_blueprint(admin_bp)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

with app.app_context():

    db.create_all()

    init_tables()


# ============================================================
# HOME
# ============================================================

@app.route("/")
@app.route("/index.html")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# INTERNSHIPS
# ============================================================

@app.route("/internships.html")
@app.route("/internships")
def internships():

    cursor = get_db_cursor()

    cursor.execute("""
        SELECT *
        FROM internships
        ORDER BY internship_id DESC
    """)

    internships_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "internships.html",
        internships=[
            dict(row)
            for row in internships_data
        ],
        search_query=""
    )


# ============================================================
# SEARCH INTERNSHIPS
# ============================================================

@app.route("/search_internships")
def search_internships():

    query = request.args.get(
        "q",
        ""
    ).strip()

    cursor = get_db_cursor()

    if query:

        search = f"%{query}%"

        cursor.execute("""
            SELECT *
            FROM internships
            WHERE title LIKE ?
               OR company LIKE ?
               OR department LIKE ?
               OR location LIKE ?
               OR internship_type LIKE ?
               OR skills LIKE ?
               OR description LIKE ?
            ORDER BY internship_id DESC
        """, (
            search,
            search,
            search,
            search,
            search,
            search,
            search
        ))

    else:

        cursor.execute("""
            SELECT *
            FROM internships
            ORDER BY internship_id DESC
        """)

    internships_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "internships.html",
        internships=[
            dict(row)
            for row in internships_data
        ],
        search_query=query
    )


# ============================================================
# VIEW SINGLE INTERNSHIP
# ============================================================

@app.route(
    "/internships/<int:internship_id>"
)
def view_internship(internship_id):

    cursor = get_db_cursor()

    cursor.execute(
        """
        SELECT *
        FROM internships
        WHERE internship_id = ?
        """,
        (internship_id,)
    )

    internship = cursor.fetchone()

    cursor.close()

    if not internship:

        return (
            "Internship not found",
            404
        )

    internship_dict = dict(
        internship
    )

    # --------------------------------------------------------
    # TAGLINE
    # --------------------------------------------------------

    internship_dict["tagline"] = (
        "Exciting opportunity "
        "to learn and grow!"
    )


    # --------------------------------------------------------
    # RESPONSIBILITIES
    # --------------------------------------------------------

    description = (
        internship_dict.get(
            "description"
        )
        or ""
    )

    internship_dict["responsibilities"] = [
        item.strip()
        for item in description.split(".")
        if item.strip()
    ][:5]


    # --------------------------------------------------------
    # POSITIONS
    # --------------------------------------------------------

    internship_dict["positions"] = (
        internship_dict.get(
            "openings",
            0
        )
    )


    # --------------------------------------------------------
    # INTERNSHIP TYPE
    # --------------------------------------------------------

    internship_dict["type"] = (
        internship_dict.get(
            "internship_type",
            ""
        )
    )


    # --------------------------------------------------------
    # COMPANY LOGO
    # --------------------------------------------------------

    if internship_dict.get(
        "company_logo"
    ):

        internship_dict["logo"] = (
            "uploads/"
            + internship_dict[
                "company_logo"
            ]
        )

    else:

        internship_dict["logo"] = (
            "images/default.png"
        )


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "internship_roles/sample.html",
        internship=internship_dict
    )


# ============================================================
# ABOUT US
# ============================================================

@app.route("/about_us")
@app.route("/about_us.html")
def about_us():

    return render_template(
        "about_us.html"
    )


# ============================================================
# CONTACT US
# ============================================================

@app.route("/contact_us")
@app.route("/contact_us.html")
def contact_us():

    return render_template(
        "contact_us.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "email" not in session:

        return redirect(
            url_for("auth_bp.login")
        )


    # ========================================================
    # STUDENT
    # ========================================================

    if (
        session.get("logged_in")
        and session.get("role")
        == "student"
    ):

        db_conn = get_db()

        email = session.get(
            "email"
        )


        # Candidate
        candidate = db_conn.execute(
            """
            SELECT
                first_name,
                last_name
            FROM candidates
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        if candidate:

            fullname = (
                f"{candidate['first_name']} "
                f"{candidate['last_name']}"
            )

        else:

            fullname = ""


        # Student info
        student_info = db_conn.execute(
            """
            SELECT *
            FROM student_info
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        # Applied internships
        applied = db_conn.execute(
            """
            SELECT
                a.*,
                i.title,
                i.company,
                i.location
            FROM apply_internships a

            LEFT JOIN internships i
                ON a.internship_id =
                   i.internship_id

            WHERE a.email = ?

            ORDER BY a.application_id DESC
            """,
            (email,)
        ).fetchall()


        return render_template(
            "dashboard.html",
            name=fullname,
            email=email,
            student_info=student_info,
            applied_internships=[
                dict(row)
                for row in applied
            ]
        )


    # ========================================================
    # RECRUITER
    # ========================================================

    if (
        session.get("logged_in")
        and session.get("role")
        == "recruiter"
    ):

        return redirect(
            url_for(
                "recruiter_bp.recruiter_dashboard"
            )
        )


    # ========================================================
    # NOT LOGGED IN
    # ========================================================

    flash(
        "Please log in to access the dashboard.",
        "warning"
    )

    return redirect(
        url_for("auth_bp.login")
    )


# ============================================================
# UPDATE STUDENT INFORMATION
# ============================================================

@app.route(
    "/update_student_info",
    methods=["POST"]
)
def update_student_info():

    if (
        not session.get("logged_in")
        or session.get("role")
        != "student"
    ):

        return jsonify({
            "error": "Unauthorized"
        }), 401


    session_email = session.get(
        "email"
    )

    posted_email = (
        request.form.get("email")
        or session_email
    )

    name = request.form.get(
        "name"
    )

    phone = request.form.get(
        "phone"
    )

    location = request.form.get(
        "location"
    )

    education = request.form.get(
        "education"
    )


    profile_picture = None
    resume = None


    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )


    # PROFILE PICTURE
    if "profile_picture" in request.files:

        file = request.files[
            "profile_picture"
        ]

        if file and file.filename:

            filename = secure_filename(
                file.filename
            )

            file.save(
                os.path.join(
                    upload_folder,
                    filename
                )
            )

            profile_picture = filename


    # RESUME
    if "resume" in request.files:

        file = request.files[
            "resume"
        ]

        if file and file.filename:

            filename = secure_filename(
                file.filename
            )

            file.save(
                os.path.join(
                    upload_folder,
                    filename
                )
            )

            resume = filename


    # DATABASE
    db_conn = get_db()

    existing = db_conn.execute(
        """
        SELECT *
        FROM student_info
        WHERE email = ?
        """,
        (session_email,)
    ).fetchone()


    if existing:

        db_conn.execute(
            """
            UPDATE student_info

            SET
                full_name = ?,
                email = ?,
                phone = ?,
                location = ?,
                education = ?,
                profile_picture =
                    COALESCE(
                        ?,
                        profile_picture
                    ),
                resume =
                    COALESCE(
                        ?,
                        resume
                    )

            WHERE email = ?
            """,
            (
                name,
                posted_email,
                phone,
                location,
                education,
                profile_picture,
                resume,
                session_email
            )
        )


    else:

        db_conn.execute(
            """
            INSERT INTO student_info
            (
                full_name,
                email,
                phone,
                location,
                education,
                profile_picture,
                resume
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                posted_email,
                phone,
                location,
                education,
                profile_picture,
                resume
            )
        )


    db_conn.commit()


    return jsonify({
        "success": True,
        "message":
            "Your profile information "
            "has been updated."
    })


# ============================================================
# LOGIN HTML
# ============================================================

@app.route("/login.html")
def login_html():

    return redirect(
        url_for("main.login")
    )


# ============================================================
# CHECK LOGIN STATUS
# ============================================================

@app.route(
    "/api/check_login_status",
    methods=["GET"]
)
def check_login_status():

    if session.get("logged_in"):

        role = session.get(
            "role",
            "unknown"
        )


        if role == "student":

            dashboard_url = url_for(
                "dashboard"
            )

        elif role == "recruiter":

            dashboard_url = url_for(
                "recruiter_bp.recruiter_dashboard"
            )

        elif role == "admin":

            dashboard_url = url_for(
                "admin_bp.admin_dashboard"
            )

        else:

            dashboard_url = url_for(
                "home"
            )


        return jsonify({
            "logged_in": True,
            "role": role,
            "dashboard_url":
                dashboard_url,
            "email":
                session.get("email")
        })


    return jsonify({
        "logged_in": False
    })


# ============================================================
# LOGOUT
# ============================================================

@app.route(
    "/api/logout",
    methods=["POST"]
)
def logout():

    session.clear()

    return jsonify({
        "message":
            "Logged out successfully"
    }), 200


# ============================================================
# APPLY INTERNSHIP
# ============================================================

@app.route(
    "/apply/internship.html"
)
def apply_internship_html():

    return redirect(
        url_for(
            "apply_bp.apply_form",
            internship_id=1
        )
    )


# ============================================================
# RECRUITER
# ============================================================

@app.route("/recruiter")
def recruiter():

    if "email" not in session:

        return redirect(
            url_for("main.login")
        )


    if (
        session.get("logged_in")
        and session.get("role")
        == "recruiter"
    ):

        return redirect(
            url_for(
                "recruiter_bp.recruiter_dashboard"
            )
        )


    return redirect(
        url_for("home")
    )


# ============================================================
# INTERNSHIP ROLE PAGE
# ============================================================

@app.route(
    "/internship_roles/<role>"
)
def role_page(role):

    try:

        return render_template(
            f"internship_roles/{role}.html"
        )

    except Exception:

        return (
            "Page not found",
            404
        )


# ============================================================
# RESUME BUILDER
# ============================================================

@app.route(
    "/resume-builder/index.html"
)
def serve_resume_builder():

    return send_from_directory(
        os.path.join(
            app.root_path,
            "resume-builder"
        ),
        "index.html"
    )


@app.route(
    "/resume-builder/<path:filename>"
)
def serve_resume_builder_files(filename):

    return send_from_directory(
        os.path.join(
            app.root_path,
            "resume-builder"
        ),
        filename
    )


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )