from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()  # This will read variables from .env

SECRET_KEY = os.environ.get('SECRET_KEY')
TEST_ENV_VAR1 = os.environ.get('TEST_ENV_VAR1')
DATABASE_URL = os.environ.get('DATABASE_URL')
# DATABASE_URL = "postgresql://testuser:testpass@db:5432/testdb"  # Update with your DB details

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Example table
class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/people/")
def read_people(db: Session = Depends(get_db)):
    people = db.query(Person).all()
    return [{"id": p.id, "name": p.name} for p in people]

@app.post("/people/")
def add_person(name: str, db: Session = Depends(get_db)):
    person = Person(name=name)
    db.add(person)
    db.commit()
    db.refresh(person)
    return {"id": person.id, "name": person.name}


# In the above code, the API assumes a running PostgreSQL server accessible at hostname db (as typical in Docker Compose or Azure Container Apps setup), with database testdb and user testuser/testpass.

