import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
from flask_session import Session
import redis
import requests
from itsdangerous import URLSafeTimedSerializer
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = "CHANGE_ME"  # Use a secure key

load_dotenv()
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))

app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1, socket_timeout=1)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis_client
Session(app)

FLASK_SECRET = os.environ.get('FLASK_SECRET', 'CHANGE_ME')
API_URL = os.environ.get('API_URL')
REPLICA_NAME = os.environ.get('ACONTAINER_APP_REPLICA_NAME')

# Shared itsdangerous serializer for tokens
SIGNER = URLSafeTimedSerializer(FLASK_SECRET, salt="cookie-session")

@app.route("/")
def index():
    error_message = request.args.get("error")
    people = []
    username = session.get('username')
    api_session_token = session.get('api_session_token')
    if not username or not api_session_token:
        error_message = error_message or "Please log in to view data."
        return render_template("index.html", people=[], error_message=error_message, username=None)
    if not API_URL:
        error_message = error_message or "API URL is not configured."
    else:
        try:
            headers = {}
            headers["X-Session"] = api_session_token
            resp = requests.get(API_URL, timeout=3, headers=headers)
            resp.raise_for_status()
            people = resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503:
                try:
                    api_error = e.response.json().get('detail', 'Service unavailable')
                    error_message = f"API Service Error: {api_error}"
                except:
                    error_message = f"API Service Error: {e.response.text or 'Service unavailable'}"
            else:
                error_message = f"API Error {e.response.status_code}: {e.response.text or 'Unknown error'}"
        except requests.exceptions.RequestException as e:
            error_message = f"API Connection Error: {str(e)}"
        except ValueError:
            error_message = "Received invalid data from API."
    return render_template("index.html", people=people, error_message=error_message, username=username, replica=REPLICA_NAME)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        session['api_session_token'] = SIGNER.dumps({'username': username})
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
    session.pop('api_session_token', None)
    return redirect(url_for('index'))

@app.route("/add", methods=["POST"])
def add_person():
    if not session.get('username') or not session.get('api_session_token'):
        message = quote_plus('Please log in to add people.')
        return redirect(f"/?error={message}")
    name = request.form["name"]
    try:
        if not API_URL:
            raise RuntimeError("API URL is not configured.")
        headers = {"X-Session": session['api_session_token']}
        resp = requests.post(API_URL, json={"name": name}, timeout=3, headers=headers)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            try:
                api_error = e.response.json().get('detail', 'Service unavailable')
                message = f"API Service Error: {api_error}"
            except:
                message = f"API Service Error: {e.response.text or 'Service unavailable'}"
        else:
            message = f"API Error {e.response.status_code}: {e.response.text or 'Unknown error'}"
        message = quote_plus(message)
        return redirect(f"/?error={message}")
    except requests.exceptions.RequestException as e:
        message = quote_plus(f"API Connection Error: {str(e)}")
        return redirect(f"/?error={message}")
    except Exception as e:
        message = quote_plus(str(e) if str(e) else "Failed to add person. API unavailable.")
        return redirect(f"/?error={message}")
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
