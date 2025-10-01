from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import redis
import pickle
from itsdangerous import Signer, BadSignature
from typing import Optional

load_dotenv()
MONGODB_URL = os.environ.get('MONGODB_URL', "mongodb://localhost:27017")
DB_NAME = os.environ.get('DB_NAME', "testdb")
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
FLASK_SECRET = os.environ.get('FLASK_SECRET', 'CHANGE_ME')

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

app = FastAPI()

# Optional Redis client to read Flask session data
redis_client = None
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1, socket_timeout=1)
    redis_client.ping()
except Exception:
    redis_client = None

signer = None
if FLASK_SECRET:
    try:
        signer = Signer(FLASK_SECRET, salt='flask-session')
    except Exception:
        signer = None

def get_username_from_request(request: Request) -> Optional[str]:
    # 1) Prefer explicit header from trusted frontend
    header_user = request.headers.get('X-User')
    if header_user:
        return header_user
    # 2) Try explicit forwarded session header from frontend
    cookie_val = request.headers.get('X-Session') or request.cookies.get('session')
    if not cookie_val or not signer or not redis_client:
        return None
    try:
        unsigned = signer.unsign(cookie_val).decode('utf-8')
    except (BadSignature, Exception):
        return None
    # Flask-Session Redis key pattern
    redis_key = f"session:{unsigned}"
    try:
        raw = redis_client.get(redis_key)
        if not raw:
            return None
        data = pickle.loads(raw)
        return data.get('username')
    except Exception:
        return None

# Pydantic model for "Person"
class PersonModel(BaseModel):
    name: str

@app.get("/people/")
async def read_people(request: Request):
    _user = get_username_from_request(request)
    people_cursor = db.people.find({})
    people = []
    async for person in people_cursor:
        people.append({
            "id": str(person.get("_id")),
            "name": person.get("name", ""),
            "username": person.get("username", "")
        })
    return people

@app.post("/people/")
async def add_person(person: PersonModel, request: Request):
    user = get_username_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: user not identified")
    # Augment the document with the active session user
    doc = {**person.dict(), "username": user}
    result = await db.people.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "name": person.name,
        "username": user
    }
