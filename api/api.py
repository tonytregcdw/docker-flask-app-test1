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
print(f"API Redis config: REDIS_HOST={REDIS_HOST}, REDIS_PORT={REDIS_PORT}")
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1, socket_timeout=1)
    redis_client.ping()
    print("API: Redis connection successful")
except Exception as e:
    print(f"API: Redis connection failed - {e}")
    redis_client = None

signer = None
if FLASK_SECRET:
    try:
        # Flask default cookie session salt is 'cookie-session'
        signer = Signer(FLASK_SECRET, salt='cookie-session')
    except Exception:
        signer = None

def get_username_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve username from forwarded signed session cookie.
    Returns (username, error_message) tuple.
    """
    cookie_val = request.headers.get('X-Session') or request.cookies.get('session')
    if not cookie_val:
        return None, "No session cookie provided"
    
    if not signer:
        return None, "Session signing not configured (FLASK_SECRET missing)"
    
    if not redis_client:
        return None, "Redis not available - cannot validate session"
    
    try:
        unsigned = signer.unsign(cookie_val).decode('utf-8')
    except (BadSignature, Exception):
        return None, "Invalid session cookie signature"
    
    # Flask-Session Redis key pattern
    redis_key = f"session:{unsigned}"
    try:
        raw = redis_client.get(redis_key)
        if not raw:
            return None, "Session expired or not found"
        data = pickle.loads(raw)
        username = data.get('username')
        if not username:
            return None, "No username in session data"
        return username, None
    except Exception as e:
        return None, f"Redis error: {str(e)}"

# Pydantic model for "Person"
class PersonModel(BaseModel):
    name: str

@app.get("/people/")
async def read_people(request: Request):
    user, error = get_username_from_request(request)
    if error:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {error}")
    
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
    user, error = get_username_from_request(request)
    if error:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {error}")
    
    # Augment the document with the active session user
    doc = {**person.dict(), "username": user}
    result = await db.people.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "name": person.name,
        "username": user
    }

    
