# ============================================================
# FINANCEFLOW
# AI PERSONAL FINANCE MANAGEMENT SYSTEM
# BACKEND - FLASK + MYSQL + RANDOM FOREST
# ============================================================

from flask import Flask, request, jsonify, session, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

import pymysql
import pandas as pd
import numpy as np
import joblib

from datetime import datetime, date, timedelta
from calendar import monthrange
from pathlib import Path
from dotenv import load_dotenv
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "financeflow-secret-key-change-this"
)

CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ]
)


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "random_forest_expense_model.pkl"
)

FEATURES_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "model_features.pkl"
)

MODEL_METADATA_PATH = (
    BASE_DIR
    / "ml"
    / "models"
    / "model_metadata.pkl"
)


# ============================================================
# MYSQL CONFIGURATION
# ============================================================

DB_HOST = os.getenv(
    "MYSQL_HOST",
    "localhost"
)

DB_USER = os.getenv(
    "MYSQL_USER",
    "root"
)

DB_PASSWORD = os.getenv(
    "MYSQL_PASSWORD",
    ""
)

DB_NAME = os.getenv(
    "MYSQL_DATABASE",
    "financeflow"
)

DB_PORT = int(
    os.getenv(
        "MYSQL_PORT",
        "3306"
    )
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


# ============================================================
# MODEL LOADING
# ============================================================

model = None
model_features = None
model_metadata = None


def load_ml_model():

    global model
    global model_features
    global model_metadata

    try:

        if MODEL_PATH.exists():

            model = joblib.load(
                MODEL_PATH
            )

            print(
                "Random Forest model loaded successfully."
            )

        else:

            print(
                f"Model file not found: {MODEL_PATH}"
            )

    except Exception as error:

        model = None

        print(
            "Model loading error:",
            error
        )


    try:

        if FEATURES_PATH.exists():

            model_features = joblib.load(
                FEATURES_PATH
            )

            print(
                "Model features loaded successfully."
            )

    except Exception as error:

        model_features = None

        print(
            "Model features loading error:",
            error
        )


    try:

        if MODEL_METADATA_PATH.exists():

            model_metadata = joblib.load(
                MODEL_METADATA_PATH
            )

    except Exception as error:

        model_metadata = None

        print(
            "Model metadata loading error:",
            error
        )


load_ml_model()


# ============================================================
# AUTH HELPER
# ============================================================

def get_current_user_id():

    return session.get(
        "user_id"
    )


def login_required():

    user_id = get_current_user_id()

    if not user_id:
        return None

    return int(user_id)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "FinanceFlow API is running",
        "status": "success"
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Report API and MySQL readiness without exposing connection details."""
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ready")
                cursor.fetchone()
        finally:
            connection.close()
        return jsonify({"status": "ok", "api": "running", "database": "connected"})
    except Exception:
        app.logger.exception("FinanceFlow health check could not connect to MySQL")
        return jsonify({
            "status": "degraded",
            "api": "running",
            "database": "disconnected",
            "message": "Check that MySQL is running and the MYSQL_* values in your existing .env file are correct."
        }), 503


# ============================================================
# MODEL INFORMATION
# ============================================================

@app.route("/model-info", methods=["GET"])
def model_info():

    return jsonify({

        "model_loaded":
            model is not None,

        "model_type":
            type(model).__name__
            if model is not None
            else None,

        "features":
            model_features,

        "metadata":
            model_metadata

    })


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["POST"])
def register():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error": "Invalid request data."
            }), 400

        name = str(
            data.get("name", "")
        ).strip()

        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        )

        if not name or not email or not password:

            return jsonify({
                "error":
                    "Name, email and password are required."
            }), 400

        if len(password) < 6:

            return jsonify({
                "error":
                    "Password must contain at least 6 characters."
            }), 400

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = %s
                    """,
                    (email,)
                )

                existing_user = cursor.fetchone()

                if existing_user:

                    return jsonify({
                        "error":
                            "An account with this email already exists."
                    }), 409

                # ------------------------------------------------
                # PASSWORD IS STORED IN password_hash COLUMN
                # ------------------------------------------------

                password_hash = generate_password_hash(
                    password
                )

                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        name,
                        email,
                        password_hash
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        name,
                        email,
                        password_hash
                    )
                )

            return jsonify({
                "message":
                    "Registration successful."
            }), 201

        finally:

            connection.close()

    except Exception as error:

        print(
            "Register error:",
            error
        )

        return jsonify({
            "error":
                "Registration failed.",
            "details":
                str(error)
        }), 500


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["POST"])
def login():
    """Log in with the registered name (username) or email address."""
    try:
        data = request.get_json(silent=True) or {}
        identifier = str(data.get("identifier", data.get("email", data.get("username", "")))).strip()
        password = str(data.get("password", ""))

        if not identifier or not password:
            return jsonify({"error": "Enter your username or email and password."}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, email, password_hash
                    FROM users
                    WHERE email = %s OR name = %s
                    ORDER BY CASE WHEN email = %s THEN 0 ELSE 1 END
                    """,
                    (identifier.lower(), identifier, identifier.lower())
                )
                candidates = cursor.fetchall()
        finally:
            connection.close()

        # Name is the project's existing display-name field. If names are not unique,
        # the password hash still determines which matching account can authenticate.
        user = next(
            (candidate for candidate in candidates
             if candidate.get("password_hash") and check_password_hash(candidate["password_hash"], password)),
            None
        )
        if not user:
            return jsonify({"error": "Invalid username/email or password."}), 401

        session.clear()
        session["user_id"] = int(user["id"])
        return jsonify({
            "message": "Login successful.",
            "user": {"id": user["id"], "name": user["name"], "email": user["email"]}
        })
    except Exception as error:
        app.logger.exception("Login error")
        return jsonify({"error": "Login failed. Check that MySQL is running and your .env settings are correct."}), 500


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "message":
            "Logged out successfully."
    })


# ============================================================
# CURRENT USER
# ============================================================

@app.route("/me", methods=["GET"])
def me():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Not logged in."
        }), 401

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        name,
                        email
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                user = cursor.fetchone()

        finally:

            connection.close()

        if not user:

            session.clear()

            return jsonify({
                "error":
                    "User not found."
            }), 404

        return jsonify({
            "user": user
        })

    except Exception as error:

        print(
            "Profile error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load profile."
        }), 500


# ============================================================
# ADD TRANSACTION
# ============================================================

@app.route("/transactions", methods=["POST"])
def add_transaction():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "error":
                    "Invalid transaction data."
            }), 400

        date = str(
            data.get("date", "")
        ).strip()

        amount = data.get(
            "amount"
        )

        category = str(
            data.get("category", "")
        ).strip()

        description = str(
            data.get("description", "")
        ).strip()

        transaction_type = str(
            data.get("type", "")
        ).strip()

        if not date:

            return jsonify({
                "error":
                    "Date is required."
            }), 400

        if amount is None:

            return jsonify({
                "error":
                    "Amount is required."
            }), 400

        if not category:

            return jsonify({
                "error":
                    "Category is required."
            }), 400

        if transaction_type not in [
            "Income",
            "Expense"
        ]:

            return jsonify({
                "error":
                    "Type must be Income or Expense."
            }), 400

        try:

            amount = float(amount)

        except:

            return jsonify({
                "error":
                    "Amount must be a valid number."
            }), 400

        if amount <= 0:

            return jsonify({
                "error":
                    "Amount must be greater than zero."
            }), 400

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO transactions
                    (
                        user_id,
                        Date,
                        Type,
                        Amount,
                        Category,
                        Description
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user_id,
                        date,
                        transaction_type,
                        amount,
                        category,
                        description
                    )
                )

                transaction_id = cursor.lastrowid

        finally:

            connection.close()

        return jsonify({

            "message":
                "Transaction added successfully.",

            "transaction_id":
                transaction_id

        }), 201

    except Exception as error:

        print(
            "Add transaction error:",
            error
        )

        return jsonify({
            "error":
                "Unable to add transaction."
        }), 500


# ============================================================
# GET TRANSACTIONS
# ============================================================

@app.route("/transactions", methods=["GET"])
def get_transactions():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        Date,
                        Type,
                        Amount,
                        Category,
                        Description
                    FROM transactions
                    WHERE user_id = %s
                    ORDER BY Date DESC, id DESC
                    """,
                    (user_id,)
                )

                transactions = cursor.fetchall()

        finally:

            connection.close()

        for transaction in transactions:

            if transaction.get("Date"):

                transaction["Date"] = (
                    transaction["Date"].strftime(
                        "%Y-%m-%d"
                    )
                    if hasattr(
                        transaction["Date"],
                        "strftime"
                    )
                    else str(
                        transaction["Date"]
                    )
                )

            transaction["Amount"] = float(
                transaction.get(
                    "Amount",
                    0
                )
            )

        return jsonify({
            "transactions":
                transactions
        })

    except Exception as error:

        print(
            "Transactions error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load transactions."
        }), 500




# ============================================================
# UPDATE TRANSACTION (ONLY THE LOGGED-IN USER'S OWN RECORD)
# ============================================================

@app.route("/transactions/<int:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401

    data = request.get_json(silent=True) or {}
    transaction_date = str(data.get("date", "")).strip()
    transaction_type = str(data.get("type", "")).strip()
    category = str(data.get("category", "")).strip()
    description = str(data.get("description", "")).strip()

    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a valid number."}), 400

    if not transaction_date or not category or transaction_type not in ("Income", "Expense") or amount <= 0:
        return jsonify({"error": "Enter a valid date, type, category and positive amount."}), 400
    try:
        datetime.strptime(transaction_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE transactions
                SET Date=%s, Type=%s, Amount=%s, Category=%s, Description=%s
                WHERE id=%s AND user_id=%s
                """,
                (transaction_date, transaction_type, amount, category, description, transaction_id, user_id)
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT id FROM transactions WHERE id=%s AND user_id=%s",
                    (transaction_id, user_id)
                )
                if not cursor.fetchone():
                    return jsonify({"error": "Transaction not found."}), 404
        return jsonify({"message": "Transaction updated successfully."})
    except Exception as error:
        print("Update transaction error:", error)
        return jsonify({"error": "Unable to update transaction."}), 500
    finally:
        if connection:
            connection.close()


# ============================================================
# DELETE TRANSACTION (ONLY THE LOGGED-IN USER'S OWN RECORD)
# ============================================================

@app.route("/transactions/<int:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM transactions WHERE id=%s AND user_id=%s",
                (transaction_id, user_id)
            )
            if cursor.rowcount == 0:
                return jsonify({"error": "Transaction not found."}), 404
        return jsonify({"message": "Transaction deleted successfully."})
    except Exception as error:
        print("Delete transaction error:", error)
        return jsonify({"error": "Unable to delete transaction."}), 500
    finally:
        if connection:
            connection.close()


# ============================================================
# DOWNLOAD DAY-WISE FINANCIAL REPORT AS PDF
# ============================================================

@app.route("/reports/financial.pdf", methods=["GET"])
def download_financial_report():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401

    end_text = request.args.get("end_date", date.today().isoformat())
    start_text = request.args.get("start_date", (date.today() - timedelta(days=29)).isoformat())
    try:
        start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
        if start_date > end_date:
            return jsonify({"error": "Start date must be on or before end date."}), 400
        if (end_date - start_date).days > 3660:
            return jsonify({"error": "Please choose a report period of 10 years or less."}), 400
    except ValueError:
        return jsonify({"error": "Dates must use YYYY-MM-DD format."}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT Date, Type, Amount, Category, Description, id
                FROM transactions
                WHERE user_id=%s AND Date >= %s AND Date <= %s
                ORDER BY Date ASC, id ASC
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            )
            transactions = cursor.fetchall()
    except Exception as error:
        print("Financial report query error:", error)
        return jsonify({"error": "Unable to build financial report."}), 500
    finally:
        if connection:
            connection.close()

    income = sum(float(t.get("Amount") or 0) for t in transactions if t.get("Type") == "Income")
    expenses = sum(float(t.get("Amount") or 0) for t in transactions if t.get("Type") == "Expense")
    count = len(transactions)
    category_totals = {}
    daily_totals = {}
    for t in transactions:
        day_value = t.get("Date")
        day_key = day_value.isoformat() if hasattr(day_value, "isoformat") else str(day_value)[:10]
        amount = float(t.get("Amount") or 0)
        if t.get("Type") == "Expense":
            category = str(t.get("Category") or "Uncategorized")
            category_totals[category] = category_totals.get(category, 0) + amount
            daily_totals[day_key] = daily_totals.get(day_key, 0) + amount

    day_count = (end_date - start_date).days + 1
    no_expense_days = day_count - sum(1 for value in daily_totals.values() if value > 0)
    average_daily_expense = expenses / day_count if day_count else 0
    highest_day = max(daily_totals.items(), key=lambda item: item[1]) if daily_totals else None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
        topMargin=15*mm, bottomMargin=15*mm, title="FinanceFlow Financial Report"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportSub", parent=styles["Normal"], textColor=colors.HexColor("#526174"), fontSize=9, leading=13))
    story = [
        Paragraph("FinanceFlow — Financial Report", styles["Title"]),
        Paragraph(f"Report period: {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}", styles["ReportSub"]),
        Spacer(1, 7*mm),
    ]

    summary_rows = [
        ["Total Income", "Total Expenses", "Net Balance", "Transactions"],
        [f"Rs. {income:,.2f}", f"Rs. {expenses:,.2f}", f"Rs. {income-expenses:,.2f}", str(count)]
    ]
    summary_table = Table(summary_rows, colWidths=[42*mm, 42*mm, 42*mm, 36*mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#172B4D")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#F0F4F8")),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#D7DEE8")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    monthly_totals = {}
    for transaction in transactions:
        transaction_date_value = transaction.get("Date")
        transaction_key = transaction_date_value.isoformat() if hasattr(transaction_date_value, "isoformat") else str(transaction_date_value)[:10]
        month_key = transaction_key[:7]
        monthly_totals.setdefault(month_key, {"income": 0.0, "expense": 0.0})
        amount_value = float(transaction.get("Amount") or 0)
        if transaction.get("Type") == "Income":
            monthly_totals[month_key]["income"] += amount_value
        elif transaction.get("Type") == "Expense":
            monthly_totals[month_key]["expense"] += amount_value

    story += [summary_table, Spacer(1, 7*mm), Paragraph("Monthly Summary", styles["Heading2"])]
    monthly_rows = [["Month", "Income (Rs.)", "Expenses (Rs.)", "Net (Rs.)"]]
    for month_key, values in sorted(monthly_totals.items()):
        monthly_rows.append([
            datetime.strptime(month_key, "%Y-%m").strftime("%b %Y"),
            f"{values['income']:,.2f}",
            f"{values['expense']:,.2f}",
            f"{values['income'] - values['expense']:,.2f}"
        ])
    if not monthly_totals:
        monthly_rows.append(["No transactions", "0.00", "0.00", "0.00"])
    monthly_table = Table(monthly_rows, repeatRows=1, colWidths=[35*mm, 45*mm, 45*mm, 45*mm])
    monthly_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCE7F5")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D7DEE8")),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(monthly_table)
    if monthly_totals and any(values["expense"] > 0 for values in monthly_totals.values()):
        chart_width, chart_height = 165*mm, 65*mm
        drawing = Drawing(chart_width, chart_height)
        chart = VerticalBarChart()
        chart.x = 18*mm
        chart.y = 12*mm
        chart.width = chart_width - 28*mm
        chart.height = chart_height - 22*mm
        ordered_months = sorted(monthly_totals)
        chart.data = [tuple(monthly_totals[key]["expense"] for key in ordered_months)]
        chart.categoryAxis.categoryNames = [
            datetime.strptime(key, "%Y-%m").strftime("%b %y")
            for key in ordered_months
        ]
        chart.categoryAxis.labels.angle = 25
        chart.categoryAxis.labels.fontSize = 6
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 6
        chart.bars[0].fillColor = colors.HexColor("#426A9A")
        chart.barWidth = min(12, chart.width / max(len(ordered_months) * 1.8, 1))
        chart.groupSpacing = 4
        drawing.add(chart)
        story += [Spacer(1, 3*mm), Paragraph("Monthly Expense Chart", styles["Heading3"]), drawing]
    story += [Spacer(1, 7*mm), Paragraph("Day-wise Expense Report", styles["Heading2"])]
    story.append(Paragraph(
        f"Average daily expense: Rs. {average_daily_expense:,.2f} · "
        f"Days with no recorded expenses: {no_expense_days} of {day_count}",
        styles["ReportSub"]
    ))
    daily_rows = [["Date", "Day", "Expense (Rs.)"]]
    day = start_date
    while day <= end_date:
        key = day.isoformat()
        daily_rows.append([day.strftime("%d %b %Y"), day.strftime("%A"), f"{daily_totals.get(key, 0):,.2f}"])
        day += timedelta(days=1)
    daily_table = Table(daily_rows, repeatRows=1, colWidths=[45*mm, 55*mm, 55*mm])
    daily_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCE7F5")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D7DEE8")),
        ("ALIGN", (2,1), (2,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [daily_table, Spacer(1, 6*mm), Paragraph("Category-wise Expenses", styles["Heading2"])]
    category_rows = [["Category", "Total Expense (Rs.)", "Share"]]
    for category, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        share = (total / expenses * 100) if expenses else 0
        category_rows.append([category, f"{total:,.2f}", f"{share:.1f}%"])
    if not category_totals:
        category_rows.append(["No recorded expenses", "0.00", "0.0%"])
    category_table = Table(category_rows, repeatRows=1, colWidths=[70*mm, 50*mm, 35*mm])
    category_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DCE7F5")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D7DEE8")),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(category_table)
    story += [Spacer(1, 6*mm), Paragraph("Transaction Details", styles["Heading2"])]
    detail_rows = [["Date", "Type", "Category", "Description", "Amount (Rs.)"]]
    for t in transactions:
        day_value = t.get("Date")
        date_label = day_value.strftime("%d %b %Y") if hasattr(day_value, "strftime") else str(day_value)[:10]
        detail_rows.append([
            date_label, str(t.get("Type") or ""),
            str(t.get("Category") or "")[:24],
            str(t.get("Description") or "")[:34],
            f"{float(t.get('Amount') or 0):,.2f}"
        ])
    if not transactions:
        detail_rows.append(["—", "—", "No transactions", "in selected period", "0.00"])
    detail_table = Table(detail_rows, repeatRows=1, colWidths=[28*mm, 22*mm, 35*mm, 65*mm, 25*mm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#172B4D")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6.5),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D7DEE8")),
        ("ALIGN", (4,1), (4,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(detail_table)
    story += [Spacer(1, 5*mm), Paragraph(
        "Note: A day with no recorded expense means no expense transaction was recorded in FinanceFlow for that date; it does not confirm that no spending occurred.",
        styles["ReportSub"]
    )]
    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="FinanceFlow_Report_{start_text}_to_{end_text}.pdf"'
    return response


# ============================================================
# CSV IMPORT
# ============================================================

@app.route(
    "/transactions/import-csv",
    methods=["POST"]
)
def import_csv():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    if "file" not in request.files:

        return jsonify({
            "error":
                "No CSV file uploaded."
        }), 400

    file = request.files["file"]

    if not file.filename:

        return jsonify({
            "error":
                "Please select a CSV file."
        }), 400

    try:

        dataframe = pd.read_csv(file)

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        column_map = {}

        for column in dataframe.columns:

            normalized = (
                column
                .lower()
                .replace("_", "")
                .replace(" ", "")
            )

            column_map[normalized] = column

        def find_column(*names):

            for name in names:

                normalized = (
                    name
                    .lower()
                    .replace("_", "")
                    .replace(" ", "")
                )

                if normalized in column_map:

                    return column_map[
                        normalized
                    ]

            return None

        date_column = find_column(
            "date"
        )

        type_column = find_column(
            "type"
        )

        amount_column = find_column(
            "amount"
        )

        category_column = find_column(
            "category"
        )

        description_column = find_column(
            "description",
            "desc"
        )

        required_columns = [
            date_column,
            type_column,
            amount_column,
            category_column
        ]

        if any(
            column is None
            for column in required_columns
        ):

            return jsonify({
                "error":
                    "CSV must contain Date, Type, Amount and Category columns."
            }), 400

        inserted_count = 0
        skipped_rows = 0

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                for _, row in dataframe.iterrows():

                    try:

                        raw_date = row[
                            date_column
                        ]

                        parsed_date = pd.to_datetime(
                            raw_date,
                            errors="coerce"
                        )

                        if pd.isna(parsed_date):

                            skipped_rows += 1
                            continue

                        date_value = (
                            parsed_date.strftime(
                                "%Y-%m-%d"
                            )
                        )

                        transaction_type = str(
                            row[type_column]
                        ).strip()

                        if transaction_type not in [
                            "Income",
                            "Expense"
                        ]:

                            skipped_rows += 1
                            continue

                        amount = float(
                            row[amount_column]
                        )

                        if amount <= 0:

                            skipped_rows += 1
                            continue

                        category = str(
                            row[category_column]
                        ).strip()

                        if not category:

                            skipped_rows += 1
                            continue

                        description = ""

                        if description_column:

                            description = str(
                                row[
                                    description_column
                                ]
                            ).strip()

                            if description == "nan":

                                description = ""

                        cursor.execute(
                            """
                            INSERT INTO transactions
                            (
                                user_id,
                                Date,
                                Type,
                                Amount,
                                Category,
                                Description
                            )
                            VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                            """,
                            (
                                user_id,
                                date_value,
                                transaction_type,
                                amount,
                                category,
                                description
                            )
                        )

                        inserted_count += 1

                    except Exception as row_error:

                        print(
                            "Skipped CSV row:",
                            row_error
                        )

                        skipped_rows += 1

        finally:

            connection.close()

        return jsonify({

            "message":
                "CSV import completed.",

            "inserted_count":
                inserted_count,

            "skipped_rows":
                skipped_rows

        })

    except Exception as error:

        print(
            "CSV import error:",
            error
        )

        return jsonify({
            "error":
                "Unable to import CSV file."
        }), 500


# ============================================================
# SUMMARY
# ============================================================

@app.route("/summary", methods=["GET"])
def summary():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Income'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS total_income,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Expense'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS total_expense,

                        COUNT(*) AS transaction_count

                    FROM transactions

                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

                result = cursor.fetchone()

        finally:

            connection.close()

        total_income = float(
            result["total_income"] or 0
        )

        total_expense = float(
            result["total_expense"] or 0
        )

        balance = (
            total_income -
            total_expense
        )

        return jsonify({

            "balance":
                balance,

            "total_income":
                total_income,

            "total_expense":
                total_expense,

            "transaction_count":
                int(
                    result["transaction_count"] or 0
                )

        })

    except Exception as error:

        print(
            "Summary error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load summary."
        }), 500


# ============================================================
# MONTHLY ANALYTICS
# ============================================================

@app.route(
    "/analytics/monthly",
    methods=["GET"]
)
def analytics_monthly():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT

                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m'
                        ) AS month,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Expense'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS expense,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Income'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS income

                    FROM transactions

                    WHERE user_id = %s

                    GROUP BY
                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m'
                        )

                    ORDER BY
                        month ASC
                    """,
                    (user_id,)
                )

                rows = cursor.fetchall()

        finally:

            connection.close()

        monthly_data = []

        for row in rows:

            monthly_data.append({

                "month":
                    row["month"],

                "expense":
                    float(
                        row["expense"] or 0
                    ),

                "income":
                    float(
                        row["income"] or 0
                    )

            })

        return jsonify({
            "monthly_data":
                monthly_data
        })

    except Exception as error:

        print(
            "Monthly analytics error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load monthly analytics."
        }), 500


# ============================================================
# MONTH-OVER-MONTH SPENDING COMPARISON
# ============================================================

@app.route("/analytics/monthly-comparison", methods=["GET"])
def analytics_monthly_comparison():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401

    month_value = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        current_start = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
    except ValueError:
        return jsonify({"error": "Month must use YYYY-MM format."}), 400

    previous_start = (current_start - timedelta(days=1)).replace(day=1)
    if current_start.month == 12:
        next_start = date(current_start.year + 1, 1, 1)
    else:
        next_start = date(current_start.year, current_start.month + 1, 1)

    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT Category AS category,
                           DATE_FORMAT(Date, '%%Y-%%m') AS month,
                           COALESCE(SUM(Amount), 0) AS total
                    FROM transactions
                    WHERE user_id = %s
                      AND Type = 'Expense'
                      AND Date >= %s
                      AND Date < %s
                    GROUP BY Category, DATE_FORMAT(Date, '%%Y-%%m')
                    ORDER BY Category
                    """,
                    (user_id, previous_start, next_start)
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        totals = {}
        for row in rows:
            category = str(row.get("category") or "Other")
            totals.setdefault(category, {"current": 0.0, "previous": 0.0})
            amount = float(row.get("total") or 0)
            if str(row.get("month")) == current_start.strftime("%Y-%m"):
                totals[category]["current"] += amount
            elif str(row.get("month")) == previous_start.strftime("%Y-%m"):
                totals[category]["previous"] += amount

        categories = []
        for category, values in totals.items():
            current = round(values["current"], 2)
            previous = round(values["previous"], 2)
            change = round(current - previous, 2)
            percentage = round((change / previous) * 100, 1) if previous else (0.0 if current == 0 else None)
            categories.append({
                "category": category,
                "current_expense": current,
                "previous_expense": previous,
                "change_amount": change,
                "percentage_change": percentage,
                "status": "increase" if change > 0 else "decrease" if change < 0 else "same"
            })

        categories.sort(key=lambda item: abs(item["change_amount"]), reverse=True)
        current_total = round(sum(item["current_expense"] for item in categories), 2)
        previous_total = round(sum(item["previous_expense"] for item in categories), 2)
        total_change = round(current_total - previous_total, 2)
        total_percentage = round(total_change / previous_total * 100, 1) if previous_total else (0.0 if current_total == 0 else None)
        return jsonify({
            "month": current_start.strftime("%Y-%m"),
            "previous_month": previous_start.strftime("%Y-%m"),
            "current_total": current_total,
            "previous_total": previous_total,
            "change_amount": total_change,
            "percentage_change": total_percentage,
            "categories": categories,
            "biggest_increase": next((item for item in sorted(categories, key=lambda x: x["change_amount"], reverse=True) if item["change_amount"] > 0), None),
            "biggest_decrease": next((item for item in sorted(categories, key=lambda x: x["change_amount"]) if item["change_amount"] < 0), None)
        })
    except Exception:
        app.logger.exception("Monthly comparison error")
        return jsonify({"error": "Unable to load month-over-month spending comparison."}), 500


# ============================================================
# YEARLY ANALYTICS
# ============================================================

@app.route(
    "/analytics/yearly",
    methods=["GET"]
)
def analytics_yearly():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT

                        YEAR(Date) AS year,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Expense'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS expense,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Income'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS income

                    FROM transactions

                    WHERE user_id = %s

                    GROUP BY
                        YEAR(Date)

                    ORDER BY
                        year ASC
                    """,
                    (user_id,)
                )

                rows = cursor.fetchall()

        finally:

            connection.close()

        yearly_data = []

        for row in rows:

            yearly_data.append({

                "year":
                    int(row["year"]),

                "expense":
                    float(
                        row["expense"] or 0
                    ),

                "income":
                    float(
                        row["income"] or 0
                    )

            })

        return jsonify({
            "yearly_data":
                yearly_data
        })

    except Exception as error:

        print(
            "Yearly analytics error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load yearly analytics."
        }), 500


# ============================================================
# CATEGORY ANALYTICS
# ============================================================

@app.route(
    "/analytics/category",
    methods=["GET"]
)
def analytics_category():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    month = request.args.get(
        "month"
    )

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                if month:

                    cursor.execute(
                        """
                        SELECT

                            Category AS category,

                            COALESCE(
                                SUM(Amount),
                                0
                            ) AS total_expense

                        FROM transactions

                        WHERE
                            user_id = %s
                            AND Type = 'Expense'
                            AND DATE_FORMAT(
                                Date,
                                '%%Y-%%m'
                            ) = %s

                        GROUP BY
                            Category

                        ORDER BY
                            total_expense DESC
                        """,
                        (
                            user_id,
                            month
                        )
                    )

                else:

                    cursor.execute(
                        """
                        SELECT

                            Category AS category,

                            COALESCE(
                                SUM(Amount),
                                0
                            ) AS total_expense

                        FROM transactions

                        WHERE
                            user_id = %s
                            AND Type = 'Expense'

                        GROUP BY
                            Category

                        ORDER BY
                            total_expense DESC
                        """,
                        (user_id,)
                    )

                rows = cursor.fetchall()

        finally:

            connection.close()

        category_data = []

        for row in rows:

            category_data.append({

                "category":
                    row["category"],

                "total_expense":
                    float(
                        row["total_expense"] or 0
                    )

            })

        return jsonify({
            "category_data":
                category_data
        })

    except Exception as error:

        print(
            "Category analytics error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load category analytics."
        }), 500


# ============================================================
# DAILY ANALYTICS
# ============================================================

@app.route(
    "/analytics/daily",
    methods=["GET"]
)
def analytics_daily():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    month = request.args.get(
        "month"
    )

    if not month:

        return jsonify({
            "error":
                "Month is required. Use YYYY-MM."
        }), 400

    try:

        try:

            year, month_number = map(
                int,
                month.split("-")
            )

            if (
                month_number < 1
                or month_number > 12
            ):

                raise ValueError

        except:

            return jsonify({
                "error":
                    "Invalid month format. Use YYYY-MM."
            }), 400

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT

                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m-%%d'
                        ) AS day,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Expense'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS expense,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Income'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS income

                    FROM transactions

                    WHERE
                        user_id = %s
                        AND DATE_FORMAT(
                            Date,
                            '%%Y-%%m'
                        ) = %s

                    GROUP BY
                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m-%%d'
                        )

                    ORDER BY
                        day ASC
                    """,
                    (
                        user_id,
                        month
                    )
                )

                rows = cursor.fetchall()

        finally:

            connection.close()

        lookup = {}

        for row in rows:

            lookup[
                str(row["day"])
            ] = {

                "expense":
                    float(
                        row["expense"] or 0
                    ),

                "income":
                    float(
                        row["income"] or 0
                    )
            }

        days_in_month = monthrange(
            year,
            month_number
        )[1]

        daily_data = []

        for day_number in range(
            1,
            days_in_month + 1
        ):

            day_key = (
                f"{year:04d}-"
                f"{month_number:02d}-"
                f"{day_number:02d}"
            )

            row = lookup.get(
                day_key
            )

            daily_data.append({

                "day":
                    day_key,

                "expense":
                    (
                        row["expense"]
                        if row
                        else 0
                    ),

                "income":
                    (
                        row["income"]
                        if row
                        else 0
                    )

            })

        return jsonify({
            "daily_data":
                daily_data
        })

    except Exception as error:

        print(
            "Daily analytics error:",
            error
        )

        return jsonify({
            "error":
                "Unable to load daily analytics."
        }), 500


# ============================================================
# ANOMALY DETECTION
# ============================================================

@app.route(
    "/analytics/anomalies",
    methods=["GET"]
)
def analytics_anomalies():
    """Detect unusual expenses using only the authenticated user's history."""
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401

    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, Date, Type, Amount, Category, Description
                    FROM transactions
                    WHERE user_id = %s AND Type = 'Expense'
                    ORDER BY Date DESC, id DESC
                    """,
                    (user_id,)
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        if not rows:
            return jsonify({"anomalies": [], "methods": [
                "personal spending pattern", "unusual frequency", "ML anomaly detection"
            ]})

        amounts = np.array([max(0.0, float(r.get("Amount") or 0)) for r in rows], dtype=float)
        median = float(np.median(amounts))
        mad = float(np.median(np.abs(amounts - median)))
        # Median/MAD is less sensitive to a few very large purchases than mean/std.
        personal_cutoff = median + (3.5 * 1.4826 * mad) if mad > 0 else median * 2.5
        if len(amounts) < 4:
            personal_cutoff = max(personal_cutoff, float(np.max(amounts)) * 1.01)

        category_amounts = {}
        category_frequency = {}
        for r in rows:
            cat = str(r.get("Category") or "Other")
            amt = max(0.0, float(r.get("Amount") or 0))
            category_amounts.setdefault(cat, []).append(amt)
            category_frequency[cat] = category_frequency.get(cat, 0) + 1

        ml_flags = set()
        if len(rows) >= 10:
            try:
                from sklearn.ensemble import IsolationForest
                matrix = np.column_stack([
                    amounts,
                    np.array([category_frequency.get(str(r.get("Category") or "Other"), 1) for r in rows], dtype=float)
                ])
                labels = IsolationForest(
                    n_estimators=100, contamination=0.08, random_state=42
                ).fit_predict(matrix)
                ml_flags = {int(rows[i]["id"]) for i, label in enumerate(labels) if label == -1}
            except Exception as ml_error:
                print("Isolation Forest skipped:", ml_error)

        anomalies = []
        for row in rows:
            amount = max(0.0, float(row.get("Amount") or 0))
            category = str(row.get("Category") or "Other")
            cat_values = category_amounts.get(category, [])
            reasons = []

            if amount > personal_cutoff and len(amounts) >= 4:
                reasons.append("Higher than your usual spending")

            if len(cat_values) >= 3:
                cat_median = float(np.median(cat_values))
                cat_mad = float(np.median(np.abs(np.array(cat_values) - cat_median)))
                cat_cutoff = cat_median + (3.5 * 1.4826 * cat_mad if cat_mad > 0 else cat_median * 1.5)
                if amount > cat_cutoff and amount > cat_median:
                    reasons.append("Unusual amount for this category")

            # Multiple same-category transactions in a short period can indicate unusual frequency.
            try:
                this_date = pd.to_datetime(row.get("Date")).date()
                same_day_count = sum(
                    1 for other in rows
                    if str(other.get("Category") or "Other") == category
                    and pd.to_datetime(other.get("Date")).date() == this_date
                )
                if same_day_count >= 3:
                    reasons.append("Repeated category spending on the same day")
            except Exception:
                pass

            if int(row["id"]) in ml_flags:
                reasons.append("Flagged by ML anomaly detection")

            if reasons:
                date_value = row.get("Date")
                date_value = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
                anomalies.append({
                    "id": row["id"],
                    "date": date_value,
                    "category": category,
                    "description": row.get("Description") or "Unusual expense",
                    "amount": amount,
                    "reasons": reasons
                })

        anomalies.sort(key=lambda x: (len(x["reasons"]), x["amount"]), reverse=True)
        return jsonify({
            "anomalies": anomalies[:10],
            "methods": ["personal spending pattern", "unusual frequency", "ML anomaly detection"]
        })
    except Exception as error:
        print("Anomaly detection error:", error)
        return jsonify({"error": "Unable to detect anomalies."}), 500


# ============================================================
# PERSONALIZED AVOIDABLE-SPENDING INSIGHTS
# ============================================================

@app.route("/analytics/avoidable-spending", methods=["GET"])
def avoidable_spending():
    """Simple explainable savings suggestions from this user's own transactions."""
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Please login first."}), 401
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT Category,
                           DATE_FORMAT(Date, '%%Y-%%m') AS month,
                           SUM(Amount) AS total,
                           COUNT(*) AS transaction_count
                    FROM transactions
                    WHERE user_id = %s
                      AND Type = 'Expense'
                      AND Date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                    GROUP BY Category, DATE_FORMAT(Date, '%%Y-%%m')
                    ORDER BY month DESC
                    """,
                    (user_id,)
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        grouped = {}
        for row in rows:
            category = str(row.get("Category") or "Other")
            grouped.setdefault(category, {})
            grouped[category][str(row["month"])] = {
                "total": float(row.get("total") or 0),
                "count": int(row.get("transaction_count") or 0)
            }

        suggestions = []
        for category, months in grouped.items():
            values = [v["total"] for v in months.values()]
            if not values:
                continue
            recent = values[0]
            baseline_values = values[1:4] if len(values) > 1 else values
            baseline = sum(baseline_values) / len(baseline_values)
            if baseline > 0 and recent > baseline * 1.15 and recent - baseline >= 100:
                excess = recent - baseline
                suggestions.append({
                    "category": category,
                    "recent_month_spend": round(recent, 2),
                    "usual_monthly_spend": round(baseline, 2),
                    "potential_saving": round(excess * 0.25, 2),
                    "message": f"{category} spending is above your recent average. Consider reducing it by 10–25%."
                })

        suggestions.sort(key=lambda item: item["recent_month_spend"] - item["usual_monthly_spend"], reverse=True)
        return jsonify({"suggestions": suggestions[:5], "basis": "Your own recent monthly transaction history"})
    except Exception as error:
        print("Avoidable spending error:", error)
        return jsonify({"error": "Unable to generate spending suggestions."}), 500


# ============================================================
# AI EXPENSE PREDICTION
# ============================================================

@app.route(
    "/predict",
    methods=["POST"]
)
def predict_expense():

    user_id = login_required()

    if not user_id:

        return jsonify({
            "error":
                "Please login first."
        }), 401

    try:
        # Cold-start: a user with no transactions should see a clear ₹0 prediction.
        # This check happens before model availability so empty accounts still work
        # even if the ML model cannot be loaded.
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS transaction_count FROM transactions WHERE user_id = %s",
                    (user_id,)
                )
                transaction_row = cursor.fetchone() or {}
                transaction_count = int(transaction_row.get("transaction_count") or 0)
        finally:
            connection.close()

        if transaction_count == 0:
            return jsonify({
                "predicted_expense": 0.0,
                "model_prediction": 0.0,
                "personal_baseline": 0.0,
                "history_months": 0,
                "prediction_method": "No transactions yet — prediction is ₹0. Add transactions to personalize your forecast.",
                "personalized": False,
                "features": {}
            }), 200

        if model is None:
            return jsonify({
                "error": "Prediction model is not available."
            }), 500

        data = request.get_json()

        if not data:

            return jsonify({
                "error":
                    "Prediction input is required."
            }), 400

        current_year = int(
            data.get(
                "Year",
                datetime.now().year
            )
        )

        current_month = int(
            data.get(
                "Month",
                datetime.now().month
            )
        )

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT

                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m'
                        ) AS month,

                        COALESCE(
                            SUM(
                                CASE
                                    WHEN Type = 'Expense'
                                    THEN Amount
                                    ELSE 0
                                END
                            ),
                            0
                        ) AS expense,

                        COUNT(*) AS transaction_count

                    FROM transactions

                    WHERE
                        user_id = %s
                        AND Type = 'Expense'

                    GROUP BY
                        DATE_FORMAT(
                            Date,
                            '%%Y-%%m'
                        )

                    ORDER BY
                        month ASC
                    """,
                    (user_id,)
                )

                monthly_rows = cursor.fetchall()

        finally:

            connection.close()

        monthly_expenses = []

        monthly_transaction_counts = []

        for row in monthly_rows:

            monthly_expenses.append(
                float(
                    row["expense"] or 0
                )
            )

            monthly_transaction_counts.append(
                int(
                    row["transaction_count"] or 0
                )
            )

        previous_month_expense = (
            monthly_expenses[-1]
            if len(monthly_expenses) >= 1
            else 0
        )

        expense_2_months_ago = (
            monthly_expenses[-2]
            if len(monthly_expenses) >= 2
            else previous_month_expense
        )

        expense_3_months_ago = (
            monthly_expenses[-3]
            if len(monthly_expenses) >= 3
            else expense_2_months_ago
        )

        previous_transaction_count = (
            monthly_transaction_counts[-1]
            if monthly_transaction_counts
            else 0
        )

        recent_expenses = (
            monthly_expenses[-3:]
            if monthly_expenses
            else [0]
        )

        three_month_average = (
            sum(recent_expenses)
            /
            len(recent_expenses)
        )

        features = {

            "Year":
                current_year,

            "Month":
                current_month,

            "Previous_Month_Expense":
                previous_month_expense,

            "Expense_2_Months_Ago":
                expense_2_months_ago,

            "Expense_3_Months_Ago":
                expense_3_months_ago,

            "Previous_Transaction_Count":
                previous_transaction_count,

            "Three_Month_Avg_Expense":
                three_month_average
        }

        if model_features:

            if isinstance(
                model_features,
                (list, tuple)
            ):

                feature_order = list(
                    model_features
                )

            else:

                feature_order = list(
                    model_features
                )

        else:

            feature_order = [
                "Year",
                "Month",
                "Previous_Month_Expense",
                "Expense_2_Months_Ago",
                "Expense_3_Months_Ago",
                "Previous_Transaction_Count",
                "Three_Month_Avg_Expense"
            ]

        input_data = pd.DataFrame(
            [[
                features.get(
                    feature,
                    0
                )
                for feature in feature_order
            ]],
            columns=feature_order
        )

        prediction = model.predict(
            input_data
        )

        model_prediction = max(0.0, float(prediction[0]))

        # All features above are computed only from transactions filtered by user_id.
        # Blend the shared model with this user's own recent expense baseline when history exists.
        personal_baseline = float(three_month_average)
        if len(monthly_expenses) >= 3:
            predicted_expense = (0.60 * model_prediction) + (0.40 * personal_baseline)
            prediction_method = "Personalized blend: Random Forest + your own recent spending"
        elif len(monthly_expenses) >= 1:
            predicted_expense = (0.35 * model_prediction) + (0.65 * personal_baseline)
            prediction_method = "Limited personal history: weighted estimate using your own spending"
        else:
            predicted_expense = model_prediction
            prediction_method = "Model estimate: not enough personal transaction history yet"

        predicted_expense = max(0.0, float(predicted_expense))

        return jsonify({
            "predicted_expense": round(predicted_expense, 2),
            "model_prediction": round(model_prediction, 2),
            "personal_baseline": round(personal_baseline, 2),
            "history_months": len(monthly_expenses),
            "prediction_method": prediction_method,
            "personalized": len(monthly_expenses) > 0,
            "features": features
        })

    except Exception as error:

        print(
            "Prediction error:",
            error
        )

        return jsonify({

            "error":
                "Unable to generate expense prediction.",

            "details":
                str(error)

        }), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error":
            "API endpoint not found."
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error":
            "Internal server error."
    }), 500


# ============================================================
# BUDGET PLANNER AND SAVINGS GOALS
# New tables are created safely on demand; existing tables are untouched.
# ============================================================

def ensure_planning_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeflow_budgets (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            month CHAR(7) NOT NULL,
            category VARCHAR(80) NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_month_category (user_id, month, category),
            INDEX idx_budget_user_month (user_id, month)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeflow_savings_goals (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(120) NOT NULL,
            target_amount DECIMAL(12,2) NOT NULL,
            current_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
            target_date DATE NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_goal_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


@app.route("/planning/budgets", methods=["GET"])
def list_budgets():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    month = (request.args.get("month") or datetime.now().strftime("%Y-%m")).strip()
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return jsonify({"error": "Month must use YYYY-MM format."}), 400
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("""
                SELECT b.id, b.month, b.category, b.amount,
                       COALESCE(s.total_spent, 0) AS spent
                FROM financeflow_budgets b
                LEFT JOIN (
                    SELECT Category AS category_key, SUM(Amount) AS total_spent
                    FROM transactions
                    WHERE user_id = %s AND Type = 'Expense'
                      AND DATE_FORMAT(`Date`, '%%Y-%%m') = %s
                    GROUP BY Category
                ) s ON LOWER(s.category_key) = LOWER(b.category)
                WHERE b.user_id = %s AND b.month = %s
                ORDER BY b.category ASC
            """, (user_id, month, user_id, month))
            rows = cursor.fetchall()
        budgets = [{**row, "amount": float(row["amount"] or 0), "spent": float(row["spent"] or 0)} for row in rows]
        return jsonify({"budgets": budgets, "month": month})
    except Exception as error:
        app.logger.exception("Budget list failed")
        return jsonify({"error": "Unable to load budgets."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/budgets", methods=["POST"])
def save_budget():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    month = str(data.get("month", "")).strip()
    category = str(data.get("category", "")).strip()
    try:
        datetime.strptime(month, "%Y-%m")
        amount = float(data.get("amount"))
        if not category or len(category) > 80 or not np.isfinite(amount) or amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Provide a valid month, category, and positive amount."}), 400
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("""
                INSERT INTO financeflow_budgets (user_id, month, category, amount)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE amount = VALUES(amount)
            """, (user_id, month, category, amount))
        return jsonify({"message": "Budget saved successfully."}), 201
    except Exception:
        app.logger.exception("Budget save failed")
        return jsonify({"error": "Unable to save budget. Check your database connection."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/budgets/<int:budget_id>", methods=["DELETE"])
def remove_budget(budget_id):
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("DELETE FROM financeflow_budgets WHERE id = %s AND user_id = %s", (budget_id, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Budget not found."}), 404
        return jsonify({"message": "Budget removed."})
    except Exception:
        app.logger.exception("Budget delete failed")
        return jsonify({"error": "Unable to remove budget."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/goals", methods=["GET"])
def list_savings_goals():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("""
                SELECT id, name, target_amount, current_amount, target_date
                FROM financeflow_savings_goals WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
        goals = [{**row, "target_amount": float(row["target_amount"] or 0),
                  "current_amount": float(row["current_amount"] or 0),
                  "target_date": row["target_date"].isoformat() if row["target_date"] else None}
                 for row in rows]
        return jsonify({"goals": goals})
    except Exception:
        app.logger.exception("Savings goals list failed")
        return jsonify({"error": "Unable to load savings goals."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/goals", methods=["POST"])
def create_savings_goal():
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    try:
        target_amount = float(data.get("target_amount"))
        if not name or len(name) > 120 or not np.isfinite(target_amount) or target_amount <= 0:
            raise ValueError
        target_date = data.get("target_date") or None
        if target_date:
            datetime.strptime(str(target_date), "%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"error": "Provide a goal name, positive target amount, and valid target date."}), 400
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("""
                INSERT INTO financeflow_savings_goals (user_id, name, target_amount, current_amount, target_date)
                VALUES (%s, %s, %s, 0, %s)
            """, (user_id, name, target_amount, target_date))
        return jsonify({"message": "Savings goal created."}), 201
    except Exception:
        app.logger.exception("Savings goal create failed")
        return jsonify({"error": "Unable to create savings goal."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/goals/<int:goal_id>/contributions", methods=["POST"])
def add_savings_contribution(goal_id):
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
        if not np.isfinite(amount) or amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Contribution must be a positive amount."}), 400
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("""
                UPDATE financeflow_savings_goals
                SET current_amount = current_amount + %s
                WHERE id = %s AND user_id = %s
            """, (amount, goal_id, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Savings goal not found."}), 404
        return jsonify({"message": "Savings contribution added."})
    except Exception:
        app.logger.exception("Savings contribution failed")
        return jsonify({"error": "Unable to add savings contribution."}), 500
    finally:
        if connection:
            connection.close()


@app.route("/planning/goals/<int:goal_id>", methods=["DELETE"])
def delete_savings_goal(goal_id):
    user_id = login_required()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            ensure_planning_tables(cursor)
            cursor.execute("DELETE FROM financeflow_savings_goals WHERE id = %s AND user_id = %s", (goal_id, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Savings goal not found."}), 404
        return jsonify({"message": "Savings goal deleted."})
    except Exception:
        app.logger.exception("Savings goal delete failed")
        return jsonify({"error": "Unable to delete savings goal."}), 500
    finally:
        if connection:
            connection.close()


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "============================================================"
    )
    print(
        " FinanceFlow - AI Personal Finance Management System"
    )
    print(
        " Backend Server"
    )
    print(
        "============================================================"
    )
    print(
        f" Model loaded: {model is not None}"
    )
    print(
        f" Database: {DB_NAME}"
    )
    print(
        " Server: http://127.0.0.1:5000"
    )
    print(
        "============================================================"
    )
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )