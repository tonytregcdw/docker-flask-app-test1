import os
import time
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import redis
from itsdangerous import URLSafeTimedSerializer, BadSignature
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")
 
load_dotenv()
MONGODB_URL = os.environ.get('MONGODB_URL', "mongodb://localhost:27017")
DB_NAME = os.environ.get('DB_NAME', "testdb")
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
FLASK_SECRET = os.environ.get('FLASK_SECRET', 'CHANGE_ME')

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

app = FastAPI()
redis_client = None

@app.on_event("startup")
async def startup_event():
    global redis_client
    logger.info("=" * 50)
    logger.info("API STARTUP: Redis Connection Debug")
    logger.info("=" * 50)
    logger.info(f"API Redis config: REDIS_HOST={REDIS_HOST}, REDIS_PORT={REDIS_PORT}")
    logger.info(f"API Environment: FLASK_SECRET={'SET' if FLASK_SECRET else 'NOT SET'}")
    logger.info(f"API Environment: MONGODB_URL={MONGODB_URL}")
    logger.info(f"API Environment: DB_NAME={DB_NAME}")
    for attempt in range(5):
        try:
            rc = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                socket_connect_timeout=2, 
                socket_timeout=2
            )
            rc.ping()
            logger.info("✅ API: Redis connection successful")
            redis_client = rc
            break
        except Exception as e:
            logger.error(f"❌ API: Redis connection failed (attempt {attempt+1}/5) - {e}")
            time.sleep(2)
    else:
        logger.error("❌ API: Redis connection could not be established after retries")
        redis_client = None
    logger.info("=" * 50)

@app.get("/health")
async def health_check():
    redis_status = "connected" if redis_client else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "mongodb": "connected",
        "flask_secret": "SET" if FLASK_SECRET else "NOT SET"
    }

# Use matching secret and salt for itsdangerous
SIGNER = URLSafeTimedSerializer(
    FLASK_SECRET,
    salt='cookie-session'
)

def get_username_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    cookie_val = request.headers.get('X-Session')
    if not cookie_val:
        return None, "No session token provided"
    try:
        session_data = SIGNER.loads(cookie_val)
        username = session_data.get('username')
        if not username:
            return None, "No username in session token"
        return username, None
    except BadSignature:
        return None, "Invalid session token signature"
    except Exception as e:
        return None, f"Session token decode error: {str(e)}"

class PersonModel(BaseModel):
    name: str

@app.post("/people/")
async def add_person(person: PersonModel, request: Request):
    logger.info(f"🔍 POST /people/ - Headers: {dict(request.headers)}")
    user, error = get_username_from_request(request)
    logger.info(f"🔍 POST /people/ - User: {user}, Error: {error}")
    if error:
        logger.error(f"❌ POST /people/ - Returning 503: {error}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {error}")
    doc = {**person.dict(), "username": user}
    result = await db.people.insert_one(doc)
    logger.info(f"✅ POST /people/ - Created person for user: {user}")
    return {
        "id": str(result.inserted_id),
        "name": person.name,
        "username": user
    }

@app.post("/people/")
async def add_person(person: PersonModel, request: Request):
    logger.info(f"🔍 POST /people/ - Headers: {dict(request.headers)}")
    user, error
