import os
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, request, redirect
import requests
from urllib.parse import quote_plus

app = Flask(__name__)

load_dotenv()

SECRET_VALUE = os.environ.get('SECRET_VALUE')

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
    
    # Check if secret value is present for special functionality
    secret_active = SECRET_VALUE is not None
    return render_template("index.html", people=people, error_message=error_message, secret_active=secret_active)

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

@app.route("/debug")
def debug_info():
    # This endpoint only works when SECRET_VALUE is present
    if not SECRET_VALUE:
        return "Debug endpoint not available - SECRET_VALUE not configured", 404
    
    debug_info = {
        "secret_configured": True,
        "secret_length": len(SECRET_VALUE),
        "api_configured": API_URL is not None,
        "api_url": API_URL,
        "secret_value_preview": SECRET_VALUE[:3] + "..." if len(SECRET_VALUE) > 3 else "***"
    }
    
    # Return as JSON for easy debugging
    from flask import jsonify
    return jsonify(debug_info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
