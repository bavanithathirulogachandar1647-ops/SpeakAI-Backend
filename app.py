from flask import Flask, request, jsonify
from flask_cors import CORS

import mysql.connector
import os

from dotenv import load_dotenv
from google import genai

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

CORS(app)


# =========================================================
# JWT CONFIGURATION
# =========================================================

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY",
    "SpeakAI_Secret_Key_2026"
)

jwt = JWTManager(app)


# =========================================================
# GEMINI CONFIGURATION
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# MYSQL DATABASE CONNECTION
# =========================================================

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="language_learning"
    )


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "AI Language Learning Platform Backend is Running!"
    })


# =========================================================
# TEST DATABASE
# =========================================================

@app.route("/test-db", methods=["GET"])
def test_db():

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute("SELECT 1")

        result = cursor.fetchone()

        cursor.close()
        db.close()

        return jsonify({
            "message": "MySQL connection successful!",
            "result": result
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    try:

        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        # -----------------------------
        # VALIDATION
        # -----------------------------

        if not name or not email or not password:

            return jsonify({
                "error": "All fields are required"
            }), 400

        if len(password) < 6:

            return jsonify({
                "error": "Password must contain at least 6 characters"
            }), 400

        # -----------------------------
        # HASH PASSWORD
        # -----------------------------

        hashed_password = generate_password_hash(
            password
        )

        # -----------------------------
        # DATABASE
        # -----------------------------

        db = get_db_connection()

        cursor = db.cursor()

        # Check existing email

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            db.close()

            return jsonify({
                "error": "Email already registered"
            }), 409

        # -----------------------------
        # INSERT USER
        # -----------------------------

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        user_id = cursor.lastrowid

        # -----------------------------
        # CREATE PROGRESS RECORD
        # -----------------------------

        cursor.execute(
            """
            INSERT INTO progress
            (
                user_id,
                vocabulary_completed,
                grammar_completed,
                quiz_score,
                pronunciation_completed
            )
            VALUES (%s, 0, 0, 0, 0)
            """,
            (user_id,)
        )

        db.commit()

        cursor.close()
        db.close()

        return jsonify({
            "message": "Registration successful",
            "user_id": user_id
        }), 201

    except mysql.connector.Error as e:

        return jsonify({
            "error": f"MySQL error: {str(e)}"
        }), 500

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.get_json()

        email = data.get("email")
        password = data.get("password")

        if not email or not password:

            return jsonify({
                "error": "Email and password are required"
            }), 400

        # -----------------------------
        # DATABASE
        # -----------------------------

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        # -----------------------------
        # CHECK USER
        # -----------------------------

        if not user:

            return jsonify({
                "error": "Invalid email or password"
            }), 401

        # -----------------------------
        # CHECK HASHED PASSWORD
        # -----------------------------

        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "error": "Invalid email or password"
            }), 401

        # -----------------------------
        # CREATE JWT TOKEN
        # -----------------------------

        access_token = create_access_token(
            identity=str(user["id"])
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }), 200

    except mysql.connector.Error as e:

        return jsonify({
            "error": f"MySQL error: {str(e)}"
        }), 500

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# AI TUTOR / AI CONVERSATION
# =========================================================

@app.route("/ai-tutor", methods=["POST"])
def ai_tutor():

    try:

        data = request.get_json()

        question = data.get("question")

        if not question:

            return jsonify({
                "error": "Question is required"
            }), 400

        prompt = f"""
You are SpeakAI, an AI English language tutor.

Answer the student's question clearly and simply.

Student question:
{question}

Give a helpful educational response.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "response": response.text
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# TAMIL TRANSLATION
# =========================================================

@app.route("/translate", methods=["POST"])
def translate():

    try:

        data = request.get_json()

        text = data.get("text")

        if not text:

            return jsonify({
                "error": "Text is required"
            }), 400

        prompt = f"""
Translate the following English text into Tamil.

English:
{text}

Return only the Tamil translation.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "translation": response.text
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# GRAMMAR CORRECTION
# =========================================================

@app.route("/grammar-correction", methods=["POST"])
def grammar_correction():

    try:

        data = request.get_json()

        text = data.get("text")

        if not text:

            return jsonify({
                "error": "Text is required"
            }), 400

        prompt = f"""
You are an English grammar teacher.

Check the following sentence.

Sentence:
{text}

Give the response in this format:

Corrected Sentence:
Explain the mistakes:
Grammar Tip:

Keep the explanation simple.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "feedback": response.text
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# AI QUIZ
# =========================================================

@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():

    try:

        data = request.get_json()

        topic = data.get("topic")

        if not topic:

            return jsonify({
                "error": "Topic is required"
            }), 400

        prompt = f"""
Create a simple English learning quiz.

Topic:
{topic}

Create 5 questions.

Each question should have:
1. Question
2. Four options: A, B, C, D
3. Correct answer

Make the quiz suitable for a beginner English learner.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "quiz": response.text
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# SPEAKING PRACTICE
# =========================================================

@app.route("/speaking-practice", methods=["POST"])
def speaking_practice():

    try:

        data = request.get_json()

        text = data.get("text")
        user_id = data.get("user_id")

        if not text:

            return jsonify({
                "error": "Text is required"
            }), 400

        prompt = f"""
You are an English pronunciation and speaking coach.

Evaluate this spoken sentence:

{text}

Give:

Score out of 100:
Pronunciation feedback:
Grammar feedback:
Speaking improvement tip:
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        feedback = response.text

        # -----------------------------
        # SAVE SPEAKING PROGRESS
        # -----------------------------

        if user_id:

            db = get_db_connection()

            cursor = db.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    vocabulary_completed,
                    grammar_completed,
                    quiz_score,
                    pronunciation_completed
                FROM progress
                WHERE user_id = %s
                """,
                (user_id,)
            )

            progress = cursor.fetchone()

            if progress:

                cursor.execute(
                    """
                    UPDATE progress
                    SET pronunciation_completed =
                        pronunciation_completed + 1
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )

            else:

                cursor.execute(
                    """
                    INSERT INTO progress
                    (
                        user_id,
                        vocabulary_completed,
                        grammar_completed,
                        quiz_score,
                        pronunciation_completed
                    )
                    VALUES (%s, 0, 0, 0, 1)
                    """,
                    (user_id,)
                )

            db.commit()

            cursor.close()
            db.close()

        return jsonify({
            "feedback": feedback
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# GET USER PROGRESS
# =========================================================

@app.route("/progress/<int:user_id>", methods=["GET"])
@jwt_required()
def get_progress(user_id):

    try:

        # -----------------------------
        # GET LOGGED-IN USER
        # -----------------------------

        current_user_id = int(
            get_jwt_identity()
        )

        # -----------------------------
        # SECURITY CHECK
        # -----------------------------

        if current_user_id != user_id:

            return jsonify({
                "error": "Unauthorized"
            }), 403

        # -----------------------------
        # DATABASE
        # -----------------------------

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                vocabulary_completed,
                grammar_completed,
                quiz_score,
                pronunciation_completed
            FROM progress
            WHERE user_id = %s
            """,
            (user_id,)
        )

        progress = cursor.fetchone()

        cursor.close()
        db.close()

        if not progress:

            return jsonify({
                "vocabulary_completed": 0,
                "grammar_completed": 0,
                "quiz_score": 0,
                "pronunciation_completed": 0
            })

        return jsonify(progress)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# UPDATE USER PROGRESS
# =========================================================

@app.route("/progress", methods=["POST"])
@jwt_required()
def update_progress():

    try:

        data = request.get_json()

        user_id = data.get("user_id")

        vocabulary_completed = int(
            data.get("vocabulary_completed", 0)
        )

        grammar_completed = int(
            data.get("grammar_completed", 0)
        )

        quiz_score = int(
            data.get("quiz_score", 0)
        )

        pronunciation_completed = int(
            data.get("pronunciation_completed", 0)
        )

        # -----------------------------
        # JWT USER
        # -----------------------------

        current_user_id = int(
            get_jwt_identity()
        )

        # -----------------------------
        # SECURITY CHECK
        # -----------------------------

        if current_user_id != int(user_id):

            return jsonify({
                "error": "Unauthorized"
            }), 403

        # -----------------------------
        # DATABASE
        # -----------------------------

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE progress
            SET
                vocabulary_completed = %s,
                grammar_completed = %s,
                quiz_score = %s,
                pronunciation_completed = %s
            WHERE user_id = %s
            """,
            (
                vocabulary_completed,
                grammar_completed,
                quiz_score,
                pronunciation_completed,
                user_id
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return jsonify({
            "message": "Progress updated successfully"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
