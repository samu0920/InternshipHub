from flask import (
    Blueprint,
    request,
    jsonify,
    session,
    render_template,
    redirect,
    url_for,
    flash,
    current_app
)

import re
import sqlite3
import os

from database import (
    get_db,
    get_db_cursor,
    db
)

from werkzeug.utils import secure_filename
from sqlalchemy import text

from flask_mail import Message
from extensions import mail


# ============================================================
# BLUEPRINT
# ============================================================

auth_bp = Blueprint(
    "auth_bp",
    __name__
)


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def valid_password(password):

    if not password:
        return False

    pattern = (
        r"^(?=.*[A-Za-z])"
        r"(?=.*\d)"
        r"(?=.*[@$!%*?&])"
        r"[A-Za-z\d@$!%*?&]{8,}$"
    )

    return re.match(pattern, password) is not None


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
    endpoint="login"
)
def login():

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":
        return render_template("login.html")


    cursor = None

    try:

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        email = (
            request.form.get("email")
            or request.form.get("username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        ).strip()

        role = (
            request.form.get("role")
            or ""
        ).strip().lower()


        print("====================================")
        print("LOGIN ATTEMPT")
        print("Email:", email)
        print("Role:", role)
        print("====================================")


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not email:

            return jsonify({
                "error": "Please enter your email"
            }), 400


        if not password:

            return jsonify({
                "error": "Please enter your password"
            }), 400


        if not role:

            return jsonify({
                "error": "Please select your role"
            }), 400


        # ====================================================
        # STUDENT LOGIN
        # ====================================================

        if role == "student":

            cursor = get_db_cursor()

            cursor.execute(
                """
                SELECT
                    candidate_id,
                    first_name,
                    last_name,
                    email,
                    password
                FROM candidates
                WHERE LOWER(email) = LOWER(?)
                """,
                (email,)
            )

            user = cursor.fetchone()


            if not user:

                print(
                    "Student not found:",
                    email
                )

                return jsonify({
                    "error":
                        "Invalid email or password"
                }), 401


            # ------------------------------------------------
            # PASSWORD CHECK
            # ------------------------------------------------

            if user["password"] != password:

                print(
                    "Wrong student password:",
                    email
                )

                return jsonify({
                    "error":
                        "Invalid email or password"
                }), 401


            # ------------------------------------------------
            # CLEAR OLD SESSION
            # ------------------------------------------------

            session.clear()


            # ------------------------------------------------
            # CREATE STUDENT SESSION
            # ------------------------------------------------

            session["user_id"] = (
                user["candidate_id"]
            )

            session["email"] = (
                user["email"]
            )

            session["name"] = (
                f"{user['first_name']} "
                f"{user['last_name']}"
            )

            session["role"] = "student"

            session["logged_in"] = True


            print(
                "STUDENT LOGIN SUCCESS:",
                user["email"]
            )


            return jsonify({
                "success": True,
                "message":
                    "Login successful",
                "redirect":
                    url_for("dashboard")
            }), 200


        # ====================================================
        # RECRUITER LOGIN
        # ====================================================

        elif role == "recruiter":

            cursor = get_db_cursor()

            cursor.execute(
                """
                SELECT
                    company_id,
                    company_name,
                    contact_email,
                    password
                FROM companies
                WHERE LOWER(contact_email) = LOWER(?)
                """,
                (email,)
            )

            user = cursor.fetchone()


            if not user:

                print(
                    "Recruiter not found:",
                    email
                )

                return jsonify({
                    "error":
                        "Invalid email or password"
                }), 401


            # ------------------------------------------------
            # PASSWORD CHECK
            # ------------------------------------------------

            if user["password"] != password:

                print(
                    "Wrong recruiter password:",
                    email
                )

                return jsonify({
                    "error":
                        "Invalid email or password"
                }), 401


            # ------------------------------------------------
            # CLEAR OLD SESSION
            # ------------------------------------------------

            session.clear()


            # ------------------------------------------------
            # CREATE RECRUITER SESSION
            # ------------------------------------------------

            session["user_id"] = (
                user["company_id"]
            )

            session["email"] = (
                user["contact_email"]
            )

            session["name"] = (
                user["company_name"]
            )

            session["role"] = "recruiter"

            session["logged_in"] = True


            print(
                "RECRUITER LOGIN SUCCESS:",
                user["contact_email"]
            )


            return jsonify({
                "success": True,
                "message":
                    "Login successful",
                "redirect":
                    url_for(
                        "recruiter_bp.recruiter_dashboard"
                    )
            }), 200


        # ====================================================
        # ADMIN
        # ====================================================

        elif role == "admin":

            return jsonify({
                "error":
                    "Admin login is not configured yet"
            }), 400


        # ====================================================
        # INVALID ROLE
        # ====================================================

        else:

            return jsonify({
                "error":
                    "Invalid role selected"
            }), 400


    # ========================================================
    # DATABASE ERROR
    # ========================================================

    except sqlite3.Error as e:

        print(
            "DATABASE LOGIN ERROR:",
            repr(e)
        )

        current_app.logger.error(
            "Database login error",
            exc_info=True
        )

        return jsonify({
            "error":
                "Database error: " + str(e)
        }), 500


    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as e:

        print(
            "LOGIN ERROR:",
            repr(e)
        )

        current_app.logger.error(
            "Login error",
            exc_info=True
        )

        return jsonify({
            "error":
                "Login error: " + str(e)
        }), 500


    # ========================================================
    # CLOSE CURSOR
    # ========================================================

    finally:

        if cursor is not None:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route(
    "/logout",
    methods=["GET"]
)
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("auth_bp.login")
    )


# ============================================================
# GENERAL SIGNUP API
# ============================================================

@auth_bp.route(
    "/signup",
    methods=["POST"]
)
def signup():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        first_name = data.get(
            "first_name"
        )

        last_name = data.get(
            "last_name"
        )

        email = data.get(
            "email"
        )

        password = data.get(
            "password"
        )

        role = data.get(
            "role"
        )


        if not all([
            first_name,
            last_name,
            email,
            password,
            role
        ]):

            return jsonify({
                "error":
                    "All fields are required"
            }), 400


        if not valid_password(password):

            return jsonify({
                "error":
                    "Password must be at least 8 characters and include a number and special character"
            }), 400


        cursor = get_db_cursor()


        cursor.execute(
            """
            INSERT INTO users
            (
                first_name,
                last_name,
                email,
                password,
                role
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                email,
                password,
                role
            )
        )


        get_db().commit()

        cursor.close()


        return jsonify({
            "message":
                "User registered successfully"
        }), 201


    except sqlite3.IntegrityError:

        return jsonify({
            "error":
                "Email already registered"
        }), 400


    except Exception as e:

        current_app.logger.error(
            f"Signup error: {e}",
            exc_info=True
        )

        return jsonify({
            "error":
                "Signup failed: " + str(e)
        }), 500


# ============================================================
# CANDIDATE SIGNUP PAGE
# ============================================================

@auth_bp.route(
    "/candidate_signup",
    methods=["GET"],
    endpoint="candidate_signup_get"
)
def candidate_signup_get():

    return render_template(
        "candidate_signup.html"
    )


# ============================================================
# CANDIDATE SIGNUP
# ============================================================

@auth_bp.route(
    "/candidate/signup",
    methods=["GET", "POST"]
)
def candidate_signup():

    if request.method == "GET":

        return render_template(
            "candidate_signup.html"
        )


    try:

        first_name = (
            request.form.get("firstName")
            or ""
        ).strip()

        last_name = (
            request.form.get("lastName")
            or ""
        ).strip()

        email = (
            request.form.get("email")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or ""
        )

        confirm_password = (
            request.form.get(
                "confirmPassword"
            )
            or ""
        )


        if not all([
            first_name,
            last_name,
            email,
            password,
            confirm_password
        ]):

            return jsonify({
                "error":
                    "All fields are required"
            }), 400


        if password != confirm_password:

            return jsonify({
                "error":
                    "Passwords do not match"
            }), 400


        if not valid_password(password):

            return jsonify({
                "error":
                    "Password must be at least 8 characters and include a number and special character"
            }), 400


        query = text(
            """
            INSERT INTO candidates
            (
                first_name,
                last_name,
                email,
                password
            )
            VALUES
            (
                :first_name,
                :last_name,
                :email,
                :password
            )
            """
        )


        db.session.execute(
            query,
            {
                "first_name":
                    first_name,

                "last_name":
                    last_name,

                "email":
                    email,

                "password":
                    password
            }
        )


        db.session.commit()


        # ----------------------------------------------------
        # WELCOME EMAIL
        # ----------------------------------------------------

        try:

            msg = Message(
                subject=
                    "Welcome to InternshipHub 🎉",

                recipients=[
                    email
                ],

                body=f"""
Hello {first_name},

Thank you for signing up at InternshipHub!

You can now explore internships and apply for opportunities.

Good luck!

- InternshipHub Team
"""
            )

            mail.send(msg)

        except Exception as mail_error:

            print(
                "Welcome email failed:",
                mail_error
            )


        return jsonify({
            "message":
                "Candidate registered successfully"
        }), 201


    except Exception as e:

        db.session.rollback()

        print(
            "Candidate signup error:",
            repr(e)
        )

        return jsonify({
            "error":
                "Failed to register candidate: "
                + str(e)
        }), 500


# ============================================================
# COMPANY SIGNUP PAGE
# ============================================================

@auth_bp.route(
    "/company_signup",
    methods=["GET"],
    endpoint="company_signup_get"
)
def company_signup_get():

    return render_template(
        "company_signup.html"
    )


# ============================================================
# COMPANY SIGNUP
# ============================================================

@auth_bp.route(
    "/company/signup",
    methods=["GET", "POST"]
)
def company_signup():

    if request.method == "GET":

        return render_template(
            "company_signup.html"
        )


    try:

        company_name = (
            request.form.get(
                "companyName"
            )
            or ""
        ).strip()

        email = (
            request.form.get(
                "companyEmail"
            )
            or ""
        ).strip()

        password = (
            request.form.get(
                "password"
            )
            or ""
        )

        phone = (
            request.form.get(
                "contactNumber"
            )
            or ""
        ).strip()

        industry = (
            request.form.get(
                "industryType"
            )
            or ""
        ).strip()

        description = (
            request.form.get(
                "companyDescription"
            )
            or ""
        ).strip()

        logo_file = request.files.get(
            "companyLogo"
        )


        # ----------------------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------------------

        missing_fields = []


        if not company_name:
            missing_fields.append(
                "companyName"
            )

        if not email:
            missing_fields.append(
                "companyEmail"
            )

        if not password:
            missing_fields.append(
                "password"
            )

        if not phone:
            missing_fields.append(
                "contactNumber"
            )

        if not industry:
            missing_fields.append(
                "industryType"
            )

        if not logo_file:
            missing_fields.append(
                "companyLogo"
            )


        if missing_fields:

            return jsonify({
                "error":
                    "Missing required fields: "
                    + ", ".join(
                        missing_fields
                    )
            }), 400


        if not valid_password(password):

            return jsonify({
                "error":
                    "Password must be at least 8 characters and include a number and special character"
            }), 400


        # ----------------------------------------------------
        # LOGO
        # ----------------------------------------------------

        filename = secure_filename(
            logo_file.filename
        )


        if not filename:

            return jsonify({
                "error":
                    "Invalid logo file"
            }), 400


        upload_folder = (
            current_app.config[
                "UPLOAD_FOLDER"
            ]
        )


        os.makedirs(
            upload_folder,
            exist_ok=True
        )


        logo_file.save(
            os.path.join(
                upload_folder,
                filename
            )
        )


        # ----------------------------------------------------
        # INSERT COMPANY
        # ----------------------------------------------------

        query = text(
            """
            INSERT INTO companies
            (
                company_name,
                contact_email,
                password,
                contact_number,
                industry_type,
                logo_filename,
                company_description
            )
            VALUES
            (
                :company_name,
                :contact_email,
                :password,
                :contact_number,
                :industry_type,
                :logo_filename,
                :company_description
            )
            """
        )


        db.session.execute(
            query,
            {
                "company_name":
                    company_name,

                "contact_email":
                    email,

                "password":
                    password,

                "contact_number":
                    phone,

                "industry_type":
                    industry,

                "logo_filename":
                    filename,

                "company_description":
                    description
            }
        )


        db.session.commit()


        # ----------------------------------------------------
        # WELCOME EMAIL
        # ----------------------------------------------------

        try:

            msg = Message(
                subject=
                    "Welcome to InternshipHub 🎉",

                recipients=[
                    email
                ],

                body=f"""
Hello {company_name},

Thank you for signing up at InternshipHub!

You can now post internship opportunities and connect with talented students.

Good luck!

- InternshipHub Team
"""
            )

            mail.send(msg)

        except Exception as mail_error:

            print(
                "Company welcome email failed:",
                mail_error
            )


        return jsonify({
            "message":
                "Company registered successfully"
        }), 201


    except sqlite3.IntegrityError:

        db.session.rollback()

        return jsonify({
            "error":
                "Email already registered"
        }), 400


    except Exception as e:

        db.session.rollback()

        print(
            "Company signup error:",
            repr(e)
        )

        return jsonify({
            "error":
                "Failed to register company: "
                + str(e)
        }), 500


# ============================================================
# UPDATE STUDENT PASSWORD
# ============================================================

@auth_bp.route(
    "/update_password",
    methods=["POST"]
)
def update_password():

    if "email" not in session:

        return jsonify({
            "error":
                "Unauthorized. Please log in again."
        }), 401


    email = session["email"]

    current_password = (
        request.form.get(
            "current_password"
        )
    )

    new_password = (
        request.form.get(
            "new_password"
        )
    )

    confirm_password = (
        request.form.get(
            "confirm_password"
        )
    )


    if not all([
        current_password,
        new_password,
        confirm_password
    ]):

        return jsonify({
            "error":
                "All fields are required"
        }), 400


    if new_password != confirm_password:

        return jsonify({
            "error":
                "New password and confirm password do not match"
        }), 400


    if not valid_password(new_password):

        return jsonify({
            "error":
                "New password must be at least 8 characters and include a number and special character"
        }), 400


    try:

        cursor = get_db_cursor()


        cursor.execute(
            """
            SELECT password
            FROM candidates
            WHERE email = ?
            """,
            (email,)
        )


        row = cursor.fetchone()


        if not row:

            return jsonify({
                "error":
                    "User not found"
            }), 404


        if row["password"] != current_password:

            return jsonify({
                "error":
                    "Current password is incorrect"
            }), 400


        cursor.execute(
            """
            UPDATE candidates
            SET password = ?
            WHERE email = ?
            """,
            (
                new_password,
                email
            )
        )


        get_db().commit()


        return jsonify({
            "message":
                "Password updated successfully"
        }), 200


    except Exception as e:

        current_app.logger.error(
            f"Password update error: {e}",
            exc_info=True
        )

        return jsonify({
            "error":
                "Password update failed"
        }), 500


# ============================================================
# UPDATE COMPANY PASSWORD
# ============================================================

@auth_bp.route(
    "/update_password_company",
    methods=["POST"]
)
def update_password_company():

    if "email" not in session:

        return jsonify({
            "error":
                "Unauthorized. Please log in again."
        }), 401


    email = session["email"]

    current_password = (
        request.form.get(
            "current_password"
        )
    )

    new_password = (
        request.form.get(
            "new_password"
        )
    )

    confirm_password = (
        request.form.get(
            "confirm_password"
        )
    )


    if not all([
        current_password,
        new_password,
        confirm_password
    ]):

        return jsonify({
            "error":
                "All fields are required"
        }), 400


    if new_password != confirm_password:

        return jsonify({
            "error":
                "New password and confirm password do not match"
        }), 400


    if not valid_password(new_password):

        return jsonify({
            "error":
                "New password must be at least 8 characters and include a number and special character"
        }), 400


    try:

        cursor = get_db_cursor()


        cursor.execute(
            """
            SELECT password
            FROM companies
            WHERE contact_email = ?
            """,
            (email,)
        )


        row = cursor.fetchone()


        if not row:

            return jsonify({
                "error":
                    "Company not found"
            }), 404


        if row["password"] != current_password:

            return jsonify({
                "error":
                    "Current password is incorrect"
            }), 400


        cursor.execute(
            """
            UPDATE companies
            SET password = ?
            WHERE contact_email = ?
            """,
            (
                new_password,
                email
            )
        )


        get_db().commit()


        return jsonify({
            "message":
                "Password updated successfully"
        }), 200


    except Exception as e:

        current_app.logger.error(
            f"Company password update error: {e}",
            exc_info=True
        )

        return jsonify({
            "error":
                "Password update failed"
        }), 500