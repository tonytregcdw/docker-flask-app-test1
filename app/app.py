import os
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, request, redirect
import requests
from urllib.parse import quote_plus

app = Flask(__name__)

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
TEST_ENV_VAR1 = os.environ.get('TEST_ENV_VAR1')

# Should point to the FastAPI server, e.g., "http://api:8000/people/"
API_URL = os.environ.get('API_URL')

@app.route("/")
def index():
    error_message = request.args.get("error")
    people = []
    if not API_URL:
        error_message = error_message or "API URL is not configured."
    else:
        try:
            resp = requests.get(API_URL, timeout=3)
            resp.raise_for_status()
            people = resp.json()
        except requests.RequestException:
            error_message = error_message or "API unavailable. Please try again later."
        except ValueError:
            error_message = error_message or "Received invalid data from API."
    return render_template("index.html", people=people, error_message=error_message)

@app.route("/add", methods=["POST"])
def add_person():
    name = request.form["name"]
    # Send JSON, not params
    try:
        if not API_URL:
            raise RuntimeError("API URL is not configured.")
        requests.post(API_URL, json={"name": name}, timeout=3)
    except Exception as e:
        message = quote_plus(str(e) if str(e) else "Failed to add person. API unavailable.")
        return redirect(f"/?error={message}")
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
