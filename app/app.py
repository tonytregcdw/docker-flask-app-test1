import os
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, request, redirect, session, url_for
from flask_session import Session
import redis
import requests
from urllib.parse import quote_plus

app = Flask(__name__)

app.secret_key = "CHANGE_ME"  # Use a secure key

# Load environment variables early for Redis config
load_dotenv()
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))

# Prefer Redis-backed sessions; gracefully fall back if Redis unavailable
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1, socket_timeout=1)
    redis_client.ping()
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis_client
except Exception:
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'

Session(app)  # Initialize server-side session



SECRET_VALUE = os.environ.get('SECRET_VALUE')

# Should point to the FastAPI server, e.g., "http://api:8000/people/"
API_URL = os.environ.get('API_URL')

@app.route("/")
def index():
    error_message = request.args.get("error")
    people = []
    username = session.get('username')

    if not username:
        # Not logged in: show template with login prompt; do not call API
        secret_active = SECRET_VALUE is not None
        error_message = error_message or "Please log in to view data."
        return render_template("index.html", people=[], error_message=error_message, secret_active=secret_active, username=None)

    # Logged in: fetch data from API if configured
    if not API_URL:
        error_message = error_message or "API URL is not configured."
    else:
        try:
            headers = {}
            # Forward the signed Flask session cookie so API can resolve user from Redis
            sess_cookie = request.cookies.get('session')
            if sess_cookie:
                headers["X-Session"] = sess_cookie
            resp = requests.get(API_URL, timeout=3, headers=headers)
            resp.raise_for_status()
            people = resp.json()
        except requests.RequestException:
            error_message = error_message or "API unavailable. Please try again later."
        except ValueError:
            error_message = error_message or "Received invalid data from API."

    secret_active = SECRET_VALUE is not None
    return render_template("index.html", people=people, error_message=error_message, secret_active=secret_active, username=username)

# (Removed duplicate index route)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return '''
        <form method="post">
            <input name="username" required />
            <button type="submit">Login</button>
        </form>
    '''

@app.route('/profile')
def profile():
    username = session.get('username')
    if username:
        return f"Welcome, {username}!"
    return "Not logged in. <a href='/login'>Login</a>"

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route("/add", methods=["POST"])
def add_person():
    # Require login to add
    if not session.get('username'):
        message = quote_plus('Please log in to add people.')
        return redirect(f"/?error={message}")
    name = request.form["name"]
    # Send JSON, not params
    try:
        if not API_URL:
            raise RuntimeError("API URL is not configured.")
        headers = {}
        # Forward the signed Flask session cookie so API can resolve user from Redis
        sess_cookie = request.cookies.get('session')
        if sess_cookie:
            headers["X-Session"] = sess_cookie
        requests.post(API_URL, json={"name": name}, timeout=3, headers=headers)
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



