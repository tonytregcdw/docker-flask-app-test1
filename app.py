import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # This will read variables from .env

SECRET_KEY = os.environ.get('SECRET_KEY')
TEST_ENV_VAR1 = os.environ.get('TEST_ENV_VAR1')

app = Flask(__name__)

@app.route('/')
def home():
    return f"Flask Container app test!  Secret: {SECRET_KEY} Envvar: {TEST_ENV_VAR1}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
