import os
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, redirect
import requests

app = Flask(__name__)


load_dotenv()  # This will read variables from .env

SECRET_KEY = os.environ.get('SECRET_KEY')
TEST_ENV_VAR1 = os.environ.get('TEST_ENV_VAR1')

# Adjust this to match the host/port of your API service inside your deployment
API_URL = os.environ.get('API_URL')
# API_URL = "http://api:8000/people/"

@app.route("/")
def index():
    try:
        resp = requests.get(API_URL)
        people = resp.json()
    except Exception as e:
        people = []
    return render_template_string("""
        <h1>People List</h1>
        <form method="post" action="/add">
            <input name="name" placeholder="Name" required>
            <input type="submit" value="Add">
        </form>
        <ul>
            {% for person in people %}
                <li>{{ person['id'] }}: {{ person['name'] }}</li>
            {% endfor %}
        </ul>
    """, people=people)

@app.route("/add", methods=["POST"])
def add_person():
    name = request.form["name"]
    requests.post(API_URL, params={"name": name})
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
