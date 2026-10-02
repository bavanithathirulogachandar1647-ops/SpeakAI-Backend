from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
from google import genai
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY",
    "SpeakAI_Secret_Key_2026"
)

jwt = JWTManager(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "language_learning")
    )


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "SpeakAI Backend is Running!"
    })


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
            "message": "Database connected successfully",
            "result": result[0]
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({
                "error": "All fields are required"
            }), 400

        db = get_db_connection()
        cursor = db.cursor()

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
            }), 400

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (name, email, hashed_password)
        )

        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO progress (
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

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


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

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if not user:
            return jsonify({
                "error": "Invalid email or password"
            }), 401

        if not check_password_hash(user["password"], password):
            return jsonify({
                "error": "Invalid email or password"
            }), 401

        access_token = create_access_token(
            identity=str(user["id"])
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"]
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/ai-tutor", methods=["POST"])
def ai_tutor():
    try:
        data = request.get_json()

        question = data.get("question")

        if not question:
            return jsonify({
                "error": "Question is required"
            }), 400

        if not client:
            return jsonify({
                "error": "Gemini API is not configured"
            }), 500

        prompt = f"""
You are an English learning AI tutor.

Explain the following question clearly and simply.
Help the learner understand the answer.

Question:
{question}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "answer": response.text
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json()

        text = data.get("text")

        if not text:
            return jsonify({
                "error": "Text is required"
            }), 400

        if not client:
            return jsonify({
                "error": "Gemini API is not configured"
            }), 500

        prompt = f"""
Translate the following English text into Tamil.

Give only the Tamil translation.

English:
{text}
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


@app.route("/grammar-correction", methods=["POST"])
def grammar_correction():
    try:
        data = request.get_json()

        text = data.get("text")

        if not text:
            return jsonify({
                "error": "Text is required"
            }), 400

        if not client:
            return jsonify({
                "error": "Gemini API is not configured"
            }), 500

        prompt = f"""
You are an English grammar correction assistant.

Analyze the following sentence.

Give:
1. Corrected sentence
2. Grammar explanation
3. One simple example

Sentence:
{text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return jsonify({
            "result": response.text
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    try:
        data = request.get_json()

        topic = data.get("topic", "English Grammar")

        if not client:
            return jsonify({
                "error": "Gemini API is not configured"
            }), 500

        prompt = f"""
Create a simple English learning quiz about {topic}.

Create 5 multiple-choice questions.

For each question provide:
- question
- four options
- correct answer

Return the result in JSON format like this:

[
  {{
    "question": "Question",
    "options": ["A", "B", "C", "D"],
    "answer": "A"
  }}
]
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text

        return jsonify({
            "quiz": text
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/speaking-practice", methods=["POST"])
def speaking_practice():
    try:
        data = request.get_json()

        text = data.get("text")

        if not text:
            return jsonify({
                "error": "Text is required"
            }), 400

        if not client:
            return jsonify({
                "error": "Gemini API is not configured"
            }), 500

        prompt = f"""
You are an English speaking practice assistant.

Analyze this sentence:

{text}

Provide:
1. Grammar feedback
2. Natural English version
3. Pronunciation tips
4. One simple improvement suggestion
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


@app.route("/progress/<int:user_id>", methods=["GET"])
@jwt_required()
def get_progress(user_id):
    try:
        current_user_id = int(get_jwt_identity())

        if current_user_id != user_id:
            return jsonify({
                "error": "Unauthorized"
            }), 403

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


@app.route("/progress", methods=["POST"])
@jwt_required()
def update_progress():
    try:
        data = request.get_json()

        user_id = data.get("user_id")

        current_user_id = int(get_jwt_identity())

        if current_user_id != int(user_id):
            return jsonify({
                "error": "Unauthorized"
            }), 403

        vocabulary_completed = data.get(
            "vocabulary_completed",
            0
        )

        grammar_completed = data.get(
            "grammar_completed",
            0
        )

        quiz_score = data.get(
            "quiz_score",
            0
        )

        pronunciation_completed = data.get(
            "pronunciation_completed",
            0
        )

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO progress (
                user_id,
                vocabulary_completed,
                grammar_completed,
                quiz_score,
                pronunciation_completed
            )
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                vocabulary_completed = VALUES(vocabulary_completed),
                grammar_completed = VALUES(grammar_completed),
                quiz_score = VALUES(quiz_score),
                pronunciation_completed = VALUES(pronunciation_completed)
            """,
            (
                user_id,
                vocabulary_completed,
                grammar_completed,
                quiz_score,
                pronunciation_completed
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


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
