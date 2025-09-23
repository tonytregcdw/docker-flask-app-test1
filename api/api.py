from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGODB_URL = os.environ.get('MONGODB_URL', "mongodb://localhost:27017")
DB_NAME = os.environ.get('DB_NAME', "testdb")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

app = FastAPI()

# Pydantic model for "Person"
class PersonModel(BaseModel):
    name: str

@app.get("/people/")
async def read_people():
    people_cursor = db.people.find({})
    people = []
    async for person in people_cursor:
        people.append({
            "id": str(person.get("_id")),
            "name": person.get("name", "")
        })
    return people

@app.post("/people/")
async def add_person(person: PersonModel):
    result = await db.people.insert_one(person.dict())
    return {
        "id": str(result.inserted_id),
        "name": person.name
    }
