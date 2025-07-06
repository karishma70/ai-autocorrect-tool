from flask import Flask, request, jsonify, session
from flask_cors import CORS
from langdetect import detect
from deep_translator import GoogleTranslator
import language_tool_python
import requests


app = Flask(__name__)
app.secret_key = 'secret123'
CORS(app)
tool = language_tool_python.LanguageTool('en-US')
users = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if email in users:
        return jsonify({"success": False, "message": "User already exists."})
    users[email] = {"password": password, "is_premium": False}
    return jsonify({"success": True, "message": "Registered successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = users.get(email)

    if user and user["password"] == password:
        return jsonify(success=True, email=email, is_premium=user.get("is_premium", False))
    return jsonify(success=False, message="Invalid credentials")

@app.route('/upgrade', methods=['POST'])
def upgrade():
    data = request.get_json()
    email = data.get('email')
    if email in users:
        users[email]["is_premium"] = True
        return jsonify(success=True)
    return jsonify(success=False, message="User not found")

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"success": True})

@app.route('/correct', methods=['POST'])
def correct_text():
    data = request.get_json()
    input_text = data.get('text', '')

    if not input_text.strip():
        return jsonify({'corrected': '', 'alternatives': []})

    try:
        response = requests.post(
            "https://api.languagetoolplus.com/v2/check",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                'text': input_text,
                'language': 'en-US'
            }
        )

        result = response.json()
        matches = result.get("matches", [])
        corrected_text = input_text
        offset_shift = 0

        alternatives = []

        for match in matches:
            replacements = match.get("replacements", [])
            if not replacements:
                continue

            start = match["offset"] + offset_shift
            end = start + match["length"]
            incorrect = corrected_text[start:end]

            best_replacement = replacements[0]["value"]
            corrected_text = corrected_text[:start] + best_replacement + corrected_text[end:]
            offset_shift += len(best_replacement) - match["length"]

            suggestions = [rep["value"] for rep in replacements[:5]]  # limit to top 5
            message = match.get("message", "")

            alternatives.append({
                "error": incorrect,
                "suggestions": suggestions,
                "message": message
            })

        return jsonify({
            "corrected": corrected_text,
            "alternatives": alternatives
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
