import os
import joblib
import pandas as pd
import pymysql

from flask import Flask, request, jsonify
from flask_cors import CORS


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "models",
    "random_forest_expense_model.pkl"
)

FEATURES_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "models",
    "model_features.pkl"
)


# ============================================================
# LOAD MACHINE LEARNING MODEL
# ============================================================

try:
    loaded_model = joblib.load(MODEL_PATH)
    model_features = joblib.load(FEATURES_PATH)

    print("Random Forest model loaded successfully!")
    print("Model type:", type(loaded_model).__name__)
    print("Number of trees:", loaded_model.n_estimators)
    print("Number of features:", len(model_features))
    print("Features:", model_features)

except Exception as e:
    print("ERROR loading ML model:", e)

    loaded_model = None
    model_features = []


# ============================================================
# MYSQL CONFIGURATION
# ============================================================

from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")


# ============================================================
# MYSQL CONNECTION
# ============================================================

def get_db_connection():

    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor
    )


# ============================================================
# HOME API
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "project": "AI Personal Finance Management System",
        "status": "Backend is running successfully"
    })


# ============================================================
# MODEL INFO API
# ============================================================

@app.route("/model-info", methods=["GET"])
def model_info():

    if loaded_model is None:
        return jsonify({
            "error": "ML model could not be loaded"
        }), 500

    return jsonify({
        "project": "AI Personal Finance Management System",
        "model": "Random Forest Regressor",
        "number_of_trees": loaded_model.n_estimators,
        "target": "Total_Expense",
        "features": model_features
    })


# ============================================================
# PREDICTION API
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    try:

        if loaded_model is None:
            return jsonify({
                "error": "ML model is not loaded"
            }), 500

        data = request.get_json()

        input_data = pd.DataFrame([{
            "Year": data["Year"],
            "Month": data["Month"],
            "Previous_Month_Expense": data["Previous_Month_Expense"],
            "Expense_2_Months_Ago": data["Expense_2_Months_Ago"],
            "Expense_3_Months_Ago": data["Expense_3_Months_Ago"],
            "Previous_Transaction_Count": data["Previous_Transaction_Count"],
            "Three_Month_Avg_Expense": data["Three_Month_Avg_Expense"]
        }])

        input_data = input_data[model_features]

        prediction = loaded_model.predict(input_data)

        return jsonify({
            "predicted_expense": round(float(prediction[0]), 2)
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400


# ============================================================
# ADD TRANSACTION API
# ============================================================

@app.route("/transactions", methods=["POST"])
def add_transaction():

    try:

        data = request.get_json()

        transaction_date = data["date"]
        description = data["description"]
        category = data["category"]
        amount = float(data["amount"])
        transaction_type = data["type"]

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                sql = """
                INSERT INTO transactions
                (Date, Amount, Category, Description, Type)
                VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    sql,
                    (
                        transaction_date,
                        amount,
                        category,
                        description,
                        transaction_type
                    )
                )

                transaction_id = cursor.lastrowid

            connection.commit()

        finally:

            connection.close()

        return jsonify({
            "message": "Transaction added successfully!",
            "transaction": {
                "id": transaction_id,
                "date": transaction_date,
                "description": description,
                "category": category,
                "amount": amount,
                "type": transaction_type
            }
        }), 201

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400


# ============================================================
# GET TRANSACTIONS API
# ============================================================

@app.route("/transactions", methods=["GET"])
def get_transactions():

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                sql = """
                SELECT
                    id,
                    Date,
                    Amount,
                    Category,
                    Description,
                    Type
                FROM transactions
                ORDER BY Date DESC, id DESC
                """

                cursor.execute(sql)

                transactions = cursor.fetchall()

        finally:

            connection.close()

        for transaction in transactions:

            if transaction["Date"] is not None:
                transaction["Date"] = transaction["Date"].isoformat()

            if transaction["Amount"] is not None:
                transaction["Amount"] = float(transaction["Amount"])

        return jsonify({
            "count": len(transactions),
            "transactions": transactions
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# SUMMARY API
# ============================================================

@app.route("/summary", methods=["GET"])
def summary():

    try:

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                income_sql = """
                SELECT COALESCE(SUM(Amount), 0) AS total_income
                FROM transactions
                WHERE Type = 'Income'
                """

                expense_sql = """
                SELECT COALESCE(SUM(Amount), 0) AS total_expense
                FROM transactions
                WHERE Type = 'Expense'
                """

                count_sql = """
                SELECT COUNT(*) AS transaction_count
                FROM transactions
                """

                cursor.execute(income_sql)
                income_result = cursor.fetchone()

                cursor.execute(expense_sql)
                expense_result = cursor.fetchone()

                cursor.execute(count_sql)
                count_result = cursor.fetchone()

        finally:

            connection.close()

        total_income = float(income_result["total_income"])
        total_expense = float(expense_result["total_expense"])
        transaction_count = int(count_result["transaction_count"])

        balance = total_income - total_expense

        return jsonify({
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "balance": round(balance, 2),
            "transaction_count": transaction_count
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# RUN FLASK SERVER
# ============================================================

if __name__ == "__main__":

    print("======================================")
    print("AI Personal Finance Management System")
    print("Flask Backend Starting...")
    print("======================================")

    print("Available APIs:")
    print("GET  /")
    print("POST /predict")
    print("GET  /model-info")
    print("POST /transactions")
    print("GET  /transactions")
    print("GET  /summary")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )